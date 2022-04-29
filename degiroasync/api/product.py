from typing import Iterable, Any, List, Dict, Union, AnyStr
from typing import Optional, AsyncGenerator, Sequence
import logging
import pprint
import itertools
import asyncio
import datetime
try:
    from enum import StrEnum
except ImportError:
    import enum
    # Exists only starting Python 3.11
    # Reimplement what we need from it here.

    class StrEnum(str, enum.Enum):
        def __str__(self):
            return str.__str__(self)

from jsonloader import JSONclass
from more_itertools import unique_everseen

from ..core.constants import PRODUCT
from ..core.constants import PRICE
from ..core.constants import POSITION
from .. import webapi
from ..core import LOGGER_NAME
from ..core import ResponseError
from ..core import Credentials, SessionCore, Config
from ..core import check_session_client, check_session_config
from ..core.helpers import dict_from_attr_list
from ..core.helpers import camelcase_dict_to_snake
from .session import Session
from .session import Exchange
from .session import check_session_exchange_dictionary


LOGGER = logging.getLogger(LOGGER_NAME)


class ProductBase:
    # Initial implementation of ProductBase included deferred populating of
    # Info to allow client for performance optimizations (e.g. use
    # products before we have received an answer to the Info query).
    # Low availability of guaranteed attributes at ProductBase.Base highlighted
    # this solution to be impractical (need to await .await_product_info for
    # every product) versus little gain as client consistently needed Info
    # data to be able to either reuse and take a decision about the product.
    #
    # This second implementation cuts the optimisation opportunity to only
    # leverage Base information to make it easier to use and reduce risk for
    # client to trip downstream by forgetting to await product Info.
    @JSONclass(annotations=True, annotations_type=True)
    class Base:
        # Attributes provided to init_batch will be populated on base
        # attribute.
        id: str

    @JSONclass(annotations=True, annotations_type=True)
    class Info:
        """
        Must be overwritten and/or subclassed by subclasses of Product.
        """
        id: str
        name: str
        symbol: str
        currency: str
        exchange_id: str
        product_type_id: Union[PRODUCT.TYPEID, int]  # is int for unknown types
    base: Base
    info: Info

    def __init__(self, *, force_init: bool = False):
        """
        Product should not be instantiatied directly, but instantiated
        through the `Product.init_batch` factory. This allows to leverage
        batches of Degiro APIs and relevant speciliazation.

        Batching your requests will improve performance and lower
        load on endpoint.

        force_init
            If this is set to True, allow init of product. Use only if you know
            what you're doing.
        """
        if not force_init:
            raise NotImplementedError("Please use ProductFactory.init_batch.")


