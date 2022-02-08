from typing import Iterable, Any, List, Dict, Tuple, Union
import logging
import pprint
import functools
import asyncio
import datetime

from ..core.constants import PRODUCT
from ..core.constants import PRICE
from ..core.constants import EnumStr
from .. import webapi
from ..core import LOGGER_NAME
from ..core import ResponseError
from ..core import Credentials, SessionCore, URLs, Config, PAClient
from ..core.helpers import set_params
from ..core.helpers import dict_from_attr_list
from ..core.helpers import setattrs
from ..core.helpers import run_in_new_thread
from ..core.helpers import check_keys
from ..core import helpers
from ..core import constants
from jsonloader import JSONclass


LOGGER = logging.getLogger(LOGGER_NAME)


@JSONclass(annotations=True, annotations_type=True)
class Region:
    id: int
    name: str


@JSONclass(annotations=True, annotations_type=True)
class Country:
    id: str
    name: str  # 2 letters country codename
    region: 'Region'


@JSONclass(annotations=True, annotations_type=True)
class Exchange:
    id: str
    name: str
    city: Union[str, None] = None
    code: Union[str, None] = None
    countryName: str  # renamed from 'country' as it is country name
    hiqAbbr: str
    micCode: Union[str, None] = None


class ExchangeDictionary:
    """
    Usage:

    >>>> exchangedict = await ExchangeDictionary(session)
    >>>> exchangedict.exchange_by(hiqAbbr='EPA')
    {''}  # TODO

    """

    exchanges: List[Exchange]
    countries: List[Country]
    regions: List[Region]

    async def __new__(cls, session: SessionCore):
        self = super().__new__(cls)

        resp = await webapi.get_product_dictionary(session)
        product_dictionary = resp.json()
        LOGGER.debug("api.ExchangeDictionary| %s",
                     pprint.pformat(product_dictionary))
        self._regions = {p['id']: Region(p)
                         for p in product_dictionary['regions']}

        self._countries_id = {}
        self._countries_name = {}
        for country in product_dictionary['countries']:
            # Replace region dict by object.
            region = self._regions[country['region']]
            country['region'] = region
            country['id'] = str(country['id'])
            # Register country
            country_inst = Country(country)
            self._countries_id[country['id']] = country_inst
            self._countries_name[country['name']] = country_inst

        self._exchanges = {}
        for exchange in product_dictionary['exchanges']:
            # Some APIs call return id in int, others in str. Fix here as all
            # str.
            exchange['id'] = str(exchange['id'])
            # Replace region dict by object.
            exchange['countryName'] = exchange['country']
            del exchange['country']

            # Register country
            self._exchanges[exchange['id']] = Exchange(exchange)

        return self

    @property
    def exchanges(self):
        return self._exchanges.values()

    @property
    def countries(self):
        return self._countries_name.values()

    @property
    def regions(self):
        return self._regions.values()

    @functools.lru_cache(32)
    def exchange_by(
            self,
            *,
            name: Union[str, None] = None,
            id: Union[int, None] = None,
            hiqAbbr: Union[str, None] = None,
            micCode: Union[str, None] = None) -> Exchange:
        """Get Exchange by *either* name, hiqAbbr (e.g. EPA),
        micCode (e.g. XPAR)."""
        if sum(attr is not None for attr in (name, id, hiqAbbr, micCode)) != 1:
            raise AssertionError(
                "Exactly one of (name, id, hiqAbbr, micCode) "
                "must be not None.")
        if id is not None:
            return self._exchanges[id]
        for exc in self._exchanges.values():
            if name is not None and exc.name == name:
                return exc
            elif hiqAbbr is not None and exc.hiqAbbr == hiqAbbr:
                return exc
            elif micCode is not None and exc.micCode == micCode:
                return exc
        raise KeyError("No exchange found with search attributes: {}",
                       (name, id, hiqAbbr, micCode))

    def country_by(
            self,
            *,
            name: Union[str, None] = None,
            id: Union[int, None] = None) -> Country:
        if sum(attr is not None for attr in (name, id)) != 1:
            raise AssertionError(
                "Exactly one of (name, id) must be not None.")
        if name is not None:
            return self._countries_name[name]
        if id is not None:
            return self._countries_id[id]


class Session(SessionCore):
    exchange_dictionary: Union[ExchangeDictionary, None] = None


