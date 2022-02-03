from __future__ import annotations
import os
import logging
import sys
import dataclasses
import asyncio
import enum

from typing import Union, Any, Iterable

import httpx

from degiroasync import helpers
#from .helpers import check_session_config
from .helpers import check_keys
from .helpers import join_url
from .helpers import setattrs
from .constants import LOGGER_NAME

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
        check_keys(config,
                ('tradingUrl',
                 'sessionId',
                 'paUrl',
                 'productSearchUrl'))
        # Store for debug purpose
        setattrs(self, **config)
        #_set_data(self, config)
        self._config = config
        return self


#def _set_data(obj : object, data : dict):
#    """
#    Helper to assign data as obj attributes.
#    """
#    for key, value in data.items():
#        if not hasattr(obj, key):
#            # Skip unknown config
#            LOGGER.debug(
#                '%s found in API response but not defined as attribute in data', key)
#            continue
#        setattr(obj, key, value)


# Currently unused
#class AwaitableDestructor:
#    # TODO This is at the idea stage: have a singleton class
#    # that other classes that have awaitable internal states should
#    # inherit from to centralize await and facilitate clean program close.
#    """
#    Classes with awaitable states should inherit from this class.
#    """
#    def __init__(self):
#        pass
#
#    async def terminate(self):
#        pass


class PAClient:
    """
    Data Structure for PA Client 
    """
    address : Union[dict, None]
    #{
    #    city = Union[str, None]
    #    country = Union[str, None]
    #    streetAddress = Union[str, None]
    #    streetAddressNumber = Union[str, None]
    #    zip: 83300
    #}
    bankAccount : Union[dict, None]
    #{
    #    bankAccountId = Union[str, None]
    #    bic = Union[str, None]
    #    iban = Union[str, None]
    #    status: VERIFIED
    #}
    canUpgrade : Union[str, None]
    clientRole : Union[str, None]
    contractType : Union[str, None]
    culture : Union[str, None]
    displayLanguage : Union[str, None]
    displayName : Union[str, None]
    effectiveClientRole : Union[str, None]
    email : Union[str, None]
    firstContact : Union[dict, None]
    #{
    #    countryOfBirth : Union[str, None]
    #    dateOfBirth : Union[str, None]
    #    displayName : Union[str, None]
    #    firstName : Union[str, None]
    #    gender : Union[str, None]
    #    lastName : Union[str, None]
    #    nationality : Union[str, None]
    #    placeOfBirth: Union[str, None]
    #}
    flatexBankAccount : Union[dict, None]
    #{
    #    bic = Union[str, None]
    #    iban = Union[str, None]
    #}
    id : Union[str, None]
    intAccount = Union[str, None]
    isAllocationAvailable = Union[str, None]
    isAmClientActive = Union[str, None]

    def set_data(self, data : dict):
        check_keys(data, ('intAccount', 'id'))
        setattrs(self, **data)
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
    LOGIN_TOTP = join_url(BASE, '/login/secure/login/totp')
    CONFIG = join_url(BASE, '/login/secure/config')
    ACCOUNT_INFO = join_url(BASE, '/trading/secure/v5/account/info')

    @staticmethod
    def get_news_by_company_url(session : Session) -> str:
        "Build news_by_company url"
        check_session_config(session)
        return join_url(session.config.refinitivNewsUrl, 'news-by-company')

    @staticmethod
    def get_client_info_url(session : Session) -> str:
        """
        Build client info url.
        """
        check_session_config(session)
        return os.path.join(session.config.paUrl, 'client')

    @staticmethod
    def get_portfolio_url(session : Session) -> str:
        """
        Build portfolio url
        """
        check_session_config(session)
        check_session_client(session)

        jsessionid = session._cookies[session.JSESSIONID]

        url = (f'{session.config.tradingUrl}'
            f'v5/update/{session.client.intAccount}'
            f';jsessionid={jsessionid}')
        #url = (f'{session.trading_url}v5/update/{session.int_account}'
            #f';jsessionid={jsessionid}')
        LOGGER.debug('get_portfolio_url: %s', url)
        return url

    @classmethod
    def get_orders_url(cls, session : Session) -> str:
        """
        Build Get Orders url
        """
        # This is is the same endpoint and url as portfolio
        return cls.get_portfolio_url(session)

    @staticmethod
    def get_price_data_url(session : Session) -> str:
        check_session_config(session)
        # Check if this should be pulled from session config
        return 'https://charting.vwdservices.com/hchart/v1/deGiro/data.js'


def check_session_config(session : Session):
    "Raise an exception if session.config is not set"
    if session.config is None:
        raise AssertionError("session.config is not set. Call get_config first.")


def check_session_client(session : Session):
    "Raise an exception if session.client is not set"
    if session.config is None:
        raise AssertionError("session.client is not set. Call get_client_info first.")
