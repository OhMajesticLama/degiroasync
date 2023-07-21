from typing import Iterable, Any, List, Dict, Union
from typing import Optional, AsyncGenerator, Sequence
from typing import Tuple
import re
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
from .session import Index
from .session import check_session_dictionary


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

    def __repr__(self):
        return (f'<degiroasync.api.product.{self.__class__.__name__} '
                f'[{self.info.name} | {self.info.symbol}]>')


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
            session: Session,
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
        products_dict: Dict[str, ProductBase] = {}

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
                    # Let int stay, it'll be a generic product.
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
                #if inst_cls is Stock:
                if (
                        product_info.get('exchange_id')
                        and issubclass(inst_cls, Stock)
                        ):
                    # WARNING: There could be exchange_id key, but empty value,
                    # We don't want to set it here if that's the case
                    product_info['exchange'] = (
                            session.dictionary.exchange_by(
                                id=product_info['exchange_id'])
                            )
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
        exchange: Exchange
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


class PriceSeriesTime:
    """
    Deprecated: please use PriceSeries class. This will be removed in a future
    version.
    """


class PriceSeries(PriceSeriesTime):
    type: PRICE.TYPE
    start: datetime.datetime
    end: datetime.datetime
    expires: datetime.datetime
    resolution: PRICE.RESOLUTION
    __data: List[List[Union[int, float]]]

    def __init__(
            self,
            *,
            start: datetime.datetime,
            end: datetime.datetime,
            currency: str,
            resolution: PRICE.RESOLUTION,
            series: Dict[str, List[List[Union[int, float]]]]
            ):
        """
        Base class for price data.

        Attributes
        ----------

        start
            Start time of the price data series returned by remote API.

        end
            End time of the price data series returned by remote API.

        currency
            Currency for the prices data.

        resolution
            Resolution of the price series.
            See :class:`~degiroasync.core.PRICE.RESOLUTION`.

        series
            Price Data Series returned by remote API. For example:

            .. code-block:: python
                {
                    'times': '2023-06-29/P1D',
                    'expires': '2023-07-05T17:54:21.7030064+02:00',
                    'data': [
                        [0, 130.54, 131.64, 129.93, 130.46],
                        [1, 131.16, 132.68, 130.42, 132.36],
                        [4, 132.8, 133.7, 131.62, 132.61],
                        [5, 132.6, 132.98, 130.96, 131.32],
                        [6, 131.2, 133.5, 130.88, 132.82]],
                    'id': 'ohlc:issueid:350118230',
                    'type': 'ohlc'
                }
        """
        # Example data containing series:
        # {
        #        'requestid': '1',
        #        'start': '2023-06-29T00:00:00',
        #        'end': '2023-07-05T00:00:00',
        #        'resolution': 'P1D',
        #        'series': [
        #            {
        #                'times': '2023-06-29/P1D',
        #                'expires': '2023-07-05T17:54:21.7030064+02:00',
        #                'data': [
        #                    [0, 130.54, 131.64, 129.93, 130.46],
        #                    [1, 131.16, 132.68, 130.42, 132.36],
        #                    [4, 132.8, 133.7, 131.62, 132.61],
        #                    [5, 132.6, 132.98, 130.96, 131.32],
        #                    [6, 131.2, 133.5, 130.88, 132.82]],
        #                'id': 'ohlc:issueid:350118230',
        #                'type': 'ohlc'
        #                }
        #            ]
        #        }
        self.start = start
        self.end = end

        expires_str = series['expires']
        # Example expire_str: '2023-07-05T17:54:21.7030064+02:00'
        # microseconds will be more then enough, remove extra digit
        expires_str = re.sub(r'\.(\d{6})\d\+', r'.\1+', expires_str)
        expires_str = re.sub(r'\+(\d{2}):(\d{2})$', r'+\1\2', expires_str)
        self.expires = datetime.datetime.strptime(
                expires_str,
                '%Y-%m-%dT%H:%M:%S.%f%z'
                )

        self.resolution = resolution
        self.currency = currency
        self.__series = series
        if series['type'] == 'time':
            self.type = PRICE.TYPE.PRICE
        elif series['type'] == 'ohlc':
            self.type = PRICE.TYPE.OHLC
        else:
            raise NotImplementedError(
                    f"Series type {series['type']} not supported.")

    def _get_delta(self):
        if self.resolution == PRICE.RESOLUTION.PT1D:
            delta = datetime.timedelta(days=1)
        elif self.resolution == PRICE.RESOLUTION.PT1M:
            delta = datetime.timedelta(minutes=1)
        else:
            raise NotImplementedError(
                    f"Resolution {self.resolution} not supported.")
        return delta

    def _get_dates_it(self) -> Iterable[datetime.datetime]:
        times_split = self.__series['times'].split('/')
        start = datetime.datetime.fromisoformat(times_split[0])
        if len(times_split) > 1:
            assert PRICE.RESOLUTION(times_split[1]) == self.resolution
        delta = self._get_delta()
        data = self.__series['data']
        delta = self._get_delta()
        return [start + d[0] * delta for d in data]

    def items(self) -> Iterable[
            Tuple[str, List[Union[float, datetime.datetime]]]
                ]:
        """

        """
        data = self.__series['data']
        yield ('date', self._get_dates_it())
        if self.type == PRICE.TYPE.OHLC:
            yield ('open', [x[1] for x in data])
            yield ('high', [x[2] for x in data])
            yield ('low', [x[3] for x in data])
            yield ('close', [x[4] for x in data])
        elif self.type == PRICE.TYPE.PRICE:
            yield ('close', [x[1] for x in data])
        else:
            raise NotImplementedError(f"Price type {self.type} not supported.")

    def iterrows(self) -> Iterable[Dict[str, Union[datetime.datetime, float]]]:
        """
        Provide data by columns, can be fed directly to instantiate a
        `pandas.DataFrame <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`

        With `pandas.DataFrame`:

            >>> pricedata = PriceData(
                    start=datetime.datetime(2023, 6, 29),
                    end=datetime.datetime(2023, 7, 5),
                    resolution=PRICE.RESOLUTION.OHLC
                    currency='EUR',
                    data={
                        'data': [
                            [0, 1., 4., 0., 2.],
                            [1, 2., 4., 0., 2.]
                            ],
                        'type': 'ohlc',
                        'times': '2023-06-29/P1D',
                        'expires': '2023-07-05T17:54:21.7030064+02:00',
                        }
                    )
            >>> import pandas as pd
            >>> df = pd.DataFrame(pricedata.iterrows())
            >>> df.columns
            Index(['date', 'open', 'high', 'low', 'close'], dtype='object')
            >>> df.iloc[0]['date']
            Timestamp('2023-06-29 00:00:00')
            >>> df['open']
            0    1.
            1    2.
            Name: open, dtype: float64
        """

        data = self.__series['data']
        if self.type == PRICE.TYPE.PRICE:
            for date, row in zip(self._get_dates_it(), data):
                yield {'date': date, 'close': row[1]}
        elif self.type == PRICE.TYPE.OHLC:
            for date, row in zip(self._get_dates_it(), data):
                yield {
                        'date': date,
                        'open': row[1],
                        'high': row[2],
                        'low': row[3],
                        'close': row[4],
                        }
        else:
            raise NotImplementedError(f"Price type {self.type} not supported.")

    @property
    def date(self):
        #print(
        #        "degiroasync.PriceSeries.date is deprecated and will be "
        #        "removed in a future version. "
        #        "Please use PriceSeries.items() or PriceSeries.iterrows().",
        #        file=sys.stderr
        #        )
        return [d.isoformat() for d in self._get_dates_it()]

    @property
    def price(self) -> Sequence[Union[float, Sequence[float]]]:
        #print(
        #        "degiroasync.PriceSeries.price is deprecated and will be "
        #        "removed in a future version. "
        #        "Please use PriceSeries.items() or PriceSeries.iterrows()",
        #        file=sys.stderr
        #        )
        if self.type == PRICE.TYPE.OHLC:
            return [row[1:] for row in self.__series['data']]
        if self.type == PRICE.TYPE.PRICE:
            return [row[1] for row in self.__series['data']]
        raise NotImplementedError(
                f"price is supported only for PRICE.TYPE.PRICE, "
                f"not {self.type}")


