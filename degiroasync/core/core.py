from __future__ import annotations
import logging
import dataclasses
try:
    from enum import StrEnum
except ImportError:
    import enum
    # Exists only starting Python 3.11
    # Reimplement what we need from it here.

    class StrEnum(str, enum.Enum):
        def __str__(self):
            return str.__str__(self)

from typing import Union, Optional

import httpx
from jsonloader import JSONclass

from .helpers import join_url
from .constants import LOGGER_NAME
from .constants import PRODUCT

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


@JSONclass(annotations=True, annotations_type=True)
class Config:
    """
    SessionCore config, as returned by endpoint.
    """
    client_id: int
    companies_service_url: Union[str, None]
    dictionary_url: str
    i18n_url: Union[str, None]
    landing_path: Union[str, None]
    latest_searched_products_url: Union[str, None]
    login_url: str
    mobile_landing_path: Union[str, None]
    pa_url: str
    payment_service_url: Union[str, None]
    product_notes_url: Union[str, None]
    product_search_url: str
    product_types_url: str
    refinitiv_agenda_url: Union[str, None]
    refinitiv_clips_url: Union[str, None]
    refinitiv_company_profile_url: Union[str, None]
    refinitiv_company_ratios_url: Union[str, None]
    refinitiv_esgs_url: Union[str, None]
    refinitiv_estimates_url: Union[str, None]
    refinitiv_financial_statements_url: Union[str, None]
    refinitiv_insider_transactions_url: Union[str, None]
    refinitiv_insiders_report_url: Union[str, None]
    refinitiv_investor_url: Union[str, None]
    refinitiv_news_url: Union[str, None]
    refinitiv_shareholders_url: Union[str, None]
    refinitiv_top_news_categories_url: Union[str, None]
    reporting_url: Union[str, None]
    session_id: Union[str, None]
    task_manager_url: Union[str, None]
    trading_url: Union[str, None]
    translations_url: Union[str, None]
    vwd_gossips_url: Union[str, None]
    vwd_news_url: Union[str, None]
    vwd_quotecast_service_url: Union[str, None]


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

    # def set_data(self, data: dict):
    #    check_keys(data, ('intAccount', 'id'))
    #    setattrs(self, **data)
    #    return self


@dataclasses.dataclass
class SessionCore:
    JSESSIONID = 'JSESSIONID'

    config: Optional[Config] = None
    client: Optional[PAClient] = None

    # Cookies
    # Wrap to not leak httpx
    _cookies: Union[httpx.Cookies, None] = None

    @property
    def cookies(self):
        return dict(self._cookies)

    @cookies.setter
    def cookies(self, cookies: dict):
        self._cookies = httpx.Cookies(cookies)

    def __hash__(self):
        return hash(self.__dict__.values())


class URLs:
    BASE = 'https://trader.degiro.nl'
    LOGIN = join_url(BASE, '/login/secure/login')
    LOGIN_TOTP = join_url(BASE, '/login/secure/login/totp')
    CONFIG = join_url(BASE, '/login/secure/config')
    ACCOUNT_INFO = join_url(BASE, '/trading/secure/v5/account/info')

    @staticmethod
    def get_news_by_company_url(session: SessionCore) -> str:
        "Build news_by_company url"
        check_session_config(session)
        return join_url(session.config.refinitiv_news_url, 'news-by-company')

    @staticmethod
    def get_client_info_url(session: SessionCore) -> str:
        """
        Build client info url.
        """
        check_session_config(session)
        return join_url(session.config.pa_url, 'client')

    @staticmethod
    def get_portfolio_url(session: SessionCore) -> str:
        """
        Build portfolio url, also used for orders.
        """
        check_session_config(session)
        check_session_client(session)

        jsessionid = session._cookies[session.JSESSIONID]

        url = join_url(
            session.config.trading_url,
            f'v5/update/{session.client.int_account}',
            f';jsessionid={jsessionid}')
        LOGGER.debug('get_portfolio_url| %s', url)
        return url

    @staticmethod
    def get_reporting_url(session: SessionCore) -> str:
        """
        Get reporting URL. Used for orders history and transactions.
        """
        check_session_config(session)
        url = session.config.reporting_url
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
        check_session_config(session)

        return join_url(
            session.config.trading_url,
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
        check_session_config(session)

        jsessionid = session._cookies[session.JSESSIONID]

        url = join_url(
            session.config.trading_url,
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
            product_type_id: Union[PRODUCT.TYPEID, None] = None) -> str:
        specialization = {
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
        }.get(product_type_id, URLs.PRODUCT_SEARCH_TYPE.GENERIC)
        check_session_config(session)
        url = join_url(
            session.config.product_search_url,
            'v5',
            specialization)
        LOGGER.debug('get_product_search_url: %s', url)
        return url

    @staticmethod
    def get_product_dictionary_url(session: SessionCore) -> str:
        check_session_config(session)
        url = session.config.dictionary_url
        LOGGER.debug('get_product_search_url: %s', url)
        return url

    @classmethod
    def get_account_info_url(cls, session: SessionCore) -> str:
        check_session_client(session)
        url = join_url(URLs.ACCOUNT_INFO, str(session.client.int_account))
        return cls._add_jsessionid(session, url)

    @classmethod
    def _add_jsessionid(cls, session: SessionCore, url: str) -> str:
        check_session_config(session)
        return url + ';jsessionid={}'.format(
            session._cookies[session.JSESSIONID])


def check_session_config(session: SessionCore):
    "Raise an exception if session.config is not set"
    if session.config is None:
        raise AssertionError(
            "session.config is not set. Call get_config first.")


def check_session_client(session: SessionCore):
    "Raise an exception if session.client is not set"
    if session.config is None:
        raise AssertionError(
            "session.client is not set. Call get_client_info first.")