class ProductFactory:
    @classmethod
    async def init_batch(
            cls,
            session: SessionCore,
            attributes_iter: Iterable[Dict[str, Any]],
            size=50
    ) -> AsyncGenerator[ProductBase, None]:
        """
        Bulk init Product instances.

        This is useful to do batch requests to populate additional attributes
        for Products.

        attributes_iter
            At the minimum must provides 'id' and 'product_type_id'.
            All attributes provided will be set to the Product.base
            oject.

        Returns an iterable of Product instances

        .. code-block:: python

            import asyncio
            products_attrs = (
                        {'id': 1, 'product_type_id': PRODUCT.TYPEID.STOCK},
                        {'id': 2, 'product_type_id': PRODUCT.TYPEID.STOCK},
                        {'id': 3, 'product_type_id': PRODUCT.TYPEID.STOCK},
                )
            products_gen = ProductFactory.init_batch(session, products_attrs)
            # At this stage, we have an awaitable for each product.
            # All products information may not be available at the same time
            # if init_batch was provided more products than the `size`
            # parameter.
            products = [p async for p in products_gen]

        """
        attributes_batch = []
        batches_awt = []

        for ind, attributes in enumerate(attributes_iter, 1):
            # Check that minimum keys are in attributes
            attributes = camelcase_dict_to_snake(attributes)
            # 2022.04 Poor JSONclass compatibility with mypy
            ProductBase.Base(attributes)  # type: ignore
            attributes_batch.append(attributes)
            if ind % size == 0:
                LOGGER.debug("init_batch| attributes_batch %s",
                             attributes_batch)
                products_batch = cls._create_batch(session,
                                                   attributes_batch.copy())
                batches_awt.append(asyncio.create_task(products_batch))
                attributes_batch.clear()

        if len(attributes_batch):
            batches_awt.append(asyncio.create_task(
                    cls._create_batch(session, attributes_batch)))
        LOGGER.debug('init_batch| batches_awt %s', batches_awt)
        ind = 0
        try:
            for ind, batch_awt in enumerate(batches_awt):
                batch = await batch_awt
                for product in batch:
                    yield product
        except Exception:
            # avoid never awaited coroutine in above generator was never
            # fully consumed
            for i in range(ind + 1, len(batches_awt)):
                await batches_awt[i]
            raise

    @classmethod
    async def _create_batch(
            cls,
            session: SessionCore,
            attributes_batch: Iterable[Dict[str, Any]]
    ) -> Iterable[ProductBase]:
        """
        Create Products and their common ProductsInfo.
        Returns an Iterable of Product instances.
        """
        attributes_batch1, attributes_batch2 = itertools.tee(attributes_batch)
        del attributes_batch

        ids_batch = (attrs['id'] for attrs in attributes_batch1)
        del attributes_batch1

        # 2022.01: Endpoint errors out on duplicate. Remove them.
        ids_batch = list(set(ids_batch))  # no duplicate.

        resp = await webapi.get_products_info(session, ids_batch)
        products_info = camelcase_dict_to_snake(resp)
        # Info is in ['data'][product_id]
        products_info = products_info['data']
        LOGGER.debug('_create_batch| products_info %s', products_info)

        return cls.__products_from_attrs(
                session,
                attributes_batch2,
                products_info
            )

    @classmethod
    def __products_from_attrs(
            cls,
            session: Session,
            products_base_iter: Iterable[Dict[str, Any]],
            products_info: Dict[str, Any]
            ) -> Iterable[ProductBase]:
        """
        Instantiate products from attributes and product_info.

        products_base_iter
            This dictionary keys and values will be assigned to the `base`
            attribute of the instantiated product.

        products_info
            This dictionary keys and values will be assigned to the `info`
            attribute of the instantiated product.
        """
        LOGGER.debug("__products_from_attrs| products_info %s",
                     products_info)
        products_dict = {}

        # Instantiate products
        for product_base in products_base_iter:
            LOGGER.debug("__products_from_attrs| product_base %s",
                         product_base)
            product_id = product_base['id']
            if product_id in products_dict:
                # Don't instantiate twice the same product: point to the
                # already instantiated one.
                instance = products_dict[product_id]
            else:
                product_info = products_info[product_id]
                LOGGER.debug("__products_from_attrs| product_info %s",
                             product_info)
                try:
                    product_info['product_type_id'] = PRODUCT.TYPEID(
                        product_info['product_type_id']
                        )
                except ValueError:
                    # Let int live its life, it'll be a generic product.
                    pass

                product_type_id = product_info['product_type_id']
                # Get specialized class if there is one implemented
                inst_cls = {
                    PRODUCT.TYPEID.CURRENCY: Currency,
                    PRODUCT.TYPEID.STOCK: Stock
                }.get(
                    product_type_id,
                    ProductGeneric
                )
                LOGGER.debug(
                        "api.ProductFactory.init_product| type_id %s class %s",
                        product_type_id, inst_cls)
                product_info = camelcase_dict_to_snake(product_info)
                # 2022.04 JSONclass poor compatibility with mypy
                info = inst_cls.Info(product_info)  # type: ignore
                instance = inst_cls(force_init=True)
                # 2022.04 JSONclass poor compatibility with mypy
                instance.base = inst_cls.Base(product_base)  # type: ignore
                instance.info = info
                products_dict[product_id] = instance
            yield instance