class PriceSeriesTime(PriceSeries):
    """
    DEPRECATED: This will be removed in a future verison, please use
    PriceSeries.
    """


async def get_price_data(*args, **kwargs):
    "DEPRECATED: Please use get_price_series instead."
    LOGGER.warn(
            "get_price_data is deprecated, please use get_price_series instead"
            )
    return await get_price_series(*args, **kwargs)


# 2022.04: mypy limited support for StrEnum, ignore until proper support.
async def get_price_series(
        session: SessionCore,
        product: Stock,
        resolution: PRICE.RESOLUTION = PRICE.RESOLUTION.PT1D,  # type: ignore
        period: PRICE.PERIOD = PRICE.PERIOD.P1MONTH,  # type: ignore
        timezone: str = 'Europe/Paris',
        culture: str = 'fr-FR',
        data_type: PRICE.TYPE = PRICE.TYPE.PRICE  # type: ignore
        ) -> PriceSeries:
    """
    Get price data for `product`.

    Parameters
    ----------
    product
        Product to look for the data.

    resolution
        How often do we want data points.

        See :class:`~degiroasync.core.constants.PRICE.RESOLUTION` for available
        values.

    period
        Period between now and data starting point.

        See :class:`~degiroasync.core.constants.PRICE.PERIOD` for available
        values.

    data_type
        Specify if we want raw price, or 'ohlc' (open, high, low, close)
        information. The latter might be useful for long periods where high
        resolution is not available.

        See :class:`~degiroasync.core.constants.PRICE.TYPE` for available
        values.

    Returns
    -------
        PriceSeriesTime
            Contains price data and time information.

    """
    # Ensure product got results of product_info
    if product.info.product_type_id != PRODUCT.TYPEID.STOCK:
        raise NotImplementedError(
            "Only productTypeId == PRODUCT.TYPEID.STOCK is currently "
            "supported by get_price_series")
    resp_json = await webapi.get_price_series(
        session,
        vwdId=product.info.vwd_id,
        vwdIdentifierType=product.info.vwd_identifier_type,
        resolution=resolution,
        period=period,
        timezone=timezone,
        culture=culture,
        data_type=data_type,
        )
    LOGGER.debug("api.get_price_series resp_json| %s", resp_json)

    # Look for price series
    series_ind = -1
    objectseries_ind = -1
    for ind, series in enumerate(resp_json['series']):
        if series['type'] == 'time':
            assert series_ind < 0, "Unexpected more than 1 series."
            series_ind = ind
        if series['type'] == 'object':
            # This is not always returned by API, don't rely on it
            objectseries_ind = ind
        if series['type'] == 'ohlc':
            assert series_ind < 0, "Unexpected more than 1 series"
            series_ind = ind

    if series_ind < 0:
        raise ResponseError("No 'time' or 'ohlc' series found in answer.")
    if objectseries_ind < 0:
        # Check currency if we have info
        object_series = resp_json['series'][objectseries_ind]
        if 'currency' in object_series.get('data', {}):
            assert object_series['data']['currency'] == product.info.currency

    series_d = resp_json['series'][series_ind]
    prices_series = PriceSeries(
            start=datetime.datetime.fromisoformat(resp_json['start']),
            end=datetime.datetime.fromisoformat(resp_json['end']),
            resolution=PRICE.RESOLUTION(resp_json['resolution']),
            currency=product.info.currency,
            series=series_d,
            )
    return prices_series


