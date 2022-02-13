from typing import Any, Union, List, Dict, Tuple
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
from ..core import TRANSACTIONS


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

# {'id': 182722888, 'productId': 65153, 'date': '2020-02-07T09:00:10+01:00', 'buysell': 'B', 'price': 36.07, 'quantity': 20, 'total': -721.4, 'orderTypeId': 0, 'counterParty': 'MK', 'transfered': False, 'fxRate': 0, 'totalInBaseCurrency': -721.4, 'feeInBaseCurrency': -0.29, 'totalPlusFeeInBaseCurrency': -721.69, 'transactionTypeId': 0, 'tradingVenue': 'XPAR'})

@JSONclass(annotations=True, annotations_type=True)
class Transaction:
    id: str
    product: ProductBase
    date: datetime.datetime
    buysell: ORDER.ACTION
    price: float
    quantity: float
    total: float
    transfered: bool
    fxRate: float
    totalInBaseCurrency: float
    totalPlusFeeInBaseCurrency: float

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
        ) -> Tuple[List[Order]]:
    """
    Get current orders and history.

    to_date:
        Request orders history up to `to_date`. Defaults to today.
    from_date:
        Request orders history from `from_date`. Defaults to today - 7 days.

    Return current_orders, historical_orders.

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
    return (
            [Order(o) for o in orders_dict],
            [Order(o) for o in orders_history_dict]
           )


async def get_transactions(
        session: SessionCore,
        from_date: Union[datetime.datetime, None] = None,
        to_date: Union[datetime.datetime, None] = None
        ) -> List[Order]:
    """
    Get transactions for `session`.

    from_date:
        Request transactions from `from_date`. Defaults to `to_date - 7 days`.

    to_date:
        Request transactions to `to_date`. Defaults to today.
    """
    to_date = to_date or datetime.datetime.today()
    from_date = from_date or to_date - datetime.timedelta(days=7)

    resp = await webapi.get_transactions(
            session,
            from_date=from_date.strftime(webapi.ORDER_DATE_FORMAT),
            to_date=to_date.strftime(webapi.ORDER_DATE_FORMAT)
            )
    data = resp.json()['data'].copy()
    products = ProductBase.init_bulk(
            session,
            map(lambda t: {'id': str(t['productId'])}, data))

    async def _build_transaction(prod, trans):
        await prod.await_product_info()
        trans.update(dict(
            id=str(trans['id']),
            product=prod,
            date=datetime.datetime.fromisoformat(trans['date']),
            buysell={'B': ORDER.ACTION.BUY,
                     'S': ORDER.ACTION.SELL}[trans['buysell']],
                ))
        return Transaction(trans)

    transactions = await asyncio.gather(*[_build_transaction(p, t)
                                          for p, t in zip(products, data)])
    return transactions
    #for prod, trans in zip(products, data):
        #await prod.await_product_info()
        #trans.update(dict(
        #    id=str(trans['id']),
        #    product=prod,
        #    date=datetime.datetime.strptime(trans['date']),
        #    buysell={'B': ORDER.ACTION.BUY,
        #             'S': ORDER.ACTION.SELL}[trans['buysell']],
        #    counterParty={
        #        'MK': TRANSACTIONS.COUNTERPARTY.MARKET,
        #        'GR': TRANSACTIONS.COUNTERPARTY.GROUP,
        #        'DG': TRANSACTIONS.COUNTERPARTY.DEGIRO
        #        }
        #        ))
        #transaction = Transaction(trans)
