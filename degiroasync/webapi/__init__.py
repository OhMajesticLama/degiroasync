"""
Async API for Degiro. This module is close to Degiro Web API structure:
responses are provided (almost) as-is with minimum abstraction
and verification.

For a higher level api, see `api` module.

Users should only import directly from `degiroasync.webapi`, its submodules
should be considered implementation details.
"""
from .webapi import *
from degiroasync.webapi import webapi

from .login import login
from .login import get_config
from .login import get_client_info
from .login import get_product_dictionary
from .webapi import get_products_info
from .webapi import search_product
from .orders import get_orders
from .orders import confirm_order
from .orders import check_order


__all__ = [
        # Login names
        login.__name__,
        get_config.__name__,
        get_client_info.__name__,
        get_product_dictionary.__name__,
        # webapi names
        get_products_info.__name__,
        search_product.__name__,
        # Orders names
        get_orders.__name__,
        confirm_order.__name__,
        check_order.__name__,
        ] + webapi.__all__