async def _search_one(
        session: Session,
        *,
        by_text: Optional[str] = None,
        by_isin: Optional[str] = None,
        by_symbol: Optional[str] = None,
        country_id: Optional[str] = None,
        exchange_id: Optional[Union[str, Exchange]] = None,
        index_id: Optional[Union[str, Index]] = None,
        product_type_id: Optional[PRODUCT.TYPEID] = PRODUCT.TYPEID.STOCK,
        offset: int = 0,
        limit: int = 100,
        ) -> (Sequence[ProductBase], int, int):
    """
    Returns
    -------

    products
        Instantiated products found.

    n_unfiltered
        Number of products returned by the API before local filtering.

    total
        Total number of products that could be returned by API, before local
        filtering.
    """
    def __custom_filter(p_json: Dict[str, Any]) -> bool:
        "Return True if product match user parameters"

        # Web API should already filter by typeId, recheck TypeID here to be
        # sure we don't have garbage in.
        for attr, key in ((product_type_id, 'productTypeId'),
                          (by_isin, 'isin'),
                          (by_symbol, 'symbol'),
                          (exchange_id, 'exchangeId'),
                          ):
            if attr is not None and p_json.get(key) != attr:
                return False
        return True

    resp_json = await webapi.search_product(
        session,
        by_text,
        product_type_id=product_type_id,
        country_id=country_id,
        index_id=index_id,
        limit=limit,
        offset=offset)
    LOGGER.debug("api.search_product response| %s",
                 pprint.pformat(resp_json))
    # Calls with more than one page could be parallelized:
    # First page is needed first to get the total answers, but
    # further pages could be fetched several at a time.
    total = resp_json['total']  # Total number of products returned
    if 'products' in resp_json:
        n_unfiltered = len(resp_json['products'])
        products_json = resp_json['products']
        LOGGER.debug("api.search_product n_products| %s",
                     products_json)
        batch_gen = ProductFactory.init_batch(
                session,
                filter(__custom_filter,
                       products_json))
        products = [p async for p in batch_gen]
        # This could be optimized later on with a generator class to be
        # able to yield data as soon as we receive it while still not
        # blocking further calls to be launched, should it be needed.
        LOGGER.debug("api.search_product (batch len, symbol)| (%s, %s)",
                     len(products), by_symbol)
        return products, n_unfiltered, total

    else:
        LOGGER.debug("No 'products' key in response. Stop.")
        raise ResponseError(f"No 'products' key in response {resp_json} ")


