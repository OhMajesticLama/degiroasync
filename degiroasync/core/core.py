from __future__ import annotations
import logging
import dataclasses
try:
    # Ignore type here: will fail w/ Python version <3.11
    from enum import StrEnum  # type: ignore
except ImportError:
    import enum
    # Exists only starting Python 3.11
    # Reimplement what we need from it here.

    # Type warning 'already defined', this statement is executed if prior
    # import failed: no risk of redefinition.
    class StrEnum(str, enum.Enum):  # type: ignore
        def __str__(self):
            return str.__str__(self)

from typing import Union, Optional, Any

import httpx
from jsonloader import JSONclass

from .helpers import join_url
from .constants import LOGGER_NAME
from .constants import PRODUCT
from .constants import TIMEOUT
from ..core.helpers import ThrottlingClient
from .exceptions import ContextError

LOGGER = logging.getLogger(LOGGER_NAME)
LOGGER.setLevel(logging.DEBUG)


@dataclasses.dataclass
class Credentials:
    """
    Holds credentials for Web API.

    If 2FA is enabled on the account, either totp_secret or one_time_password
    must be provided for the login to be successful.

    `totp_secret` can be obtained in a 2FA editor/app (e.g. andOTP) in the
    'Secret' field.

    If use of `one_time_password` is chosen instead, be mindful that login
    must be called promptly as one_time_password expires frequently.
    """
    username: str
    password: str

    totp_secret: Union[str, None] = None
    one_time_password: Union[str, None] = None

    def __hash__(self) -> int:
        return hash(
            '|'.join(
                ':'.join((str(k), str(v)))
                for k, v in self.__dict__.items())
                )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Credentials):
            raise AttributeError(
                    "other is not `Credentials` instance.")
        return hash(self) == hash(other)


@JSONclass(annotations=True, annotations_type=True)
class Config:
    """
    SessionCore config, as returned by endpoint.
    """
    client_id: int
    companies_service_url: Union[str, None]
    dictionary_url: str
    i18n_url: Optional[str]
    landing_path: Optional[str]
    latest_searched_products_url: Optional[str]
    login_url: str
    mobile_landing_path: Optional[str]
    pa_url: str
    payment_service_url: Optional[str]
    product_notes_url: Optional[str]
    product_search_url: str
    product_types_url: str
    refinitiv_agenda_url: Optional[str]
    refinitiv_clips_url: Optional[str]
    refinitiv_company_profile_url: Optional[str]
    refinitiv_company_ratios_url: Optional[str]
    refinitiv_esgs_url: Optional[str]
    refinitiv_estimates_url: Optional[str]
    refinitiv_financial_statements_url: Optional[str]
    refinitiv_insider_transactions_url: Optional[str]
    refinitiv_insiders_report_url: Optional[str]
    refinitiv_investor_url: Optional[str]
    refinitiv_news_url: Optional[str]
    refinitiv_shareholders_url: Optional[str]
    refinitiv_top_news_categories_url: Optional[str]
    reporting_url: Optional[str]
    session_id: Optional[str]
    task_manager_url: Optional[str]
    trading_url: Optional[str]
    translations_url: Optional[str]
    vwd_gossips_url: Optional[str]
    vwd_news_url: Optional[str]
    vwd_quotecast_service_url: Optional[str]


@JSONclass(annotations=True, annotations_type=True)
class PAClient:
    """
    Data Structure for PA Client
    """
    address: Union[dict, None]
    # {
    #    city = Union[str, None]
    #    country = Union[str, None]
    #    street_address = Union[str, None]
    #    street_address_number = Union[str, None]
    #    zip: 83300
    # }
    bank_account: Union[dict, None]
    # {
    #    bank_account_id = Union[str, None]
    #    bic = Union[str, None]
    #    iban = Union[str, None]
    #    status: VERIFIED
    # }
    can_upgrade: Union[bool, None]
    client_role: Union[str, None]
    contract_type: Union[str, None]
    culture: Union[str, None]
    display_language: Union[str, None]
    display_name: Union[str, None]
    effective_client_role: Union[str, None]
    email: Union[str, None]
    first_contact: Union[dict, None]
    # {
    #    countryOfBirth: Union[str, None]
    #    dateOfBirth: Union[str, None]
    #    displayName: Union[str, None]
    #    firstName: Union[str, None]
    #    gender: Union[str, None]
    #    lastName: Union[str, None]
    #    nationality: Union[str, None]
    #    placeOfBirth: Union[str, None]
    # }
    flatex_bank_account: Union[dict, None]
    # {
    #    bic = Union[str, None]
    #    iban = Union[str, None]
    # }
    id: Union[str, None]
    int_account: Union[int, None]
    is_allocation_available: Union[bool, None]
    is_am_client_active: Union[bool, None]


