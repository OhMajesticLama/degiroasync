import logging
from typing import Union

import httpx

from .webapi import get_trading_update
from ..core import SessionCore
from ..core import URLs
from ..core import constants
from ..core import ORDER
from ..core import join_url
from ..core import check_session_client
from ..core import check_session_config
from .webapi import check_response


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
        intAccount=session.client.intAccount,
        sessionId=jsession_id
            )
    data = dict(
        buySell=buy_sell,
        orderType=order_type,
        price=price,
        productId=product_id,
        timeType=time_type
            )

    async with httpx.AsyncClient() as client:
        response = await client.post(
                url,
                params=params,
                json=data,
                )
    check_response(response)
    resp_json = response.json()
    LOGGER.debug("check_order| %s", resp_json)
    return response


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
        ) -> httpx.Response:
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

    ```
    """
    _order_calls_check(session,
                       product_id=product_id,
                       buy_sell=buy_sell,
                       time_type=time_type,
                       order_type=order_type,
                       size=size,
                       price=price)
    # This call will not have integration tests to prevent misplaced orders
    # All changes must be manually verified to work as intended.

    jsessionid = session._cookies[session.JSESSIONID]

    url = URLs.get_check_order_url(session)
    params = dict(
        intAccount=session,
        sessionId=jsessionid
            )
    data = dict(
        buySell=buy_sell,
        orderType=order_type,
        price=price,
        productId=product_id,
        size=size,
        time_type=time_type
            )
    async with httpx.AsyncClient() as client:
        response = await client.post(
                url,
                params=params,
                json=data,
                )
    check_response(response)
    resp_json = response.json()
    LOGGER.debug("check_order| %s", resp_json)
    return response


async def get_orders(session: SessionCore) -> httpx.Response:
    """
    Get current and historical orders
    """
    return await get_trading_update(
            session,
            params={'orders': 0, 'historicalOrders': 0, 'transactions': 0}
            )