class ProductsInfo:
    # TODO: assess if it would be useful to create a generic batch class
    def __init__(self, session: SessionCore, products_ids: List[str]):
        "Takes a non-awaited get_products_info call."
        self.__awaitable = webapi.get_products_info(session, products_ids)
        self.__response = None
        self.__awaitable_lock = asyncio.Lock()

    async def get_response(self, product_id: Union[None, str] = None) -> Dict:
        """
        Return products_info for `product_id`, or all available products
        if None is passed.
        """
        async with self.__awaitable_lock:
            if self.__response is None:
                resp = await self.__awaitable
                self.__awaitable = None
                helpers.check_response(resp)
                self.__response = resp.json()
                import pprint
                LOGGER.debug("ProductsInfo.get_response: %s",
                             pprint.pformat(self.__response))

        if product_id is None:
            return self.__response['data']
        else:
            return self.__response['data'][product_id]

    async def terminate(self):
        """
        This method should be awaited when destroying the object for a clean
        close.
        """
        if self.__response is None:
            async with self.__awaitable_lock:
                await self.__awaitable
        return None


class ProductBase:
    @JSONclass(annotations=True, annotations_type=True)
    class Base:
        id: str
        productTypeId: int

    class Info:
        """
        Must be overwritten and/or subclassed by subclasses of ProductBase.
        """
        name: str
        symbol: str
    base: Base
    info: Union[None, Info] = None

    def __init__(
            self, *,
            _product_info: ProductsInfo,
            **attributes: Dict[str, Any]):
        """
        Consider using `Product.init_bulk` to instantiate Products:
        API endpoint provides bulk request, batching will speed up your
        requests.

        id: str
            `id` is `id` attribute as returned by DegiroAPI. It is used
            to query Degiro endpoints for this product.
        """
        #if self.Info is ProductBase.Info:
        #    raise NotImplementedError(
        #        "ProductBase.Info must be overwritten by subclasses.")
        self.base = self.Base(attributes)
        self.__product_info_batch = _product_info
        self.__product_info = None


    @staticmethod
    def init_product(
            *,
            _product_info: ProductsInfo,
            productTypeId: Union[int, None] = None,
            **attributes: Dict[str, Any]):
        """
        Initialize adequate product specialization based on productTypeId.
        Default to ProductGeneric if no specialized implementation found for
        provided productTypeId.
        """
        params = dict(productTypeId=productTypeId, **attributes)
        LOGGER.debug("api.ProductBase.init_product| attributes %s", attributes)
        # Some attributes are not returned in a consistent way.
        # Manually fix the most important of them
        force_types = (('id', str),)
        for attr, loader in force_types:
            if attr in params:
                params[attr] = loader(params[attr])

        cls = {
            PRODUCT.TYPEID.CURRENCY: Currency,
            PRODUCT.TYPEID.STOCK: Stock
                }.get(
                        productTypeId,
                        ProductGeneric
                    )
        LOGGER.debug("api.ProductBase.init_product| class %s", cls)
        return cls(_product_info=_product_info,
                   **params)

    async def await_product_info(self) -> None:
        """
        Ensure we have received product_info attributes by awaiting this
        method.
        """
        if self.__product_info is None:
            self.__product_info = await self.__product_info_batch.get_response(
                    self.base.id)
            LOGGER.debug("ProductsInfo.await_product_info: %s",
                         self.__product_info)
            self.info = self.Info(self.__product_info)
            # Unreference batch when we don't need it anymore
            self.__product_info_batch = None
        return

    @classmethod
    def init_bulk(
            cls,
            session: SessionCore,
            attributes_iter: Iterable[Dict[str, Any]],
            batch_size=50
            ) -> List['Product']:
        """
        Bulk init Product instances.

        This is useful to do batch requests to populate additional attributes
        for Products.

        generator_output: bool
            If set to True, yield Products as they are instanciated

        Returns a List of Product instances
        """
        instances = []
        attributes_batch = []

        for ind, attributes in enumerate(attributes_iter, 1):
            attributes_batch.append(attributes)
            if ind % batch_size == 0:
                products_batch = cls._create_batch(session, attributes_batch)
                instances.extend(products_batch)
                attributes_batch.clear()

        if len(attributes_batch):
            instances.extend(cls._create_batch(session, attributes_batch))
        return instances

    @staticmethod
    def _create_batch(
            session: SessionCore,
            attributes_batch: Iterable[Dict[str, Any]]
            ) -> Iterable['ProductBase']:
        """
        Create Products and their common ProductsInfo.
        Returns an Iterable of Product instances.
        """
        ids_batch = [attrs['id'] for attrs in attributes_batch]
        products_info_batch = ProductsInfo(session, ids_batch)

        products_batch = map(
                lambda attrs: ProductBase.init_product(
                    _product_info=products_info_batch, **attrs),
                attributes_batch)
        return products_batch


