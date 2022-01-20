import os
import logging
import sys
import dataclasses
from urllib.parse import urljoin
import asyncio

from typing import Union, Any, Iterable

import httpx

LOGGER_NAME = 'degiroasync'
LOGGER = logging.getLogger(LOGGER_NAME)

@dataclasses.dataclass
class Credentials:
    username : str
    password : str
    totp_secret : Union[str, None] = None




@dataclasses.dataclass
class Config:
    # Session config, as returned by Degiro
    clientId = Union[str, None]
    companiesServiceUrl = Union[str, None]
    dictionaryUrl = Union[str, None]
    i18nUrl = Union[str, None]
    landingPath = Union[str, None]
    latestSearchedProductsUrl = Union[str, None]
    loginUrl = Union[str, None]
    mobileLandingPath = Union[str, None]
    paUrl = Union[str, None]
    paymentServiceUrl = Union[str, None]
    productNotesUrl = Union[str, None]
    productSearchUrl = Union[str, None]
    productTypesUrl = Union[str, None]
    refinitivAgendaUrl = Union[str, None]
    refinitivClipsUrl = Union[str, None]
    refinitivCompanyProfileUrl = Union[str, None]
    refinitivCompanyRatiosUrl = Union[str, None]
    refinitivEsgsUrl = Union[str, None]
    refinitivEstimatesUrl = Union[str, None]
    refinitivFinancialStatementsUrl = Union[str, None]
    refinitivInsiderTransactionsUrl = Union[str, None]
    refinitivInsidersReportUrl = Union[str, None]
    refinitivInvestorUrl = Union[str, None]
    refinitivNewsUrl = Union[str, None]
    refinitivShareholdersUrl = Union[str, None]
    refinitivTopNewsCategoriesUrl = Union[str, None]
    reportingUrl = Union[str, None]
    sessionId = Union[str, None]
    taskManagerUrl = Union[str, None]
    tradingUrl = Union[str, None]
    translationsUrl = Union[str, None]
    vwdGossipsUrl = Union[str, None]
    vwdNewsUrl = Union[str, None]
    vwdQuotecastServiceUrl = Union[str, None]

    def set_data(self, config : dict):
        """
        Register config dictionnary.
        """
        _check_keys(config,
                ('tradingUrl',
                 'sessionId',
                 'paUrl',
                 'productSearchUrl'))
        # Store for debug purpose
        _set_data(self, config)
        self._config = config
        return self


def _check_keys(data : dict, keys : Iterable[str]):
    """
    Helper to check keys are in data.
    """
    for attr in keys:
        if attr not in data:
            raise AssertionError(f'{attr} not found in config.'
                    ' Please try again later and open a bug ticket if the problem persits.')


def _set_data(obj : object, data : dict):
    """
    Helper to assign data as obj attributes.
    """
    for key, value in data.items():
        if not hasattr(obj, key):
            # Skip unknown config
            LOGGER.debug(
                '%s found in API response but not defined as attribute in data', key)
            continue
        setattr(obj, key, value)


def join_url(*sections):
    """
    Helper to build urls, with slightly different behavior from
    urllib.parse.urljoin, see example below.

    >>> join_url('https://foo.bar', '/rest/of/url')
    'https://foo.bar/rest/of/url'
    >>> join_url('https://foo.bar/product', '/rest/of/url')
    'https://foo.bar/product/rest/of/url'
    >>> join_url('https://foo.bar/product/', '/rest/of/url')
    'https://foo.bar/product/rest/of/url'
    >>> # We need this helper because of below
    ... # urllib.parse.urljoin behavior that is not suitable
    ... # for our purpose.
    >>> import urllib.parse
    >>> urllib.parse.urljoin('https://foo.bar/product', '/rest//of/url')
    'https://foo.bar/rest/of/url'

    """
    return '/'.join(s.strip('/') for s in sections)


