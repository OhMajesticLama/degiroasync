from typing import Any, Union, List, Dict
import functools
import datetime
import logging
import asyncio

from jsonloader import JSONclass

from .product import ProductBase
from .. import webapi
from ..core import SessionCore
from ..core import ORDER
from ..core import LOGGER_NAME


LOGGER = logging.getLogger(LOGGER_NAME)


@JSONclass(annotations=True, annotations_type=True)
class Order:
    created: str
    orderId: str
    productId: str
    size: Union[float, int]
    price: float
    buysell: str  # 'B' or 'S'
    orderTypeId: int
    orderTimeTypeId: int
    currentTradedSize: int
    totalTradedSize: int
    type: str  # 'CREATED' or ...?
    isActive: bool
    status: str  # 'REJECTED' or ...?
    #product: Union[ProductBase, None] = None  # do we want to reinstantiate
                                               # products here or let user?


async def submit_order():
    raise NotImplementedError


@functools.wraps(webapi.check_order)
async def check_order(
        session: SessionCore,
        *,
        product: ProductBase,
        buy_sell: str,
        time_type: ORDER.TIME,
        order_type: ORDER.TYPE,
        size: int,
        price: Union[float, None] = None,
        ) -> Any:

    response = await webapi.check_order(
        session=session,
        product_id=product.base.id,
        buy_sell=buy_sell,
        time_type=time_type,
        order_type=order_type,
        size=size,
        price=price
            )
    resp_json = response.json()
    return resp_json


async def get_orders(
        session: SessionCore,
        from_date: Union[datetime.datetime, None] = None,
        to_date: Union[datetime.datetime, None] = None,
        ) -> Dict[str, List[Order]]:
    """
    Get current orders and history.

    to_date:
        Request orders history up to `to_date`. Defaults to today.
    from_date:
        Request orders history from `from_date`. Defaults to today - 7 days.

    """
    if to_date is None:
        to_date = datetime.datetime.today()
    if from_date is None:
        from_date = to_date - datetime.timedelta(days=7)

    orders_current_resp, orders_history_resp = await asyncio.gather(
        webapi.get_orders(session),
        webapi.get_orders_history(
            session,
            from_date=from_date.strftime(webapi.ORDER_DATE_FORMAT),
            to_date=to_date.strftime(webapi.ORDER_DATE_FORMAT))
            )

    orders_dict = orders_current_resp.json()['orders']['value']
    orders_history_dict = orders_history_resp.json()['data']
    LOGGER.debug("get_orders orders_dict| %s", orders_dict)
    LOGGER.debug("get_orders orders_history_dict| %s", orders_history_dict)
    for order_list in (orders_dict, orders_history_dict):
        for order in order_list:
            order['productId'] = str(order['productId'])
    return {
            'orders': [Order(o) for o in orders_dict],
            'ordersHistory': [Order(o) for o in orders_history_dict]
           }