class Currency(ProductBase):
    class Info(ProductBase.Info):
        "Store Info calls return."
        isin: str
        symbol: str
        name: str
        vwd_id: Optional[str] = None  # not set if non-tradable
        tradable: bool
        product_type_id: PRODUCT.TYPEID

    info: Info


class Stock(ProductBase):
    class Info(ProductBase.Info):
        "Store Info calls return."
        isin: str
        symbol: str
        name: str
        vwd_id: Optional[str] = None  # not set if non-tradable
        vwd_identifier_type: Optional[str] = None  # not set if non-tradable
        product_type: str
        product_type_id: PRODUCT.TYPEID
        tradable: bool
        category: str
        # feed_quality: str  # Not always available

    class VWDIDTYPES(StrEnum):
        ISSUEID = 'issueId'
        VWDKEY = 'vwdkey'

    info: Info


class ProductGeneric(ProductBase):
    class Base(ProductBase.Base):
        id: str

    class Info(ProductBase.Info):
        "Store Info calls return."
        isin: str
        symbol: str
        name: str
        tradable: bool

    info: Info


@JSONclass(annotations=True, annotations_type=True)
class TotalPortfolio:
    degiro_cash: float
    flatex_cash: float
    total_cash: float
    total_deposit_withdrawal: float
    today_deposit_withdrawal: float
    cash_fund_compensation_currency: str
    cash_fund_compensation: float
    cash_fund_compensation_withdrawn: float
    today_non_product_fees: float
    free_space_new: Dict[str, float]  # Currency: value
    report_margin: float
    report_creation_time: str
    report_portf_value: float
    report_cash_bal: float
    report_netliq: float
    report_overall_margin: float
    report_total_long_val: float
    report_deficit: float
    margin_call_status: str
    """
    Total Portfolio

    Core parameters for total portfolio as returned per API.

    Any additional parameter will be set to the object to reflect
    up to date API changes.
    """


@JSONclass(annotations=True, annotations_type=True)
class Position:
    """
    A position on a product, returned by get_portfolio.

    Be careful when dealing with products in different currencies:
    `value` attribute is in the account local currency, while `price`
    in the currency of the product. `average_fx_rate` and other fx are
    necessary to do the conversion between `price * size` and `value`
    """
    product: ProductBase
    size: Union[int, float]
    price: float
    value: float
    position_type: Union[POSITION.TYPE, str]
    break_even_price: float
    average_fx_rate: Union[float, int]
    realized_product_pl: float
    today_realized_product_pl: float
    realized_fx_pl: Union[float, int]
    today_realized_fx_pl: Union[float, int]
    pl_base: Dict[str, float]
    today_pl_base: Dict[str, float]
    portfolio_value_correction: Union[float, int]

    # Example camel case JSON:
# {'id': '8217023', 'position_type': 'PRODUCT', 'size': 70, 'price': 55.39, 'value': 3877.3, 'pl_base': {'EUR': -4796.53}, 'today_pl_base': {'EUR': -3877.3}, 'portfolio_value_correction': 0, 'break_even_price': 68.36, 'average_fx_rate': 1, 'realized_product_pl': -11.33, 'realized_fx_pl': 0, 'today_realized_product_pl': 0.0, 'today_realized_fx_pl': 0}