@dataclasses.dataclass
class SessionCore:
    JSESSIONID = 'JSESSIONID'

    config: Optional[Config] = None
    client: Optional[PAClient] = None

    _max_requests_default: int = 40
    _period_seconds_default: int = 1

    # Cookies
    _cookies: Optional[httpx.Cookies] = None
    _http_client: Optional[ThrottlingClient] = None

    @property
    def cookies(self):
        return dict(self._cookies)

    def update_throttling(
            self,
            max_requests: int = 20,
            period_seconds: float = 1
            ):
        """
        Update throttling parameters. No limit if max_requests <= 0.

        Note: going over 40 requests per second seems to trigger API bans.

        Parameters
        ----------

        max_requests
            Maximum number of requests per `period_seconds` before throttling.
            If <= 0, no limit.

        period_seconds
            Period on which to count requests.
        """
        if self._http_client is None:
            self._max_requests_default = max_requests
            self._period_seconds_default = period_seconds
        else:
            self._http_client._max_requests = max_requests
            self._http_client._period_s = period_seconds

    @cookies.setter
    def cookies(self, cookies: dict):
        self._cookies = httpx.Cookies(cookies)

    def __hash__(self):
        return hash(self.__dict__.values())

    async def __aenter__(self) -> ThrottlingClient:
        if self._http_client is None:
            self._http_client = ThrottlingClient(
                    max_requests=self._max_requests_default,
                    period_seconds=self._period_seconds_default,
                    timeout=TIMEOUT
                    )
        return await self._http_client.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._http_client.__aexit__(exc_type, exc_val, exc_tb)