class Currency(ProductBase):
    @JSONclass(annotations=True, annotations_type=True)
    class Info(ProductBase.Info):
        "Store Info calls return."
        # Must await .await_product_info() before use
        isin: str
        symbol: str
        name: str
        vwdId: Union[str, None] = None  # not set for non-tradable
        productType: str
        tradable: bool


class Stock(ProductBase):
    @JSONclass(annotations=True, annotations_type=True)
    class Info(ProductBase.Info):
        "Store Info calls return."
        # Must await .await_product_info() before use
        isin: str
        symbol: str
        name: str
        vwdId: Union[str, None] = None  # not set for non-tradable
        vwdIdentifierType: Union[str, None] = None  # not set for non-tradable
        productType: str
        tradable: bool
        category: str
        feedQuality: str

    class VwdIdentifierTypes(EnumStr):
        ISSUEID = 'issueId'
        VWDKEY = 'vwdkey'


class ProductGeneric(ProductBase):
    @JSONclass(annotations=True, annotations_type=True)
    class Base:
        id: str
        productTypeId: Union[None, int]  # sometimes not returned by API.

    @JSONclass(annotations=True, annotations_type=True)
    class Info(ProductBase.Info):
        "Store Info calls return."
        # Must await .await_product_info() before use
        isin: str
        symbol: str
        name: str
        tradable: bool
           

@JSONclass(annotations=True, annotations_type=True)
class TotalPortfolio:
    degiroCash: float
    flatexCash: float
    totalCash: float
    totalDepositWithdrawal: float
    todayDepositWithdrawal: float
    cashFundCompensationCurrency: str
    cashFundCompensation: float
    cashFundCompensationWithdrawn: float
    todayNonProductFees: float
    freeSpaceNew: Dict[str, float]  # Currency: value
    reportMargin: float
    reportCreationTime: str
    reportPortfValue: float
    reportCashBal: float
    reportNetliq: float
    reportOverallMargin: float
    reportTotalLongVal: float
    reportDeficit: float
    marginCallStatus: str
    """
    Total Portfolio

    Core parameters for total portfolio as returned per API.

    Any additional parameter will be set to the object to reflect
    up to date API changes.
    """


async def get_portfolio(
        session: SessionCore
        ) -> Tuple[TotalPortfolio, Iterable[ProductBase]]:
    """
    Returns (TotalPortfolio, Products). Refer to `TotalPortfolio` and
    `Products` classes for attributes available.
    """
    if session.config is None:
        await webapi.get_config(session)
    if session.client is None:
        await webapi.get_client_info(session)

    resp = await webapi.get_portfolio(session)
    resp_json = resp.json()
    portf_json = resp_json['portfolio']['value']
    portf_dict_json = [dict_from_attr_list(v['value'], ignore_error=True)
                       for v in portf_json]
    LOGGER.debug("api.get_portfolio| %s", pprint.pformat(portf_dict_json))

    portfolio = ProductBase.init_bulk(session, portf_dict_json)

    total_args = dict_from_attr_list(resp_json['totalPortfolio']['value'],
                                     ignore_error=True)
    total_portfolio = TotalPortfolio(total_args)

    return total_portfolio, portfolio


@JSONclass(annotations=True, annotations_type=True)
class PriceData:
    start: str
    end: str
    series: List[Dict[str, Union[list, float, str, int]]]
    resolution: str


@JSONclass(annotations=True, annotations_type=True)
class PriceSeries:
    type: str
    expires: str


class PriceSeriesObject(PriceSeries):
    """

    Example JSON answer

    """