async def get_portfolio(
        session: SessionCore
) -> Sequence[Position]:
    """
    Returns Products in portfolio. Refer to  `Products` classes for minimum
    available attributes.
    """
    check_session_client(session)
    check_session_config(session)

    resp_json = await webapi.get_portfolio(session)
    portf_json = resp_json['portfolio']['value']
    portf_dict_json = [
            camelcase_dict_to_snake(
                dict_from_attr_list(v['value'], ignore_error=True))
            for v in portf_json]
    LOGGER.debug("api.get_portfolio| %s", pprint.pformat(portf_dict_json))

    portfolio = ProductFactory.init_batch(
            session,
            ({'id': p['id']} for p in portf_dict_json))

    products = {p.info.id: p async for p in portfolio}
    for portf in portf_dict_json:
        portf['product'] = products[portf['id']]
        try:
            portf['position_type'] = POSITION.TYPE(portf['position_type'])
        except ValueError:
            # Let str value
            LOGGER.info("POSITION TYPE %s unknown. Leave as is.",
                        portf['position_type'])
        del portf['id']
    # 2022.04 JSONclass has poor compatibility with mypy
    return [Position(portf) for portf in portf_dict_json]  # type: ignore


async def get_portfolio_total(
        session: SessionCore
) -> TotalPortfolio:
    """
    Returns (TotalPortfolio, Products). Refer to `TotalPortfolio` and
    `Products` classes for attributes available.
    """
    check_session_client(session)
    check_session_config(session)

    resp_json = await webapi.get_portfolio_total(session)

    LOGGER.debug("api.get_portfolio_total| %s", resp_json)

    total_args = dict_from_attr_list(resp_json['totalPortfolio']['value'],
                                     ignore_error=True)
    total_portfolio = TotalPortfolio(camelcase_dict_to_snake(total_args))

    return total_portfolio


@JSONclass(annotations=True, annotations_type=True)
class PriceSeries:
    type: str
    expires: str


@JSONclass(annotations=True, annotations_type=True)
class PriceSeriesTime:
    """
    Converted Wrapper for PriceSeriestime for get_price_data.

    times
        Starting time of the series.

    price
        Price floats of the series

    date
        Dates in ISO 8601 format. A data point (`date`, `price`) shares the
        same index in the `price` and `date` list attributes.

    resolution
        `PRICE.RESOLUTION` of the data, if known. It may differ from requested
        resolution.

    expires
        As returned per end point. Can be used as indication when to query
        for new data.
    """
    times: str
    price: List[float]
    date: List[str]
    resolution: Union[PRICE.RESOLUTION, str]
    expires: str


# 2022.04: mypy limited support for StrEnum, ignore until proper support.
async def get_price_data(
        session: SessionCore,
        product: Stock,
        resolution: PRICE.RESOLUTION = PRICE.RESOLUTION.PT1M,  # type: ignore
        period: PRICE.PERIOD = PRICE.PERIOD.P1DAY,  # type: ignore
        timezone: str = 'Europe/Paris',
        culture: str = 'fr-FR',
        data_type: PRICE.TYPE = PRICE.TYPE.PRICE  # type: ignore
        ) -> PriceSeriesTime:
    """
    Get price data for `product`.

    product
        Product to look for the data.

    resolution
        How close do we request data points to be.

    period
        How long of data do we want

    data_type
        Specify if we want raw price, or 'ohlc' (open, high, low, close)
        information. The latter might be useful for long periods where high
        resolution is not available.

    Returns
    -------
        PriceSeriesTime
            Contains price data and time information.

    """
    # Ensure product got results of product_info
    if product.info.product_type_id != PRODUCT.TYPEID.STOCK:
        raise NotImplementedError(
            "Only productTypeId == PRODUCT.TYPEID.STOCK is currently "
            "supported by get_price_data")
    resp_json = await webapi.get_price_data(
        session,
        vwdId=product.info.vwd_id,
        vwdIdentifierType=product.info.vwd_identifier_type,
        resolution=resolution,
        period=period,
        timezone=timezone,
        culture=culture,
        data_type=data_type)
    LOGGER.debug("api.get_price_data resp_json| %s", resp_json)
    timeseries_ind = -1
    objectseries_ind = -1
    # Look for time series
    for ind, series in enumerate(resp_json['series']):
        if series['type'] == 'time':
            timeseries_ind = ind
        if series['type'] == 'object':
            objectseries_ind = ind  # Might be used in later revisions.
    if timeseries_ind < 0:
        raise ResponseError("No 'time' series found in answer.")
    converted_time_series = convert_time_series(resp_json['series'][ind])
    converted_time_series['date'] = converted_time_series['data']['date']
    converted_time_series['price'] = converted_time_series['data']['price']
    try:
        resolution_out = PRICE.RESOLUTION(converted_time_series['resolution'])
        converted_time_series['resolution'] = resolution_out
    except ValueError:
        LOGGER.debug(
                "converted_time_series['resolution'] is unknown: %s. "
                "Leave as str",
                converted_time_series['resolution']
                )
    del converted_time_series['data']
    return PriceSeriesTime(converted_time_series)


