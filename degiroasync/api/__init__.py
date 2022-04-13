"""
High-level API for DEGIRO platform.
===================================

This module provides an interface that is higher level than the `webapi` module
(or the direct HTTP API).
It provides various data structures with guaranteed fields, and functions
to build or act on those data structures.

Users should only import directly from `degiroasync.api`, its submodules
should be considered implementation details.

Data Structures
+++++++++++++++

Details on data structures are available for each data structure.

Core structures to be aware off when dealing with `degiroasync` are:

    - *Session*
      It is necessary with almost every call in this module. Session contains
      session identifier, as well as basic mapping information between
      identifiers and objects.
    - *Product*
      A product per DEGIRO API. This can be a Shares, ETF or any other product
      available on the platform.
    - *Order*
      An order per DEGIRO API. As in the web trader, an order can be active
      or not, and different order types exist (BUY, SELL, LIMITED ...).
    - *Transaction*
      A transaction per DEGIRO API. This reflects cash impacts on the account.
      There can be zero to many transactions per Order. As of 2022.03, DEGIRO
      API does not seem to provide relationship between transactions and
      orders.

Other data structures are available, but more situational. They can be found
in the module members documentation.

Functions
+++++++++

Several functions reflecting the API calls are implemented in this module,
An overview of some of the essential ones is listed below.
Details can be found with each function documentation:

    - *login*
      Builds a `Session` instance, this supports login with or without 2FA.
    - *get_portfolio* and *get_portfolio_total*
      Provide data on products currently held on the account.
    - *search_product*
      Find and instantiate DEGIRO products from various search options (text,
      ISIN, symbol, exchange ...).
    - *get_price_data*
      Get price data on a Product.
    - *get_orders* and *check_order*
      Get orders on the account, start placing an order. Note: `webapi` module
      must currently be used to confirm an order.

"""
from .orders import check_order
from .orders import get_orders
from .orders import get_transactions
from .orders import Order
from .orders import Transaction
from .session import Session
from .session import login
from .session import get_exchange_dictionary
from .session import ExchangeDictionary
from .session import Exchange, Region, Country
from .product import get_portfolio
from .product import get_portfolio_total
from .product import get_price_data
from .product import search_product
from .product import Stock
from .product import Currency
from .product import ProductBase
from .product import ProductFactory  # Don't expose in __all__
from .product import ProductGeneric
from .product import PriceSeriesTime
from .product import TotalPortfolio
from ..core import Credentials
from ..core.constants import PRODUCT
from ..core.constants import PRICE
from ..core.constants import ORDER
from ..core.constants import POSITION


__all__ = [
        # Choice between strings or import errors at this level.
        # An object missing __name__ will fail at module import, typos
        # in object names are flagged by editor's tools and easier to catch
        # than typos in a string.
        obj.__name__ for obj in (  # type: ignore
            # Session
            login,
            Credentials,
            Session,
            get_exchange_dictionary,
            ExchangeDictionary,
            Exchange, Region, Country,

            # Product
            search_product,
            get_portfolio,
            get_price_data,

            # PriceData,
            PriceSeriesTime,
            Stock,
            Currency,
            ProductBase,
            ProductGeneric,

            get_portfolio,
            get_portfolio_total,
            TotalPortfolio,

            # Order
            check_order,
            get_orders,
            get_transactions,
            Order,
            Transaction,

            # Constants
            #PRODUCT,
            #ORDER,
            #PRICE,
            #POSITION
)]