# Example JSON Answer
# {'expires': '2022-02-04T19:31:38.7281028+01:00', 'data': {'issueId': 360114899, 'companyId': 1001, 'name': 'AIRBUS', 'identifier': 'issueid:360114899', 'isin': 'NL0000235190', 'alfa': 'AIR15598', 'market': 'XPAR', 'currency': 'EUR', 'type': 'AAN', 'quality': 'REALTIME', 'lastPrice': 110.32, 'lastTime': '2022-02-04T17:35:13', 'absDiff': -1.32, 'relDiff': -0.01182, 'highPrice': 112.16, 'highTime': '2022-02-04T09:01:36', 'lowPrice': 108.66, 'lowTime': '2022-02-04T14:34:47', 'openPrice': 111.94, 'openTime': '2022-02-04T09:00:12', 'closePrice': 111.94, 'closeTime': '2022-02-04T09:00:12', 'cumulativeVolume': 1209672.0, 'previousClosePrice': 111.64, 'previousCloseTime': '2022-02-03T17:36:47', 'tradingStartTime': '09:00:00', 'tradingEndTime': '17:40:00', 'tradingAddedTime': '00:10:00', 'lowPriceP1Y': 89.54, 'highPriceP1Y': 121.1, 'windowStart': '2022-02-04T00:00:00', 'windowEnd': '2022-02-04T17:35:13', 'windowFirst': '2022-02-04T09:00:00', 'windowLast': '2022-02-04T17:35:00', 'windowHighTime': '2022-02-04T09:01:00', 'windowHighPrice': 112.16, 'windowLowTime': '2022-02-04T14:34:00', 'windowLowPrice': 108.66, 'windowOpenTime': '2022-02-04T09:00:12', 'windowOpenPrice': 111.94, 'windowPreviousCloseTime': '2022-02-03T17:36:47', 'windowPreviousClosePrice': 111.64, 'windowTrend': -0.01182}, 'id': 'issueid:360114899', 'type': 'object'}
    @JSONclass(annotations=True, annotations_type=True)
    class Data:
        issueId: str
        companyId: Union[int, str]  # Depends on the alignment of planets.
        name: str
        currency: str
        market: str
        identifier: str
        isin: str
        alfa: str
        openTime: str
        closetime: str
        lowTime: str
        HighTime: str
        tradingStartTime: str
        tradingEndTime: str
        windowPreviousClosePrice: float
        windowLowPrice: float
        windowHighPrice: float


class PriceSeriesTime(PriceSeries):
    """
    Converted Wrapper for PriceSeriestime for get_price_data.
    """
    times: str
    data: Dict[str, List[Union[float, str]]]


async def get_price_data(
        session: SessionCore,
        product: Stock,
        resolution: PRICE.RESOLUTION = PRICE.RESOLUTION.PT1M,
        period: PRICE.PERIOD = PRICE.PERIOD.P1DAY,
        timezone: str = 'Europe/Paris',
        culture: str = 'fr-FR',
        data_type: PRICE.TYPE = PRICE.TYPE.PRICE
        ) -> PriceSeriesTime:
    """Single product get_price request, used by generic call."""
    # Ensure product got results of product_info
    if product.base.productTypeId != PRODUCT.TYPEID.STOCK:
        raise NotImplementedError(
            "Only productTypeId == PRODUCT.TYPEID.STOCK is currently "
            "supported by get_price_data")
    await product.await_product_info()
    resp = await webapi.get_price_data(
            session,
            vwdId=product.info.vwdId,
            vwdIdentifierType=product.info.vwdIdentifierType,
            resolution=resolution,
            period=period,
            timezone=timezone,
            culture=culture,
            data_type=data_type)
    resp_json = resp.json()
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
    return PriceSeriesTime(converted_time_series)


def convert_time_series(
        data_series: Dict[str, Union[str, List[Union[float, int]]]]
        ) -> Dict[str,
                  Union[
                      str,
                      Dict[str, Union[float, str]]]]:
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
    data_out = data_series.copy()

    for key in ('times', 'expires', 'data'):
        if key not in data_series:
            raise KeyError(f'{key} not found in data_series {data_series}')

    if resolution_t != PRICE.RESOLUTION.PT1M:
        raise NotImplementedError("convert_time_series has not been tested "
                                  "with other resolutions than PT1M.")

    data_new = {'price': [], 'date': []}
    data_out['data'] = data_new
    data_out['type'] = 'time'
    data_out['resolution'] = resolution_t
    data_out['times'] = time_t

    start_date = datetime.datetime.fromisoformat(time_t)
    for kv in data_series['data']:
        data_new['price'].append(kv[1])
        measure_date = start_date + datetime.timedelta(minutes=kv[0])
        data_new['date'].append(measure_date.isoformat())
    return data_out


