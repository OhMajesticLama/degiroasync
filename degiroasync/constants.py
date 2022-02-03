import enum
LOGGER_NAME = 'degiroasync'


class EnumStr(str, enum.Enum):
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
    def __repr__(self):
        return f"'{super().__str__()}'"

    def __str__(self):
        return super().__str__()


class DegiroStatus:
    TOTP_NEEDED = 6


class Order:
    class Action:
        BUY = 0
        SELL = 1

    class Type:
        LIMITED = 0
        STOP_LIMITED = 1
        MARKET_ORDER = 2
        STOP_LOSS = 3

    class Time:
        DAY = 1
        PERMANENT = 3


class ProductConst:
    class TypeId:
        ALL = None
        SHARES = 1
        BONDS = 2
        FUTURES = 7
        OPTIONS = 8
        INVEST_FUNDS = 13
        LEVERAGE_PRODUCTS = 14
        ETFS = 131
        CFDS = 535
        WARRANTS = 536

    class Type(EnumStr):
        STOCKS = 'STOCKS'


class Sort(EnumStr):
    ASC = "asc"
    DESC = "desc"


class PriceConst:
    class Resolution(EnumStr):
        # Resolution
        PT1M = 'PT1M'  # Higher resolution, is it one minute?
        PT1D = 'P1D'   # 1 tic per day

    class Period(EnumStr):
        # Periods
        # P stands for Prior
        P1DAY = 'P1D'
        P1WEEK = 'P1W'
        P1MONTH = 'P1M'
        P3MONTH = 'P3M'
        P6MONTH = 'P6M'
        P1YEAR = 'P1Y'
        P50YEAR = 'P50Y'

    class Type(EnumStr):
        PRICE = 'price'
        OHLC = 'ohlc'


