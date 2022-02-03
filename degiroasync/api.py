from typing import Iterable, Any, List, Dict, Tuple, Callable, Union
import dataclasses
import logging
import pprint
from collections.abc import Awaitable
import time
import functools
import asyncio
import pprint
import datetime

from .constants import DegiroStatus
from .constants import ProductConst
from .constants import PriceConst
from . import webapi
from .webapi import login
from .core import LOGGER_NAME
from .core import Credentials, Session, URLs, Config, PAClient
#from .jsonwrapper import JSONWrapper
from .helpers import set_params
from .helpers import dict_from_attr_list
from .helpers import setattrs
from .helpers import run_in_new_thread
from .helpers import check_keys
from degiroasync import helpers
from degiroasync import constants
from jsonloader import JSONclass, JSONWrapper


LOGGER = logging.getLogger(LOGGER_NAME)


class ProductsInfo:
    # TODO: assess if it would be useful to create a generic batch class
    def __init__(self, session: Session, products_ids: List[str]):
        "Takes a non-awaited get_products_info call."
        self.__awaitable = webapi.get_products_info(session, products_ids)
        self.__response = None
        self.__awaitable_lock = asyncio.Lock()

    async def get_response(self, product_id: Union[None, str]=None) -> Dict:
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
                LOGGER.debug("ProductsInfo.get_response: %s", pprint.pformat(self.__response))

        if product_id is None:
            return self.__response['data']
        else:
            return self.__response['data'][product_id]


    async def terminate(self):
        """
        This method should be awaited when destroying the object for a clean close.
        """
        if self.__response is None:
            await self.__request
        return None


class Product:
    @JSONclass(annotations=True, annotations_type=True)
    class Base:
        id: str
        price: float
        size: int
        value: float

    @JSONclass(annotations=True, annotations_type=True)
    class Info:
        "Store Info calls return."
        # Must await .await_product_info() before use
        isin: str
        symbol: str
        name: str
        vwdId: str
        productType: str

    info: Union[None, Info] = None
    base: Base


    def __getattr__(self, attr: str) -> Union[str, float, int, Dict]:
        """
        This method is called if `attr` was not found in object.

        This can legitimately happen if `attr` is expected to be provided by
        a `webapi.get_products_info` call.
        In which case, `.await_product_info`
        method class should be called before accessing such an attribute to
        ensure we have received an answer: if we have not received an answer to
        this product info request, raises `RuntimeError`.

        If we have received an answer to this product info request but `attr`
        is still not found, raises `AttributeError`.
        """
        # TODO: Remove commented code once external behavior is validated
        # and locked.
        # Only called if attribute not found.
        # This might be an additional attribute from product_info 
        # Wait for product info to be populated
        #import asyncio
        #loop = asyncio.get_event_loop()
        #def _product_info():
        #loop.shutdown_asyncgens(self.await_product_info)
        #self.wait_product_info()
        if self.__product_info is None:
            raise RuntimeError(f"{attr} not found in {self}."
                    " Additional product info not received yet. Try await .await_product_info().")
        elif attr in self.__product_info:
            return self.__product_info[attr]
        else:
            raise AttributeError(f"{attr} not found in {self}. "
                    "This could be triggered by an API change. "
                    " product_info: {}".format(pprint.pformat(self.__product_info)))
                
    @staticmethod
    def _create_batch(
            session: Session,
            attributes_batch: Iterable[Dict[str, Any]]
            ) -> Iterable[Any]:
        """
        Create Products and their common ProductsInfo.
        Returns an Iterable of Product instances.
        """
        ids_batch = [attrs['id'] for attrs in attributes_batch]
        #ids_batch = map(lambda attrs: attrs['id'], attributes_batch) 
        products_info_batch = ProductsInfo(session, ids_batch)
        products_batch = map(
                lambda attrs: Product(
                    product_info=products_info_batch, **attrs),
                attributes_batch) 
        return products_batch

    @classmethod
    def init_bulk(cls,
            session: Session,
            attributes_iter: Iterable[Dict[str, Any]],
            batch_size=50
            ) -> List[Any]:
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
            #TODO: remove this commented section when support for JSONclass
            # is fixed.
            #check_keys(attributes, cls.MINIMUM_ATTRIBUTES)
            attributes_batch.append(attributes)
            if ind % batch_size == 0:
                products_batch = cls._create_batch(session, attributes_batch)
                instances.extend(products_batch)
                attributes_batch.clear()

        if len(attributes_batch):
            instances.extend(cls._create_batch(session, attributes_batch))
        return instances

    def __init__(self, *,
            id: str,
            product_info: ProductsInfo,
            **kwargs):
        """
        Consider using `Product.init_bulk` to instantiate Products: API endpoint
        provides bulk request, batching will speed up your requests.

        id: str
            `id` is `id` attribute as returned by DegiroAPI. It is used
            to query Degiro endpoints for this product.
        """
        self.id = id  # we can't do anything without this one
        setattrs(self, **kwargs)
        self.__product_info_batch = product_info
        self.__product_info = None

    async def await_product_info(self) -> None:
        """
        Ensure we have received product_info attributes by awaiting this method.
        """
        if self.__product_info is None:
            self.__product_info = await self.__product_info_batch.get_response(self.id)
            LOGGER.debug("ProductsInfo.wait_product_info: %s", self.__product_info)
            # Unreference batch when we don't need it anymore
            self.__product_info_batch = None
        return

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


