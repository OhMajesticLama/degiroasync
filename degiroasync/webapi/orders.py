import httpx

from .webapi import get_trading_update
from ..core import SessionCore


async def set_order(session: SessionCore):
    raise NotImplementedError

async def check_order(session: SessionCore):
    raise NotImplementedError

async def get_orders(session: SessionCore) -> httpx.Response:
    """
    Get current and historical orders
    """
    return await get_trading_update(
            session,
            params={'orders': 0, 'historicalOrders': 0, 'transactions': 0})
