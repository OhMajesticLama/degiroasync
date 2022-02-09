import enum

# Used to get same Logger instance across submodules.
LOGGER_NAME = 'degiroasync'


class _EnumBase(enum.Enum):
    """
    Base class for Enums that should behave as str or other types.

    >>> class EnumStr(str, _EnumBase):
    ...     pass
    ...
    >>> class Foo(EnumStr):
    ...     A = 'foo'
    ...
    >>> str(Foo.A)
    'foo'

    """
    def __repr__(self):
        return f"'{self.__str__()}'"

    def __str__(self):
        return self.value.__str__()


# Will be replaced by enum.StrEnum in Python 3.11
# TODO: move to StrEnum and do a try/except ImportError to switch to stdlib
# implementation when available.
class EnumStr(str, _EnumBase):
    """
    Base class for Enums that should behave as str.

    Refer to example below for difference in behavior with other Enum based
    solutions.

    >>> import enum
    >>> # Basic enum.Enum example
    >>> class Foo(enum.Enum):
    ...     A = 'foo'
    ...
    >>> Foo.A
    <Foo.A: 'foo'>
    >>> str(Foo.A)
    'Foo.A'
    >>> repr(Foo.A)
    "<Foo.A: 'foo'>"
    >>> type(Foo.A)
    <enum 'Foo'>
    >>> # Inheriting from str, enum.Enum
    >>> class Foo(str, enum.Enum):
    ...     A = 'foo'
    ...
    >>> Foo.A
    <Foo.A: 'foo'>
    >>> str(Foo.A)
    'Foo.A'
    >>> repr(Foo.A)
    "<Foo.A: 'foo'>"
    >>> type(Foo.A)
    <enum 'Foo'>

    >>> # An EnumStr child can be used as a drop-in replacement for a str
    >>> class Foo(EnumStr):
    ...     A = 'foo'
    ...
    >>> Foo.A
    'foo'
    >>> str(Foo.A)
    'foo'
    >>> repr(Foo.A)
    "'foo'"
    >>> type(Foo.A)
    <enum 'Foo'>
    """


class EnumInt(int, _EnumBase):
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

    >>> # An EnumStr child can be used as a drop-in replacement for an int
    >>> class Foo(EnumInt):
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


class LOGIN(EnumInt):
    TOTP_NEEDED = 6


class ORDER:
    """
    Constants for orders in web API.
    """
    class ACTION(EnumStr):
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

    class TYPE(EnumInt):
        """
        LIMITED:
            This is the "Limit" field value in the web trader.

        MARKET:
            This is the "Market" field value in the web trader.

        STOP_LOSS:
            This is the "Stop Loss" field value in the web trader.

        STOP_LIMITED:
            This is the "Stop Limited" field value in the web trader.
        """
        LIMITED = 0
        STOP_LIMITED = 1
        MARKET_ORDER = 2
        STOP_LOSS = 3

    class TIME(EnumInt):
        DAY = 1
        PERMANENT = 3


class PRODUCT:
    class TYPEID(EnumInt):
        STOCK = 1
        BONDS = 2
        FUTURES = 7
        OPTIONS = 8
        INVEST_FUNDS = 13
        LEVERAGE_PRODUCTS = 14
        ETFS = 131
        CFDS = 535
        WARRANTS = 536
        CURRENCY = 311

    class TYPE(EnumStr):
        STOCK = 'STOCK'


class SORT(EnumStr):
    ASC = "asc"
    DESC = "desc"


class PRICE:
    class RESOLUTION(EnumStr):
        # Resolution
        PT1M = 'PT1M'  # Higher resolution, 1 minute
        PT1D = 'P1D'   # 1 tic per day

    class PERIOD(EnumStr):
        # Periods
        # P stands for Prior
        P1DAY = 'P1D'
        P1WEEK = 'P1W'
        P1MONTH = 'P1M'
        P3MONTH = 'P3M'
        P6MONTH = 'P6M'
        P1YEAR = 'P1Y'
        P50YEAR = 'P50Y'

    class TYPE(EnumStr):
        PRICE = 'price'
        OHLC = 'ohlc'
