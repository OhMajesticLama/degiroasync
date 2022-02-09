from typing import Any, Union
import functools


from .product import ProductBase
from .. import webapi
from ..core import SessionCore
from ..core import ORDER


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


async def get_orders():
    raise NotImplementedError
