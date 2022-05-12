from typing import Any, Union, List, Dict, Tuple, Optional
import datetime
import logging
import asyncio
import itertools

from jsonloader import JSONclass

from .product import ProductBase
from .product import ProductFactory
from .. import webapi
from ..core import SessionCore
from ..core import ORDER
from ..core import TRANSACTION
from ..core import LOGGER_NAME
from ..core import camelcase_dict_to_snake
from ..core.helpers import dict_from_attr_list


LOGGER = logging.getLogger(LOGGER_NAME)


@JSONclass(annotations=True, annotations_type=True)
class Order:
    order_id: Optional[str] = None  # Can be None if STATUS == REJECTED
    product_id: str
    size: Union[float, int]
    price: float
    buysell: ORDER.ACTION
    order_type_id: int
    order_time_type_id: int

    # product: Union[ProductBase, None] = None  # do we want to reinstantiate
    # products here or let user?
    #: Creation date of the order, not always available for "Outstanding".
    created: Optional[str] = None

    current_traded_size: int = 0
    total_traded_size: int = 0
    # 'CREATE' or ... ?
    type: Optional[str] = None
    is_active: bool

    #: Not always available for "Outstanding" orders
    status: Optional[ORDER.STATUS] = None

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
    fx_rate: float
    total_in_base_currency: float
    total_plus_fee_in_base_currency: float
    total_plus_all_fees_in_base_currency: float
    transaction_type_id: Union[TRANSACTION.TYPEID, int]

# Raw JSON Example
# {"id":335133382,"productId":8615503,"date":"2022-02-26T00:00:00+01:00","buysell":"S","price":134.6600,"quantity":-40,"total":5386.4000000000,"transfered":true,"fxRate":0,"nettFxRate":0,"grossFxRate":0,"autoFxFeeInBaseCurrency":0,"totalInBaseCurrency":5386.4000000000,"totalFeesInBaseCurrency":0,"totalPlusFeeInBaseCurrency":5386.4000000000,"totalPlusAllFeesInBaseCurrency":5386.4000000000,"transactionTypeId":20


async def confirm_order():
    """
    Not implemented. Use webapi.confirm_order.
    """
    raise NotImplementedError


async def check_order(
        session: SessionCore,
        *,
        product: ProductBase,
        buy_sell: ORDER.ACTION,
        time_type: ORDER.TIME,
        order_type: ORDER.TYPE,
        size: int,
        price: Union[float, None] = None,
        ) -> Dict[str, Any]:
    """
    This must be called to obtain a confirmation_id prior to confirming an
    order.

    This can also be used to get an order fees before confirming the order.

    .. code-block:: python

        # Get your products through search_product
        check_order(
            product=product,
            buy_sell=ORDER.ACTION.SELL,
            time_type=ORDER.TIME,
            order_type=ORDER.TYPE,
            size=1,
            price=100
        )

    WARNING: This call is rate limited at the end-point level, tests would show
    the call to be rate limited at 1 per second. Users should throttle their
    calls to this function.

    Example return:

    .. code-block:: python

        {
            'confirmation_id': '0f404158-3628-414b-87fc-91e2ab2ba1ee',
            'free_space_new': 62283.1,
            'transaction_fee': 0.5,
            'show_ex_ante_report_link': True
        }

    In the case of a SELL order, the parameter 'transaction_opposite_fee'
    has also been observed. It does not seem to serve a differente purpose
    than transaction_fee.
    """
    assert isinstance(buy_sell, ORDER.ACTION)

    resp_json = await webapi.check_order(
        session=session,
        product_id=product.base.id,
        buy_sell=buy_sell,
        time_type=time_type,
        order_type=order_type,
        size=size,
        price=price
    )
    return camelcase_dict_to_snake(resp_json['data'])


async def get_orders(
        session: SessionCore,
        from_date: Union[datetime.datetime, None] = None,
        to_date: Union[datetime.datetime, None] = None,
        ) -> Tuple[List[Order]]:
    """
    Get current orders and history.

    to_date
        Request orders history up to `to_date`. Defaults to today.
    from_date
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

    LOGGER.debug(
            "get_orders orders_current_resp| %s",
            orders_current_resp)
    orders_dict = orders_current_resp['orders']
    del orders_current_resp
    for order in orders_dict:
        if 'isActive' not in order and 'created' not in order:
            # If no information and not created, consider order not active.
            # It was chosen to mark isActive = False explicitly instead of
            # having an Optional is_active attribute as a None might easily
            # be misinterpreted as False by clients.
            order['isActive'] = False

    orders_history_dict = orders_history_resp['data']
    LOGGER.debug("get_orders orders_dict| %s", orders_dict)
    LOGGER.debug("get_orders orders_history_dict| %s", orders_history_dict)
    # Ensure types expected types & set constants.
    for order in itertools.chain(orders_dict, orders_history_dict):
        order['productId'] = str(order['productId'])
        order['buysell'] = {
            'B': ORDER.ACTION.BUY,
            'S': ORDER.ACTION.SELL
        }[order['buysell']]
        if 'status' in order:
            order['status'] = {
                'CONFIRMED': ORDER.STATUS.CONFIRMED,
                'REJECTED': ORDER.STATUS.REJECTED,
                'PENDING': ORDER.STATUS.PENDING
                    }[order['status']]
    # 2022.03 mypy does not handle __new__ well, ignore for now.
    return (
        [Order(camelcase_dict_to_snake(o))  # type: ignore
            for o in orders_dict],
        [Order(camelcase_dict_to_snake(o))  # type: ignore
            for o in orders_history_dict]
    )


async def get_transactions(
        session: SessionCore,
        from_date: Union[datetime.datetime, None] = None,
        to_date: Union[datetime.datetime, None] = None
        ) -> List[Transaction]:
    """
    Get transactions for `session`.

    from_date
        Request transactions from `from_date`. Defaults to `to_date - 7 days`.

    to_date
        Request transactions to `to_date`. Defaults to today.
    """
    to_date = to_date or datetime.datetime.now()
    from_date = from_date or to_date - datetime.timedelta(days=7)

    resp = await webapi.get_transactions(
        session,
        from_date=from_date.strftime(webapi.ORDER_DATE_FORMAT),
        to_date=to_date.strftime(webapi.ORDER_DATE_FORMAT)
    )
    data = resp['data'].copy()
    products_gen = ProductFactory.init_batch(
        session,
        map(lambda t: {'id': str(t['productId'])}, data))
    products = [p async for p in products_gen]
    del products_gen

    async def _build_transaction(prod, trans):
        trans.update(dict(
            id=str(trans['id']),
            product=prod,
            date=datetime.datetime.fromisoformat(trans['date']),
            buysell={'B': ORDER.ACTION.BUY,
                     'S': ORDER.ACTION.SELL}[trans['buysell']],
        ))
        return Transaction(camelcase_dict_to_snake(trans))

    transactions = await asyncio.gather(*[_build_transaction(p, t)
                                          for p, t in zip(products, data)])
    return transactions
