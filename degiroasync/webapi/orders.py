import logging
from typing import Union, Dict, Any
import datetime

import httpx

from .product import get_trading_update
from ..core import SessionCore
from ..core import URLs
from ..core import constants
from ..core import ORDER
from ..core.constants import TIMEOUT
from ..core import join_url
from ..core import check_session_client
from ..core import check_session_config
from ..core.helpers import check_response
from ..core.helpers import dict_from_attr_list


LOGGER = logging.getLogger(constants.LOGGER_NAME)


async def confirm_order(
        session: SessionCore,
        *,
        confirmation_id: str,
        product_id: str,
        buy_sell: str,
        time_type: ORDER.TIME,
        order_type: ORDER.TYPE,
        size: int,
        price: Union[float, None] = None,
):
    """
    Close the placing order process. This is used after `check_order`
    to confirm placing an order. It must be called with the same paramaters
    and the confirmation_id obtained with `check_order`.

    buy_sell:
        One of ('BUY', 'SELL').

    price:
        Price in currency of the product.

    product_id:
        Product on which to place the order.

    order_type:
        Specify if we want a STOP_LIMITED, MARKET_ORDER, STOP_LOSS,
        STOP_LIMITED.

    time_type:
        Specify if we want a DAY or PERMANENT order.

    Check `degiroasync.core.ORDER` for details.

    Example data with request:
    ```
    {
        "buySell": "BUY",
        "orderType": 0,
        "price": 10,
        "productId": "96008",
        "size": 1,
        "timeType": 1
    }
    ```

    Example JSON response:
    ```
    # TODO: Next time we place an order
    {'data': {'confirmationId': 'a8e49a7e-4d79-4f21-961b-988dc0806d09', 'freeSpaceNew': 55395, 'transactionFee': 0.5, 'showExAnteReportLink': True}}

    ```
    """
    # This call will not have integration tests to prevent misplaced orders
    # All changes must be manually verified to work as intended.
    _order_calls_check(session,
                       product_id=product_id,
                       buy_sell=buy_sell,
                       time_type=time_type,
                       order_type=order_type,
                       size=size,
                       price=price)

    jsession_id = session._cookies[session.JSESSIONID]

    url = join_url(
        URLs.get_confirm_order_url(session),
        confirmation_id
    )
    url += f';{jsession_id}'

    params = dict(
        intAccount=session.client.int_account,
        sessionId=jsession_id
    )
    data = dict(
        buySell=buy_sell,
        orderType=order_type,
        price=price,
        productId=product_id,
        timeType=time_type
    )

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            url,
            params=params,
            json=data,
        )
    check_response(response)
    resp_json = response.json()
    LOGGER.debug("check_order| %s", resp_json)
    return resp_json


def _order_calls_check(
        session: SessionCore,
        *,
        product_id: str,
        buy_sell: str,
        time_type: ORDER.TIME,
        order_type: ORDER.TYPE,
        size: int,
        price: Union[float, None] = None,
):
    check_session_config(session)
    check_session_client(session)

    # We're a bit more strict than usual in type checking here: it's really
    # *not* the place where we want to give room and flexibility to users
    # in exchange of safety.
    if not isinstance(order_type, ORDER.TYPE):
        raise TypeError("order_type must be an ORDER.TYPE")

    if not isinstance(time_type, ORDER.TIME):
        raise TypeError("order_type must be an ORDER.TIME")

    if order_type != ORDER.TYPE.MARKET_ORDER and price is None:
        raise AssertionError("price must not be None for orders that are not "
                             "MARKET_ORDER.")


async def check_order(
        session: SessionCore,
        *,
        product_id: str,
        buy_sell: str,
        time_type: ORDER.TIME,
        order_type: ORDER.TYPE,
        size: int,
        price: Union[float, None] = None,
) -> Dict[str, Any]:
    """
    Start the placing order process. This is used to retrieve order
    cost for instance and is mandatory to actually place an order with
    `confirm_order`.

    buy_sell:
        One of ('BUY', 'SELL').

    price:
        Price in currency of the product.

    product_id:
        Product on which to place the order.

    order_type:
        Specify if we want a STOP_LIMITED, MARKET_ORDER, STOP_LOSS,
        STOP_LIMITED.

    time_type:
        Specify if we want a DAY or PERMANENT order.

    Check `degiroasync.core.ORDER` for details.

    Example data with request:
    ```
    {
        "buySell": "BUY",
        "orderType": 0,
        "price": 10,
        "productId": "96008",
        "size": 1,
        "timeType": 1
    }
    ```

    Example JSON response:
    ```
    {
        "data": {
            "confirmationId": "c64332f0-a800-4f04-bc29-12a2b7efa20b",
            "freeSpaceNew": 2282.0,
            "showExAnteReportLink": true,
            "transactionFee": 0.5
        }

    }
    ```
    """
    if buy_sell not in ("BUY", "SELL"):
        raise AssertionError("buy_sell not 'BUY' or 'SELL'")
    LOGGER.debug("webapi.check_order| %s", str(buy_sell))
    _order_calls_check(session,
                       product_id=product_id,
                       buy_sell=buy_sell,
                       time_type=time_type,
                       order_type=order_type,
                       size=size,
                       price=price)

    jsessionid = session._cookies[session.JSESSIONID]

    url = URLs.get_check_order_url(session)
    params = dict(
        intAccount=session.client.int_account,
        sessionId=jsessionid
    )
    data = dict(
        buySell=buy_sell,
        orderType=order_type,
        price=price,
        productId=product_id,
        size=size,
        timeType=time_type
    )
    LOGGER.debug("check_order data| %s", data)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            url,
            params=params,
            json=data,
            headers={
                'content-type': 'application/json;charset=UTF-8'
            },
            cookies=session._cookies
        )
    check_response(response)
    resp_json = response.json()
    LOGGER.debug("check_order| %s", resp_json)
    return response.json()