def convert_time_series(
        data_series: Dict[str, Union[str, List[Union[float, int]]]]
    ) -> Dict[str,
              Union[str, Dict[str, Union[float, str]]]
              ]:
    """
    Helper to convert data series.

    Aims to make it easier to feed inin a pandas friendly format.

    >>> data = {
    ...     "times": "2022-01-20T00:00:00/PT1M",
    ...     "expires": "2022-01-20T10:12:56+01:00",
    ...     "data": [
    ...         [
    ...             540,
    ...             114.0
    ...         ],
    ...         [
    ...             541,
    ...             114.08
    ...         ],
    ...         [
    ...             542,
    ...             114.12
    ...         ]
    ...     ]
    ... }
    >>> data_out = convert_time_series(data)
    {

        "type": "time",
        "times": "2022-01-20T00:00:00",
        "resolution": "PT1M",
        "expires": "2022-01-20T10:11:53+01:00",
        "data": {
            'price': [114.0, 114.08, 114.12],
            'date': [
                '2022-01-20T09:00:00',
                '2022-01-20T09:01:00',
                '2022-01-20T09:02:00']
        }
    }

    """
    time_t, resolution_t = data_series['times'].split('/')
    data_out: Dict[str, Any] = data_series.copy()

    for key in ('times', 'expires', 'data'):
        if key not in data_series:
            raise KeyError(f'{key} not found in data_series {data_series}')

    resolution_whitelist = (PRICE.RESOLUTION.PT1M, PRICE.RESOLUTION.PT1D)
    if resolution_t not in resolution_whitelist:
        raise NotImplementedError("convert_time_series has not been tested "
                                  "with resolutions other than {}. "
                                  "Received resolution: {}".format(
                                        resolution_whitelist,
                                        resolution_t
                                        )
                                  )

    data_new: Dict[str, Union[Sequence[str], Sequence[float]]] = {
        'price': [],
        'date': [],
        }
    data_out['data'] = data_new
    data_out['type'] = 'time'
    data_out['resolution'] = resolution_t
    data_out['times'] = time_t
    # Multiplier to get time delta (in minutes) from time index
    # returned by API.
    time_multiplier: int = {
        PRICE.RESOLUTION.PT1M: 1,
        PRICE.RESOLUTION.PT1D: 60*24
        }[resolution_t]

    start_date = datetime.datetime.fromisoformat(time_t)
    for kv in data_series['data']:
        data_new['price'].append(float(kv[1]))
        time_ind = kv[0]
        time_delta = float(time_ind) * time_multiplier
        measure_date = start_date + datetime.timedelta(minutes=time_delta)
        data_new['date'].append(measure_date.isoformat())
    return data_out


