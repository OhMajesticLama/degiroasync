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

from typing import Union

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
    # SessionCore config, as returned by Degiro
    clientId: int
    companiesServiceUrl: Union[str, None]
    dictionaryUrl: str
    i18nUrl: Union[str, None]
    landingPath: Union[str, None]
    latestSearchedProductsUrl: Union[str, None]
    loginUrl: str
    mobileLandingPath: Union[str, None]
    paUrl: str
    paymentServiceUrl: Union[str, None]
    productNotesUrl: Union[str, None]
    productSearchUrl: str
    productTypesUrl: str
    refinitivAgendaUrl: Union[str, None]
    refinitivClipsUrl: Union[str, None]
    refinitivCompanyProfileUrl: Union[str, None]
    refinitivCompanyRatiosUrl: Union[str, None]
    refinitivEsgsUrl: Union[str, None]
    refinitivEstimatesUrl: Union[str, None]
    refinitivFinancialStatementsUrl: Union[str, None]
    refinitivInsiderTransactionsUrl: Union[str, None]
    refinitivInsidersReportUrl: Union[str, None]
    refinitivInvestorUrl: Union[str, None]
    refinitivNewsUrl: Union[str, None]
    refinitivShareholdersUrl: Union[str, None]
    refinitivTopNewsCategoriesUrl: Union[str, None]
    reportingUrl: Union[str, None]
    sessionId: Union[str, None]
    taskManagerUrl: Union[str, None]
    tradingUrl: Union[str, None]
    translationsUrl: Union[str, None]
    vwdGossipsUrl: Union[str, None]
    vwdNewsUrl: Union[str, None]
    vwdQuotecastServiceUrl: Union[str, None]


@JSONclass(annotations=True, annotations_type=True)
class PAClient:
    """
    Data Structure for PA Client
    """
    address: Union[dict, None]
    # {
    #    city = Union[str, None]
    #    country = Union[str, None]
    #    streetAddress = Union[str, None]
    #    streetAddressNumber = Union[str, None]
    #    zip: 83300
    # }
    bankAccount: Union[dict, None]
    # {
    #    bankAccountId = Union[str, None]
    #    bic = Union[str, None]
    #    iban = Union[str, None]
    #    status: VERIFIED
    # }
    canUpgrade: Union[str, None]
    clientRole: Union[str, None]
    contractType: Union[str, None]
    culture: Union[str, None]
    displayLanguage: Union[str, None]
    displayName: Union[str, None]
    effectiveClientRole: Union[str, None]
    email: Union[str, None]
    firstContact: Union[dict, None]
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
    flatexBankAccount: Union[dict, None]
    # {
    #    bic = Union[str, None]
    #    iban = Union[str, None]
    # }
    id: Union[str, None]
    intAccount = Union[str, None]
    isAllocationAvailable = Union[str, None]
    isAmClientActive = Union[str, None]

    # def set_data(self, data: dict):
    #    check_keys(data, ('intAccount', 'id'))
    #    setattrs(self, **data)
    #    return self


@dataclasses.dataclass
class SessionCore:
    JSESSIONID = 'JSESSIONID'

    config: Union[Config, None] = None
    client: Union[PAClient, None] = None

    # Cookies
    # Wrap to not leak httpx
    _cookies: Union[httpx.Cookies, None] = None

    @property
    def cookies(self):
        return dict(self._cookies)

    @cookies.setter
    def cookies(self, cookies: dict):
        self._cookies = httpx.Cookies(cookies)


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
        return join_url(session.config.refinitivNewsUrl, 'news-by-company')

    @staticmethod
    def get_client_info_url(session: SessionCore) -> str:
        """
        Build client info url.
        """
        check_session_config(session)
        return join_url(session.config.paUrl, 'client')

    @staticmethod
    def get_portfolio_url(session: SessionCore) -> str:
        """
        Build portfolio url, also used for orders.
        """
        check_session_config(session)
        check_session_client(session)

        jsessionid = session._cookies[session.JSESSIONID]

        url = join_url(
            session.config.tradingUrl,
            f'v5/update/{session.client.intAccount}',
            f';jsessionid={jsessionid}')
        LOGGER.debug('get_portfolio_url| %s', url)
        return url

    @staticmethod
    def get_reporting_url(session: SessionCore) -> str:
        """
        Get reporting URL. Used for orders history and transactions.
        """
        check_session_config(session)
        url = session.config.reportingUrl
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

        >>>> confirmation_id = '98741234kjaskdjfz098234'
        >>>> confirm_order_url_base = URLs.get_confirm_order_url(session)
        >>>> join_url(confirm_order_url_base, confirmation_id)

        """
        check_session_config(session)

        return join_url(
            session.config.tradingUrl,
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
            session.config.tradingUrl,
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
            session.config.productSearchUrl,
            'v5',
            specialization)
        LOGGER.debug('get_product_search_url: %s', url)
        return url

    @staticmethod
    def get_product_dictionary_url(session: SessionCore) -> str:
        check_session_config(session)
        url = session.config.dictionaryUrl
        LOGGER.debug('get_product_search_url: %s', url)
        return url

    @classmethod
    def get_account_info_url(cls, session: SessionCore) -> str:
        check_session_client(session)
        url = join_url(URLs.ACCOUNT_INFO, str(session.client.intAccount))
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