async def search_product(
        session: Session,
        *,
        by_text: Optional[str] = None,
        by_isin: Optional[str] = None,
        by_symbol: Optional[str] = None,
        by_country: Optional[str] = None,
        by_exchange: Optional[Union[str, Exchange]] = None,
        by_index: Optional[Union[str, Index]] = None,
        product_type_id: Optional[PRODUCT.TYPEID] = PRODUCT.TYPEID.STOCK,
        max_iter: Optional[int] = 1000
        ) -> List[ProductBase]:
    """
    Access `product_search` endpoint.

    Exactly one of `by_text`, `by_isin`, `by_symbol` be set.
    Note: API endpoint doesn't return expected results with both text and
    ISIN search.

    Parameters
    ----------

        by_text
            As a search text in Degiro search field website.

        by_isin
            Will look-up products with provided ISIN identifier.

        by_symbol
            Product outputs will be filtered on their 'symbol'.

        by_country
            Products matching this argument, string must be ISO 3166-1 alpha-2
            2 letters code.

        product_type_id
            Restricts search to one type of products.
            See :class:`~degiroasync.core.PRODUCT.TYPEID`

        by_exchange
            Restricts results to products in an exchange. Can be either an
            Exchange instance or an `hiq_abbr` str (e.g. EPA for Paris, AEX
            for Amsterdam)

        by_index
            Restricts results to products in an index. Can be either an
            Index instance or an index `name` str.

        product_type_id
            Restricts search to one type of products.

        max_iter
            Pull `max_iter` pages of results. If `None`, don't stop until end
            is reached. Default value: 1000.

    Returns
    -------

        Return a list of ProductBase objects returned by Degiro for
        `search_txt` attribute.
    """
    if sum(k is not None for k in (by_text, by_isin, by_symbol)) > 1:
        raise AssertionError(
            "Only one of by_text, by_isin, by_symbol can "
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
        elif by_country is not None:
            pass  # Could also be set without text deal with it after
        elif by_index is not None:
            pass  # Manage below
        else:
            raise AssertionError(
                    "by_text is None and no search parameters was set or "
                    "found. Have you set a search parameters to "
                    "search_product?"
                    "\n If yes, this shouldn't be happening, please open a bug"
                    " report."
                    )

    country_id = None
    if by_country is not None:
        country = session.dictionary.country_by(
            name=by_country
                )
        country_id = country.id

    exchange_id = None
    if by_exchange is not None:
        if isinstance(by_exchange, Exchange):
            exchange_id = by_exchange.id
        elif isinstance(by_exchange, str):
            check_session_dictionary(session)
            exchange = session.dictionary.exchange_by(
                hiq_abbr=by_exchange)
            exchange_id = exchange.id
        else:
            raise TypeError(
                "Only Exchange or str types supported for 'by_exchange'.")

    index_id = None
    if by_index is not None:
        if isinstance(by_index, Index):
            index_id = by_index.id
        elif isinstance(by_index, str):
            check_session_dictionary(session)
            index = session.dictionary.index_by(name=by_index)
            index_id = index.id
        else:
            raise TypeError(
                "Only Index or str types supported for 'by_index'.")

    limit = 100
    products = []

    # trigger first call to get total:
    products, n_unfiltered, total = await _search_one(
            session,
            by_text=by_text,
            by_isin=by_isin,
            by_symbol=by_symbol,
            country_id=country_id,
            exchange_id=exchange_id,
            index_id=index_id,
            offset=0,
            limit=limit
            )

    if n_unfiltered < total:
        # Generate args
        args = ({
            'session': session,
            'by_text': by_text,
            'by_isin': by_isin,
            'by_symbol': by_symbol,
            'index_id': index_id,
            'country_id': country_id,
            'exchange_id': exchange_id,
            'offset': offset,
            'limit': limit,
            } for offset in range(n_unfiltered, total, limit)
            )
        # The use of _search_one and gather improves performance over
        # sequential queries in a while loop as before.
        # 20230713 FR symbols query, throttling at 10 queries per 1 second:
        #   - With gather+_search_one: 3.6s
        #   - With legacy sequential calls: 6.9s
        answers = await asyncio.gather(
                    *[_search_one(**kwa) for kwa in args])
        for prods, _, _ in answers:
            products += prods

    return list(unique_everseen(products, lambda p: p.info.id))


__all__ = [
    obj.__name__ for obj in (  # type: ignore
        # Login & setup
        Credentials,
        Session,
        SessionCore,
        Config,
        PriceSeries,

        # Product data structures
        # PriceData,
        Stock,
        Currency,
        ProductBase,
        get_portfolio,
        get_price_series,
        search_product
    )
]