async def search_product(
        session: Session,
        *,
        by_text: Optional[str] = None,
        by_isin: Optional[str] = None,
        by_symbol: Optional[str] = None,
        by_exchange: Union[str, Exchange, None] = None,
        product_type_id: Optional[PRODUCT.TYPEID] = PRODUCT.TYPEID.STOCK,
        max_iter: Union[int, None] = 1000
        ) -> List[ProductBase]:
    """
    Access `product_search` endpoint.

    Exactly one of `by_text`, `by_isin`, `by_symbol` be set.
    This is done because endpoint API doesn't return expected results
    with both text and ISIN search.

    product_type_id
        Restricts search to one type of products.

    by_exchange
        Restricts results to products in a exchange. Can be either an Exchange
        instance or an `hiq_abbr` str (e.g. EPA for Paris, AEX for Amsterdam)

    max_iter
        Pull `max_iter` pages of results. If `None`, don't stop until end is
        reached. Default value: 1000.

    Return a list of ProductBase objects returned by Degiro for `search_txt`
    attribute.
    """
    if sum(k is not None for k in (by_text, by_isin, by_symbol)) != 1:
        raise AssertionError(
            "Exactly one of by_text, by_isin, by_symbol must "
            "be not None.")
    # Degiro API doesn't support well 2 or more attribute in searchTxt:
    # e.g. we can't search for "AIRBUS NL0000235190" and get all the AIRBUS
    # named products with ISIN NL0000235190.
    if by_text is None:
        # We've checked above that we only have one not-None search parameter.
        if by_symbol is not None:
            by_text = by_symbol
        elif by_isin is not None:
            by_text = by_isin
        else:
            raise AssertionError(
                    "by_text is None and no search parameters was set or "
                    "found. Have you set a search parameters to "
                    "get_price_data?"
                    "\n If yes, this shouldn't be happening, please open a bug"
                    " report."
                    )

    exchange_id = None
    if by_exchange is not None:
        if isinstance(by_exchange, Exchange):
            exchange_id = by_exchange.id
        elif isinstance(by_exchange, str):
            check_session_exchange_dictionary(session)
            exchange = session.exchange_dictionary.exchange_by(
                hiq_abbr=by_exchange)
            exchange_id = exchange.id
        else:
            raise TypeError(
                "Only Exchange or str types supported for 'by_exchange'.")

    limit = 100
    offset = 0
    products = []

    def __custom_filter(p_json: Dict[str, Any]) -> bool:
        "Return True if product match user parameters"

        # Web API should already filter by typeId, recheck TypeID here to be
        # sure we don't have garbage in.
        for attr, key in ((product_type_id, 'productTypeId'),
                          (by_isin, 'isin'),
                          (by_symbol, 'symbol'),
                          (exchange_id, 'exchangeId')):
            if attr is not None and p_json.get(key) != attr:
                return False
        return True

    iter_n = 0
    run_forever = max_iter is None
    if max_iter is None:
        max_iter = -1
    while iter_n < max_iter or run_forever:
        iter_n += 1
        resp_json = await webapi.search_product(
            session,
            by_text,
            product_type_id=product_type_id,
            limit=limit,
            offset=offset)
        LOGGER.debug("api.search_product response| %s",
                     pprint.pformat(resp_json))
        if 'products' in resp_json:
            products_json = resp_json['products']
            LOGGER.debug("api.search_product n_products| %s",
                         products_json)
            batch_gen = ProductFactory.init_batch(
                    session,
                    filter(__custom_filter,
                           products_json))
            batch = [p async for p in batch_gen]
            # This could be optimized later on with a generator class to be
            # able to yield data as soon as we receive it while still not
            # blocking further calls to be launched, should it be needed.
            products += batch
            LOGGER.debug("api.search_product (batch len, symbol)| (%s, %s)",
                         len(batch), by_symbol)
            if len(products_json) < limit:
                break
            else:
                offset += len(products_json)
        else:
            LOGGER.debug("No 'products' key in response. Stop.")
            break
    # return a unique list
    return list(unique_everseen(products, lambda p: p.info.id))


__all__ = [
    obj.__name__ for obj in (  # type: ignore
        # Login & setup
        Credentials,
        Session,
        SessionCore,
        Config,

        # Product data structures
        # PriceData,
        Stock,
        Currency,
        ProductBase,
        get_portfolio,
        get_price_data,
        search_product
    )
]