class PAClient:
    """
    Client with 
    """

    address = Union[dict, None]
    #{
    #    city = Union[str, None]
    #    country = Union[str, None]
    #    streetAddress = Union[str, None]
    #    streetAddressNumber = Union[str, None]
    #    zip: 83300
    #}
    bankAccount = Union[dict, None]
    #{
    #    bankAccountId = Union[str, None]
    #    bic = Union[str, None]
    #    iban = Union[str, None]
    #    status: VERIFIED
    #}
    canUpgrade = Union[str, None]
    clientRole = Union[str, None]
    contractType = Union[str, None]
    culture = Union[str, None]
    displayLanguage = Union[str, None]
    displayName = Union[str, None]
    effectiveClientRole = Union[str, None]
    email = Union[str, None]
    firstContact = Union[dict, None]
    #{
    #    countryOfBirth = Union[str, None]
    #    dateOfBirth = Union[str, None]
    #    displayName = Union[str, None]
    #    firstName = Union[str, None]
    #    gender = Union[str, None]
    #    lastName = Union[str, None]
    #    nationality = Union[str, None]
    #    placeOfBirth: Draguignan
    #}
    flatexBankAccount = Union[dict, None]
    #{
    #    bic = Union[str, None]
    #    iban = Union[str, None]
    #}
    id = Union[str, None]
    intAccount = Union[str, None]
    isAllocationAvailable = Union[str, None]
    isAmClientActive = Union[str, None]

    def set_data(self, data : dict):
        _check_keys(data, ('intAccount', 'id'))
        _set_data(self, data)
        return self


@dataclasses.dataclass
class Session:
    JSESSIONID = 'JSESSIONID'

    config : Union[Config, None] = None
    client : Union[PAClient, None] = None

    # Cookies
    # Wrap to not leak httpx
    _cookies : Union[httpx.Cookies, None] = None

    @property
    def cookies(self):
        return dict(self._cookies)

    @cookies.setter
    def cookies(self, cookies : dict):
        self._cookies = httpx.Cookies(cookies)


class URLs:
    BASE = 'https://trader.degiro.nl'
    LOGIN = join_url(BASE, '/login/secure/login')
    #LOGIN = urljoin(BASE, '/login/secure/login')
    LOGIN_TOTP = join_url(BASE, '/login/secure/login/totp')
    CONFIG = join_url(BASE, '/login/secure/config')
    ACCOUNT_INFO = join_url(BASE, '/trading/secure/v5/account/info')
    NEWS_BY_COMPANY = join_url(BASE, '/dgtbxdsservice/newsfeed/v2/news-by-company')

    @staticmethod
    def get_client_info_url(session : Session) -> str:
        """
        Build client info url.
        """
        if session.config is None:
            raise AssertionError("session.config is not set. Call get_config first.")
        return os.path.join(session.config.paUrl, 'client')

    @staticmethod
    def get_portfolio_url(session : Session) -> str:
        """
        Build portfolio url
        """
        if session.config is None:
            raise AssertionError("session.config is not set. Call get_config first.")
        if session.client is None:
            raise AssertionError("session.client is not set. Call get_client_info first.")

        jsessionid = session._cookies[session.JSESSIONID]

        url = (f'{session.config.tradingUrl}'
            f'v5/update/{session.client.intAccount}'
            f';jsessionid={jsessionid}')
        #url = (f'{session.trading_url}v5/update/{session.int_account}'
            #f';jsessionid={jsessionid}')
        LOGGER.debug('get_portfolio_url: %s', url)
        return url


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

class Product:
    class Type:
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

class Sort:
    ASC = "asc"
    DESC = "desc"


# Logs helpers
FORMAT_DEFAULT = '%(asctime)s-%(name)s-%(levelname)s- %(message)s'
STREAMHANDLER_DEFAULT = logging.StreamHandler(stream=sys.stdout)

def set_logs(
        logger : logging.Logger,
        logging_level : int,
        log_format : str = FORMAT_DEFAULT,
        handler : logging.Handler = STREAMHANDLER_DEFAULT
        ):
    "Configure logging for this module."
    # Configure logging
    logger.setLevel(logging_level)
    #handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging_level)
    # DEBUG: Will need to find where another handler is being added when running tests. nose2 catches loggers by default.
    #logger.addHandler(handler)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)

