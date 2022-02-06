from __future__ import annotations
import os
import logging
import sys
import dataclasses
import asyncio
import enum

from typing import Union, Any, Iterable

import httpx
from jsonloader import JSONclass

from degiroasync.core import helpers
#from .helpers import check_session_config
from .helpers import check_keys
from .helpers import join_url
from .helpers import setattrs
from .helpers import ResponseError
from .constants import LOGGER_NAME

LOGGER = logging.getLogger(LOGGER_NAME)



@dataclasses.dataclass
class Credentials:
    username : str
    password : str
    totp_secret : Union[str, None] = None


#@dataclasses.dataclass
@JSONclass(annotations=True, annotations_type=True)
class Config:
    # SessionCore config, as returned by Degiro
    clientId : int
    companiesServiceUrl : Union[str, None]
    dictionaryUrl : str
    i18nUrl : Union[str, None]
    landingPath : Union[str, None]
    latestSearchedProductsUrl : Union[str, None]
    loginUrl : str
    mobileLandingPath : Union[str, None]
    paUrl : str
    paymentServiceUrl : Union[str, None]
    productNotesUrl : Union[str, None]
    productSearchUrl : str
    productTypesUrl : str
    refinitivAgendaUrl : Union[str, None]
    refinitivClipsUrl : Union[str, None]
    refinitivCompanyProfileUrl : Union[str, None]
    refinitivCompanyRatiosUrl : Union[str, None]
    refinitivEsgsUrl : Union[str, None]
    refinitivEstimatesUrl : Union[str, None]
    refinitivFinancialStatementsUrl : Union[str, None]
    refinitivInsiderTransactionsUrl : Union[str, None]
    refinitivInsidersReportUrl : Union[str, None]
    refinitivInvestorUrl : Union[str, None]
    refinitivNewsUrl : Union[str, None]
    refinitivShareholdersUrl : Union[str, None]
    refinitivTopNewsCategoriesUrl : Union[str, None]
    reportingUrl : Union[str, None]
    sessionId : Union[str, None]
    taskManagerUrl : Union[str, None]
    tradingUrl : Union[str, None]
    translationsUrl : Union[str, None]
    vwdGossipsUrl : Union[str, None]
    vwdNewsUrl : Union[str, None]
    vwdQuotecastServiceUrl : Union[str, None]


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


@JSONclass(annotations=True, annotations_type=True)
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

    #def set_data(self, data : dict):
    #    check_keys(data, ('intAccount', 'id'))
    #    setattrs(self, **data)
    #    return self


@dataclasses.dataclass
class SessionCore:
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
    def get_news_by_company_url(session : SessionCore) -> str:
        "Build news_by_company url"
        check_session_config(session)
        return join_url(session.config.refinitivNewsUrl, 'news-by-company')

    @staticmethod
    def get_client_info_url(session : SessionCore) -> str:
        """
        Build client info url.
        """
        check_session_config(session)
        return join_url(session.config.paUrl, 'client')

    @staticmethod
    def get_portfolio_url(session : SessionCore) -> str:
        """
        Build portfolio url
        """
        check_session_config(session)
        check_session_client(session)

        jsessionid = session._cookies[session.JSESSIONID]

        url = join_url(
            session.config.tradingUrl,
            f'v5/update/{session.client.intAccount}',
            f';jsessionid={jsessionid}')
        LOGGER.debug('get_portfolio_url: %s', url)
        return url

    @classmethod
    def get_orders_url(cls, session : SessionCore) -> str:
        """
        Build Get Orders url
        """
        # This is is the same endpoint and url as portfolio
        return cls.get_portfolio_url(session)

    @staticmethod
    def get_price_data_url(session : SessionCore) -> str:
        check_session_config(session)
        # Check if this should be pulled from session config
        return 'https://charting.vwdservices.com/hchart/v1/deGiro/data.js'

    @staticmethod
    def get_product_search_url(session : SessionCore) -> str:
        check_session_config(session)
        url = join_url(
                session.config.productSearchUrl,
                'v5/products/lookup')
        LOGGER.debug('get_product_search_url: %s', url)
        return url

    @staticmethod
    def get_product_dictionary_url(session : SessionCore) -> str:
        check_session_config(session)
        url = session.config.dictionaryUrl
        LOGGER.debug('get_product_search_url: %s', url)
        return url


def check_session_config(session : SessionCore):
    "Raise an exception if session.config is not set"
    if session.config is None:
        raise AssertionError("session.config is not set. Call get_config first.")


def check_session_client(session : SessionCore):
    "Raise an exception if session.client is not set"
    if session.config is None:
        raise AssertionError("session.client is not set. Call get_client_info first.")