async def get_price_data_batch(
        session: SessionCore,
        products: Union[Iterable[ProductBase], ProductBase],
        resolution: PRICE.RESOLUTION = PRICE.RESOLUTION.PT1D,
        period: PRICE.PERIOD = PRICE.PERIOD.P1DAY,
        timezone: str = 'Europe/Paris',
        culture: str = 'fr-FR',
        data_type: PRICE.TYPE = PRICE.TYPE.PRICE
        ):
    """
    Get price data for products. Be mindful that not all product types will

    >>>>
    """
    raise NotImplementedError  # Add helper around _get_price_data
    if isinstance(products, ProductBase):
        products = [products]

    for product in products:
        # Ensure product got results of product_info
        if product.productTypeId != PRODUCT.TYPEID.STOCK:
            raise NotImplementedError(
                "Only productTypeId == PRODUCT.TYPEID.STOCK is currently "
                "supported by get_price_data_bulk")
        await product.await_product_info()
        vwdId = product.vwdId
        prices_req.append(webapi.get_price_data(
                session,
                vwdId,
                resolution=resolution,
                period=period,
                timezone=timezone,
                culture=culture,
                data_type=data_type))


async def search_product(
        session: Session,
        *,
        by_text: Union[str, None] = None,
        by_isin: Union[str, None] = None,
        by_symbol: Union[str, None] = None,
        by_exchange: Union[str, Exchange, None] = None,
        product_type_id: Union[PRODUCT.TYPEID, None] = PRODUCT.TYPEID.STOCK,
        max_iter: Union[int, None] = 1000) -> List[ProductBase]:
    """
    Access `product_search` endpoint.

    Exactly one of `by_text`, `by_isin`, `by_symbol` be set.
    This is done because endpoint API doesn't return expected results
    with both text and ISIN search.

    `product_type_id`
        Restricts search to one type of products.
    `by_exchange`
        Restricts results to products in a exchange. Can be either an Exchange
        instance or an `hiqAbbr` (e.g. EPA for Paris, AEX for Amsterdam)

    Return a list of Product objects returned by Degiro for `search_txt`
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
        by_text = ' '.join(filter(lambda k: k is not None,
                                  (by_text, by_isin, by_symbol)))

    exchange_id = None
    if by_exchange is not None:
        if isinstance(by_exchange, Exchange):
            exchange_id = by_exchange.id
        elif isinstance(by_exchange, str):
            _check_session_exchange_dictionary(session)
            exchange = session.exchange_dictionary.exchange_by(
                    hiqAbbr=by_exchange)
            exchange_id = exchange.id
        else:
            raise TypeError(
                    "Only Exchange or str types supported for 'by_exchange'.")

    limit = 10
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

    for _ in range(max_iter):
        resp = await webapi.search_product(
                session,
                by_text,
                product_type_id=product_type_id,
                limit=limit,
                offset=offset)
        resp_json = resp.json()
        LOGGER.debug("api.search_product response| %s",
                     pprint.pformat(resp_json))
        if 'products' in resp_json:
            products_json = resp_json['products']
            batch = ProductBase.init_bulk(session,
                                          filter(__custom_filter,
                                                 products_json))
            # This could be optimized later on with a generator class to be
            # able to yield data as soon as we receive it while still not
            # blocking further calls to be launched, should it be needed.
            products += batch
            if len(batch) < limit:
                break
            else:
                offset += len(batch)
        else:
            break
    return products


async def login(
        credentials: Credentials,
        session: Union[Session, None] = None) -> Session:
    """
    Authentify with Degiro API and populate basic information that'll be needed
    for further calls.

    `session` will be updated with required data for further connections.

    Strictly equivalent to:

    >>>> session = await degiroasync.webapi.login(credentials)
    >>>> await webapi.get_config(session)
    >>>> await webapi.get_client_info(session)

    If no `session` is provided, create one.
    """
    if session is None:
        session = Session()
    await webapi.login(credentials, session)
    await webapi.get_config(session)
    await webapi.get_client_info(session)
    await get_exchange_dictionary(session)
    return session


def _check_session_exchange_dictionary(session: Session):
    """
    Check that session exchange dictionary has been populated.
    Raise AssertionError if not.
    """
    if session.exchange_dictionary is None:
        raise AssertionError(
                "session.exchange_dictionary is not set. "
                "Use api.login to build your session or call "
                "api.get_exchange_dictionary on it.")


async def get_exchange_dictionary(session: Session) -> Session:
    """
    Populate session with exchange_dictionary.
    """
    session.exchange_dictionary = await ExchangeDictionary(session)
    return session


__all__ = [
    obj.__name__ for obj in (
        # Login & setup
        login,
        Credentials,
        Session,
        SessionCore,
        Config,
        ExchangeDictionary,

        # Product data structures
        PriceData,
        Stock,
        Currency,
        ProductBase,

        get_portfolio,
        get_price_data,
        get_exchange_dictionary,
        search_product
        )
        ]
