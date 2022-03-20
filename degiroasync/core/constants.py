import enum

try:
    from enum import StrEnum
except ImportError:
    # Exists only starting Python 3.11
    # Reimplement what we need from it here.
    class StrEnum(str, enum.Enum):
        def __str__(self):
            return str.__str__(self)


# Used to get same Logger instance across submodules.
LOGGER_NAME = 'degiroasync'


class ResponseError(Exception):
    "Raised when bad response has been received from server."


class _EnumBase(enum.Enum):
    """
    Base class for Enums that should behave as str or other types.

    >>> class StrEnum(str, _EnumBase):
    ...     pass
    ...
    >>> class Foo(StrEnum):
    ...     A = 'foo'
    ...
    >>> str(Foo.A)
    'foo'

    """

    def __repr__(self):
        return f"'{self.__str__()}'"

    def __str__(self):
        return self.value.__str__()


class IntEnum(int, _EnumBase):
    """
    Base class for Enums that should behave as str.

    Refer to example below for difference in behavior with other Enum based
    solutions.

    >>> import enum
    >>> # Basic enum.Enum example
    >>> class Foo(enum.Enum):
    ...     A = 1
    ...
    >>> Foo.A
    <Foo.A: 1>
    >>> str(Foo.A)
    'Foo.A'
    >>> repr(Foo.A)
    "<Foo.A: 1>"
    >>> type(Foo.A)
    <enum 'Foo'>
    >>> # Inheriting from str, enum.Enum
    >>> class Foo(int, enum.Enum):
    ...     A = 1
    ...
    >>> Foo.A
    <Foo.A: 1>
    >>> str(Foo.A)
    'Foo.A'
    >>> repr(Foo.A)
    "<Foo.A: 1>"
    >>> type(Foo.A)
    <enum 'Foo'>

    >>> # An StrEnum child can be used as a drop-in replacement for an int
    >>> class Foo(IntEnum):
    ...     A = 1
    ...
    >>> Foo.A
    1
    >>> str(Foo.A)
    '1'
    >>> repr(Foo.A)
    "'1'"
    >>> type(Foo.A)
    <enum 'Foo'>
    """


class LOGIN(IntEnum):
    TOTP_NEEDED = 6


class ORDER:
    """
    Constants for orders in web API.
    """
    class ACTION(StrEnum):
        """
        BUY:
            Use when placing a _BUY_ order on a product.

        SELL:
            Use when placing a _SELL_ order on a product.

        Check `ORDER.TYPE` for types of orders.

        For use with `checkOrder` HTTP endpoint - or `check_order` degiroasync
        API calls.
        """
        BUY = 'BUY'
        SELL = 'SELL'

    class TYPE(IntEnum):
        """
        LIMITED:
            This is the "Limit" field value of "Order type" in the web trader.

        MARKET:
            This is the "Market" field value of "Order type" in the web trader.

        STOP_LOSS:
            This is the "Stop Loss" field value of "Order type" in the web
            trader.

        STOP_LIMITED:
            This is the "Stop Limited" field value of "Order type" in the web
            trader.

        AMOUNT:
            This is the "Amount" field value of "Order type" in the web trader.
            It's used for investment funds.
        """
        LIMITED = 0
        STOP_LIMITED = 1
        MARKET_ORDER = 2
        STOP_LOSS = 3
        AMOUNT = 4

    class TIME(IntEnum):
        DAY = 1
        PERMANENT = 3

    class STATUS(StrEnum):
        CONFIRMED = 'CONFIRMED'
        REJECTED = 'REJECTED'


class TRANSACTION:
    class TYPEID(IntEnum):
        pass

    class COUNTERPARTY(StrEnum):
        MARKET = 'MK'
        DEGIRO = 'DG'
        GROUP = 'GR'


class PRODUCT:
    class TYPEID(IntEnum):
        STOCK = 1
        BONDS = 2
        FUTURES = 7
        OPTIONS = 8
        FUNDS = 13
        LEVERAGE_PRODUCTS = 14
        ETFS = 131
        CFDS = 535
        WARRANTS = 536
        CURRENCY = 311

    class TYPE(StrEnum):
        STOCK = 'STOCK'
        FUND = 'FUND'
        CASH = 'CASH'
        CURRENCY = 'CURRENCY'


class SORT(StrEnum):
    ASC = "asc"
    DESC = "desc"


class PRICE:
    class RESOLUTION(StrEnum):
        # Resolution
        PT1M = 'PT1M'  # Higher resolution, 1 minute
        PT1D = 'P1D'   # 1 tic per day

    class PERIOD(StrEnum):
        # Periods
        # P stands for Prior
        P1DAY = 'P1D'
        P1WEEK = 'P1W'
        P1MONTH = 'P1M'
        P3MONTH = 'P3M'
        P6MONTH = 'P6M'
        P1YEAR = 'P1Y'
        P50YEAR = 'P50Y'

    class TYPE(StrEnum):
        PRICE = 'price'
        OHLC = 'ohlc'


class POSITION:
    class TYPE(StrEnum):
        PRODUCT = 'PRODUCT'

# HTTP Requests global timeout, in seconds
TIMEOUT: float = 20