#class TotalPortfolio:
#    def __init__(self, 
#        *,
#        degiroCash: float,
#        flatexCash: float,
#        totalCash: float,
#        totalDepositWithdrawal: float,
#        todayDepositWithdrawal: float,
#        cashFundCompensationCurrency: str,
#        cashFundCompensation: float,
#        cashFundCompensationWithdrawn: float,
#        todayNonProductFees: float,
#        freeSpaceNew: float,
#        reportMargin: float,
#        reportCreationTime: str,
#        reportPortfValue: float,
#        reportCashBal: float,
#        reportNetliq: float,
#        reportOverallMargin: float,
#        reportTotalLongVal: float,
#        reportDeficit: float,
#        marginCallStatus: str,
#        **kwargs
#        ):
#        """
#        Total Portfolio
#
#        Core parameters for total portfolio as returned per API.
#        
#        Any additional parameter will be set to the object to reflect
#        up to date API changes.
#        """
#        # Optional args
#        setattrs(self, **kwargs)
#        # Set mandatory args
#        args = locals().copy()
#        del args['self']
#        del args['kwargs']
#        setattrs(self, **args)


async def get_portfolio(session: Session
        ) -> Tuple[TotalPortfolio, Iterable[Product]]:
    """
    Returns (TotalPortfolio, Products). Refer to `TotalPortfolio` and `Products`
    classes for attributes available.
    """
    if session.config is None:
        await webapi.get_config(session)
    if session.client is None:
        await webapi.get_client_info(session)

    resp = await webapi.get_portfolio(session)
    resp_json = resp.json()
    portf_json = resp_json['portfolio']['value']

    portfolio = Product.init_bulk(session, (dict_from_attr_list(value['value'],
        ignore_error=True) for value in portf_json))
    #portfolio = (set_params(Product(), value['value'], ignore_error=True)
    #        for value in portf_json)

    total_args = dict_from_attr_list(resp_json['totalPortfolio']['value'],
            ignore_error=True)
    total_portfolio = TotalPortfolio(total_args) 

    return total_portfolio, portfolio


#@JSONclass(annotations=True, annotations_type=True)
class PriceData(JSONWrapper):
    start: str
    end: str
    series: List[Dict[str, Union[float, str, int]]]
    resolution: str


    MINIMUM_ATTRIBUTES = ('series', 'resolution', 'start', 'end')
    def __init__(self, **kwargs):
        check_keys(kwargs, *self.MINIMUM_ATTRIBUTES)
        super().__init__(**kwargs)


@JSONclass(annotations=True, annotations_type=True)
class InputTimeSeriesPrice:
    "Structure for straight out of Degiro API Price TimeSeries"
    times: str
    expires : str
    data: List[List[Union[int, float]]]

class PriceTimeSeries:
    pass  # TODO: Currently not used


async def get_price_data(
        session: Session,
        products: Union[Iterable[Product], Product],
        resolution: PriceConst.Resolution = PriceConst.Resolution.PT1D,
        period: PriceConst.Period = PriceConst.Period.P1DAY,
        timezone: str = 'Europe/Paris',
        culture: str = 'fr-FR',
        data_type: PriceConst.Type = PriceConst.Type.PRICE
        ) -> JSONWrapper:
        # Ensure product got results of product_info
        await product.await_product_info()
        resp = await webapi.get_price_data(session,
                product.vwdId,
                resolution=resolution,
                period=period,
                timezone=timezone,
                culture=culture,
                data_type=data_type)
        check_response(resp)
        resp_json = resp.json()
        # TODO:  rework/check & update PriceData
        timeseries = _TimesSeriesPrice(resp_json)
        del resp_json
        #check_keys(resp_json, PriceData.MINIMUM_ATTRIBUTES)
        del resp
        data = PriceData(resp_json)
        # double check we have the right company
        
        if data.resolution != resolution:
            raise RuntimeError(
                    "Returned resolution {} different from input resolution {}.".format(data.resolution, resolution))

        # make time series pandas friendly
        series = data.series
        filtered = tuple(filter(lambda s: 'time' in s ))
        if not len(timeseries):
            raise KeyError(
                    "'time' timeseries not found in response: {}".format(resp_json))
        timeseries = filtered[0]
        


        # Return as is or build a dataframe


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

    if resolution_t != PriceConst.Resolution.PT1M:
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


async def get_price_data_bulk(
        session: Session,
        products: Union[Iterable[Product], Product],
        resolution: PriceConst.Resolution = PriceConst.Resolution.PT1D,
        period: PriceConst.Period = PriceConst.Period.P1DAY,
        timezone: str = 'Europe/Paris',
        culture: str = 'fr-FR',
        data_type: PriceConst.Type = PriceConst.Type.PRICE
        ):
    """
    Get price data for products. Be mindful that not all product types will
    have 

    >>>  
    """
    if isinstance(products, Product):
        products = [products]

    for product in products:
        # Ensure product got results of product_info
        if product.productType != ProductConst.Type.STOCKS:
            raise NotImplementedError(
                "Only productType == 'STOCKS' is currently supported by get_price_data_bulk")
        await product.await_product_info()
        vwdId = product.vwdId
        prices_req.append(webapi.get_price_data(session,
                vwdId,
                resolution=resolution,
                period=period,
                timezone=timezone,
                culture=culture,
                data_type=data_type))
        


__all__ = [
    obj.__name__ for obj in (
        login,
        Credentials,
        Session,
        Config,
        PriceData,
        Product,
        get_portfolio,
        webapi.get_config,
        webapi.get_client_info
        )
        ]