async def get_orders(session: SessionCore) -> Dict[str, Any]:
    """
    Get current and historical orders.

    Example response:

    {'orders': [
        {
        'id': '52401b7d-00ed-4aed-979d-a2476e331b26',
        'date': '2022-05-12T15:08:33',
        'productId': 255931,
        'product': 'Veolia Environnement',
        'contractType': 1,
        'contractSize': 1.0,
        'currency': 'EUR',
        'buysell': 'B',
        'size': 100.0,
        'quantity': 100.0,
        'price': 24.7,
        'stopPrice': 0.0,
        'totalOrderValue': 2470.0,
        'orderTypeId': 0,
        'orderTimeTypeId': 1,
        'orderType': 'LIMIT',
        'orderTimeType': 'DAY',
        'isModifiable': True,
        'isDeletable': True
        }]
    }

    """
    # TODO: assess if historicalOrders is relevant here
    # or if it should be removed and we should only rely on get_orders_history
    orders = await get_trading_update(
        session,
        params={
            'orders': 0,
            }
            #'historicalOrders': 0}
    )
    LOGGER.debug("webapi.get_orders| orders %s", orders)
    orders = {
            'orders': [
                dict_from_attr_list(order['value'])
                for order in orders['orders']['value']
                if order['name'] == 'order'
                ]
            }
    LOGGER.debug("webapi.get_orders| orders rebuilt %s", orders)
    return orders


ORDER_DATE_FORMAT = '%d/%m/%Y'


async def get_orders_history(
        session: SessionCore,
        from_date: str,
        to_date: str,
) -> Dict[str, Any]:
    """
    Get historical orders for session.

    from_date:
        Date in format DD/MM/YYYY. Raise ValueError if incorrect format.
    to_date:
        Date in format DD/MM/YYYY. Raise ValueError if incorrect format.

    Example return in json():
    ```
    {
        'data': {
            [
                {
                    'created': '2021-11-05T11:56:33+01:00',
                    'orderId': 'asdfjkhrewqrkljh',
                    'productId': 12341234,
                    'size': 100,
                    'price': 390,
                    'buysell': 'B',
                    'orderTypeId': 1,
                    'stopPrice': 0,
                    'currentTradedSize': 0,
                    'totalTradedSize': 0,
                    'type': 'CREATE',
                    'status': 'CONFIRMED',
                    'last': '2021-11-6T12:33:23+01:00',
                    'isActive': True
                }
            ]
        }
    }
    ```
    """
    check_session_config(session)
    check_session_client(session)
    # Check date format, datetime will raise an exception
    datetime.datetime.strptime(from_date, ORDER_DATE_FORMAT)
    datetime.datetime.strptime(to_date, ORDER_DATE_FORMAT)

    jsessionid = session._cookies[session.JSESSIONID]

    url = URLs.get_orders_history_url(session)
    params = dict(
        fromDate=from_date,
        toDate=to_date,
        intAccount=session.client.int_account,
        sessionId=jsessionid
    )

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            url,
            params=params,
            headers={
                'content-type': 'application/json'
            },
            cookies=session._cookies
        )
    check_response(response)
    resp_json = response.json()
    LOGGER.debug("get_orders_history| %s", resp_json)
    return response.json()


async def get_transactions(
        session: SessionCore,
        from_date: str,
        to_date: str,
) -> Dict[str, Any]:
    """
    Get transactions for session.

    from_date:
        Date in format DD/MM/YYYY. Raise ValueError if incorrect format.
    to_date:
        Date in format DD/MM/YYYY. Raise ValueError if incorrect format.

    Example return in json():
    ```
    {
        'data': {
            [
                {
                    'id': 123123,
                    'productId': 12341234,
                    'date': '2021-11-05T11:56:33+01:00',
                    'buysell': 'B',
                    'price': 39,
                    'quantity': 100,
                    'total': -3900,
                    'orderTypeId': 1,
                    'counterParty': 1,
                    'transfered': False,
                    'fxRate': 0,
                    'totalInBaseCurrency': -3900,
                    'feeInBaseCurrency': -12,
                    'totalPlusFeeInBaseCurrency': -3912,
                    'transactionTypeId': -3912,
                    'tradingVenue': -3912,
                }
            ]
        }
    }
    ```
    """
    check_session_config(session)
    check_session_client(session)
    # Check date format, datetime will raise an exception
    datetime.datetime.strptime(from_date, ORDER_DATE_FORMAT)
    datetime.datetime.strptime(to_date, ORDER_DATE_FORMAT)

    jsessionid = session._cookies[session.JSESSIONID]

    url = URLs.get_transactions_url(session)
    params = dict(
        fromDate=from_date,
        toDate=to_date,
        intAccount=session.client.int_account,
        sessionId=jsessionid,
        groupTransactionsByOrder=False
    )

    LOGGER.debug('get_transactions params| %s', params)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            url,
            params=params,
            headers={
                'content-type': 'application/json'
            },
            cookies=session._cookies
        )
    check_response(response)
    resp_json = response.json()
    LOGGER.debug("get_transactions response| %s", resp_json)
    return resp_json