class URLs:
    BASE = 'https://trader.degiro.nl'
    LOGIN = join_url(BASE, '/login/secure/login')
    LOGIN_TOTP = join_url(BASE, '/login/secure/login/totp')
    CONFIG = join_url(BASE, '/login/secure/config')
    ACCOUNT_INFO = join_url(BASE, '/trading/secure/v5/account/info')

    @staticmethod
    def get_news_by_company_url(session: SessionCore) -> str:
        "Build news_by_company url"
        config = check_session_config(session)
        if config.refinitiv_news_url is None:
            raise ContextError(
                    "Session attribute 'refinitiv_news_url' is not set."
                    )
        return join_url(config.refinitiv_news_url, 'news-by-company')

    @staticmethod
    def get_client_info_url(session: SessionCore) -> str:
        """
        Build client info url.
        """
        config = check_session_config(session)
        if config.pa_url is None:
            raise ContextError(
                    "Session attribute 'pa_url' is not set."
                    )
        return join_url(config.pa_url, 'client')

    @staticmethod
    def get_portfolio_url(session: SessionCore) -> str:
        """
        Build portfolio url, also used for orders.
        """
        config = check_session_config(session)
        client = check_session_client(session)

        if session._cookies is None:
            raise ContextError("_cookies not set in session.")

        jsessionid = session._cookies[session.JSESSIONID]

        if config.trading_url is None:
            raise ContextError(
                    "Session attribute 'trading_url' is not set."
                    )
        url = join_url(
            config.trading_url,
            f'v5/update/{client.int_account}',
            f';jsessionid={jsessionid}')
        LOGGER.debug('get_portfolio_url| %s', url)
        return url

    @staticmethod
    def get_reporting_url(session: SessionCore) -> str:
        """
        Get reporting URL. Used for orders history and transactions.
        """
        config = check_session_config(session)
        url = config.reporting_url
        if url is None:
            raise ContextError(
                    "Session attribute 'reporting_url' is not set."
                    )
        LOGGER.debug('get_reporting_url| %s', url)
        return url

    @classmethod
    def get_orders_history_url(cls, session: SessionCore) -> str:
        """
        Get reporting URL. Used for orders history.
        """
        url = join_url(cls.get_reporting_url(session), 'v4/order-history')
        LOGGER.debug('get_orders_history_url| %s', url)
        return url

    @classmethod
    def get_transactions_url(cls, session: SessionCore) -> str:
        """
        Get reporting URL. Used for orders history.
        """
        url = join_url(cls.get_reporting_url(session), 'v4/transactions')
        LOGGER.debug('get_transactions_url| %s', url)
        return url

    @staticmethod
    def get_confirm_order_url(session: SessionCore) -> str:
        """
        Build url for confirm_order.

        This url will need to be completed by caller with `confirmation_id`
        For example:

        .. code-block:: python

            confirmation_id = '98741234kjaskdjfz098234'
            confirm_order_url_base = URLs.get_confirm_order_url(session)
            join_url(confirm_order_url_base, confirmation_id)

        """
        config = check_session_config(session)

        return join_url(
            config.trading_url,
            'v5/order'
        )

    @classmethod
    def get_orders_url(cls, session: SessionCore) -> str:
        """
        Build Get Orders url
        """
        # This is is the same endpoint and url as portfolio
        return cls.get_portfolio_url(session)

    @classmethod
    def get_check_order_url(cls, session: SessionCore) -> str:
        """
        Get check order URL.
        """
        config = check_session_config(session)

        jsessionid = check_session_cookies(session)[session.JSESSIONID]

        url = join_url(
            config.trading_url,
            f'v5/checkOrder;jsessionid={jsessionid}'
        )
        LOGGER.debug('get_check_order_url| %s', url)
        return url

    @staticmethod
    def get_price_data_url(session: SessionCore) -> str:
        check_session_config(session)
        # Check if this should be pulled from session config
        return 'https://charting.vwdservices.com/hchart/v1/deGiro/data.js'

    class PRODUCT_SEARCH_TYPE(StrEnum):
        GENERIC = 'products/lookup'
        STOCKS = 'stocks'
        ETFS = 'etfs'
        BONDS = 'bonds'
        OPTIONS = 'options'
        FUTURES = 'futures'
        FUNDS = 'funds'
        LEVERAGED_PRODUCTS = 'leverageds'
        WARRANTS = 'warrants'

    @staticmethod
    def get_product_search_url(
            session: SessionCore,
            product_type_id: Optional[PRODUCT.TYPEID] = None) -> str:
        specialization: Union[str, URLs.PRODUCT_SEARCH_TYPE] = {
            PRODUCT.TYPEID.STOCK:
                URLs.PRODUCT_SEARCH_TYPE.STOCKS,
            PRODUCT.TYPEID.ETFS:
                URLs.PRODUCT_SEARCH_TYPE.ETFS,
            PRODUCT.TYPEID.OPTIONS:
                URLs.PRODUCT_SEARCH_TYPE.OPTIONS,
            PRODUCT.TYPEID.BONDS:
                URLs.PRODUCT_SEARCH_TYPE.BONDS,
            PRODUCT.TYPEID.FUNDS:
                URLs.PRODUCT_SEARCH_TYPE.FUNDS,
            PRODUCT.TYPEID.LEVERAGE_PRODUCTS:
                URLs.PRODUCT_SEARCH_TYPE.LEVERAGED_PRODUCTS,
            PRODUCT.TYPEID.WARRANTS:
                URLs.PRODUCT_SEARCH_TYPE.WARRANTS,
            # mypy doesn't handle well the error management in dict.get:
            # here we rely on dict.get to provide default value if
            # product_type_id is not found or None.
        }.get(
            product_type_id,  # type: ignore
            URLs.PRODUCT_SEARCH_TYPE.GENERIC
        )
        config = check_session_config(session)
        url = join_url(
            config.product_search_url,
            'v5',
            specialization)
        LOGGER.debug('get_product_search_url: %s', url)
        return url

    @staticmethod
    def get_product_dictionary_url(session: SessionCore) -> str:
        config = check_session_config(session)
        url = config.dictionary_url
        LOGGER.debug('get_product_search_url: %s', url)
        return url

    @classmethod
    def get_account_info_url(cls, session: SessionCore) -> str:
        client = check_session_client(session)
        url = join_url(URLs.ACCOUNT_INFO, str(client.int_account))
        return cls._add_jsessionid(session, url)

    @classmethod
    def _add_jsessionid(cls, session: SessionCore, url: str) -> str:
        check_session_config(session)
        cookies = check_session_cookies(session)
        return url + ';jsessionid={}'.format(
            cookies[session.JSESSIONID])


def check_session_config(session: SessionCore) -> Config:
    "Raise an exception if session.config is not set"
    if session.config is None:
        raise AssertionError(
            "session.config is not set. Call get_config first.")
    return session.config


def check_session_client(session: SessionCore) -> PAClient:
    "Raise an exception if session.client is not set"
    if session.client is None:
        raise AssertionError(
            "session.client is not set. Call get_client_info first.")
    return session.client


def check_session_cookies(session: SessionCore) -> httpx.Cookies:
    "Helper to get cookies from a session."
    if session._cookies is not None:
        return session._cookies
    else:
        raise ContextError("Cookies not set in session. Abort.")
