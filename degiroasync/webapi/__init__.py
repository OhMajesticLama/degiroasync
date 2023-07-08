"""
A Python API close to Webtrader HTTP API
========================================

Async API for Degiro. This module is close to Degiro Web API structure:
responses are provided (almost) as-is with minimum abstraction
and verification.

For a higher level api, see `api` module.

Users should only import directly from `degiroasync.webapi`, its submodules
should be considered implementation details.
"""


from .login import login
from .login import get_config
from .login import get_client_info
from .login import get_product_dictionary
# Currently implemented but uncertain usefulness.
from .login import get_account_info
from .product import get_products_info
from .product import search_product
from .product import get_portfolio
from .product import get_portfolio_total
from .product import get_company_profile
from .product import get_news_by_company
from .product import get_price_data
from .product import get_price_series
from .orders import get_orders
from .orders import get_orders_history
from .orders import get_transactions
from .orders import confirm_order
from .orders import check_order
from .orders import ORDER_DATE_FORMAT


__all__ = [
        obj.__name__
        for obj in (
                # login & account
                login,
                get_config,
                get_client_info,
                get_product_dictionary,
                get_account_info,
                # product
                get_portfolio,
                get_portfolio_total,
                get_products_info,
                search_product,
                get_company_profile,
                get_news_by_company,
                get_price_data,
                get_price_series,
                # orders
                get_orders,
                get_orders_history,
                get_transactions,
                confirm_order,
                check_order,
        )
    ] + [
    'ORDER_DATE_FORMAT'
]
