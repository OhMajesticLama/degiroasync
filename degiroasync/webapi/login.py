from typing import Union, Dict, Any, Optional
import logging
import json
import base64
import struct
import hmac
import hashlib
import time

from ..core.constants import LOGGER_NAME
from ..core.constants import LOGIN
from ..core.constants import TIMEOUT
from ..core import Credentials, SessionCore, URLs, Config, PAClient
from ..core import check_session_config
from ..core.helpers import check_response
from ..core.helpers import camelcase_dict_to_snake
from ..core.helpers import ThrottlingClient

LOGGER = logging.getLogger(LOGGER_NAME)


# Dedicated Throttling client for login as it is much more restricted.
_LOGIN_THROTTLE = ThrottlingClient(max_requests=1, period_seconds=2)


async def login(
        credentials: Credentials,
        session: Optional[SessionCore] = None) -> SessionCore:
    """
    Authentify with Degiro API.
    `session` will be updated with required data for further connections.
    If no `session` is provided, create one.
    """
    url = URLs.LOGIN
    session = session or SessionCore()
    payload = {
        "username": credentials.username,
        "password": credentials.password,
        "isRedirectToMobile": False,
        "isPassCodeReset": '',
        "queryParams": {"reason": "session_expired"}
    }
    async with _LOGIN_THROTTLE as client:
        LOGGER.debug("login| url %s", url)
        response = await client.post(url, content=json.dumps(payload))
        LOGGER.debug("login| response %s", response.__dict__)

        response_load = response.json()

        if response_load['status'] == LOGIN.TOTP_NEEDED:
            # totp needed
            if (credentials.totp_secret is None and
                    credentials.one_time_password is None):
                raise AssertionError(
                    "Account has TOTP enabled, but no TOTP secret"
                    " nor one_time_password was provided.")
            elif credentials.totp_secret is not None:
                payload["oneTimePassword"] = _get_totp_token(
                    credentials.totp_secret)
            elif credentials.one_time_password is not None:
                payload["oneTimePassword"] = credentials.one_time_password

            url = URLs.LOGIN_TOTP
            LOGGER.debug("run totp login at %s", url)
            response = await client.post(
                url,
                content=json.dumps(payload),
                cookies=response.cookies)
            LOGGER.debug(response.__dict__)
            LOGGER.debug(response.json())

        check_response(response)
        session._cookies = response.cookies

        if SessionCore.JSESSIONID not in session._cookies:
            LOGGER.error("No JSESSIONID in response: %s", response)
            LOGGER.error("No JSESSIONID in response cookies: %s",
                         response.cookies)
            raise AssertionError("No JSESSIONID in response.")

        return session


async def get_config(session: SessionCore) -> SessionCore:
    """
    Populate session with configuration
    """
    _check_active_session(session)
    async with session as client:
        res = await client.get(URLs.CONFIG, cookies=session._cookies)

    check_response(res)
    config = Config(camelcase_dict_to_snake(res.json()['data']))

    session.config = config

    return session


async def get_client_info(session: SessionCore) -> SessionCore:
    """
    Get client information.
    """
    url = URLs.get_client_info_url(session)

    async with session as client:
        res = await client.get(
            url,
            params={'sessionId': session._cookies[session.JSESSIONID]},
            cookies=session._cookies)

    check_response(res)
    resp_data = res.json()['data']
    if 'id' in resp_data:
        resp_data['id'] = str(resp_data['id'])
    session.client = PAClient(camelcase_dict_to_snake(resp_data))
    return session


async def get_account_info(session: SessionCore) -> SessionCore:
    """

    """
    _check_active_session(session)
    url = URLs.get_account_info_url(session)
    async with session as client:
        res = await client.get(url,
                               cookies=session._cookies
                               )
    check_response(res)
    res_json = res.json()
    LOGGER.debug("get_account_info| res_json %s", res_json)
    return res_json


async def get_product_dictionary(session: SessionCore) -> Dict[str, Any]:
    """
    Get product dictionary information from server.

    This is needed to provide human-redeable product data for products:

    - Bonds, CFD Exchange places.
    - ETF fees types.
    - Countries.

    Returns
    -------

        Example JSON below, most rows were removed to keepsome structure
        readibility. Example from 2023.07.

        ``` JSON
        {'bondExchanges': [{'country': 905, 'exchange': 5001, 'id': 5001},
                           {'country': 846,
                            'exchange': 676,
                            'id': 676,
                            'postfix': 'NYSE'},
                           {'country': 957, 'exchange': 999, 'id': 999},
                           {'country': 846,
                            'exchange': 663,
                            'id': 663,
                            'postfix': 'NASDAQ'},
                           {'country': 915, 'exchange': 608, 'id': 608}],
         'bondIssuerTypes': [{'id': 0,
                              'name': 'all',
                              'translation': 'Koersen.step1.530'},
                             {'id': 2,
                              'name': 'company',
                              'translation': 'Koersen.step1.544'}],
         'bondSortColumns': [{'id': 'exchangeHiqAbbr'},
                             {'id': 'name'},
                             {'id': 'exchangeName'}],
         'cfdExchanges': [{'country': 906, 'exchange': 194, 'id': 194},
                          {'country': 975, 'exchange': 508, 'id': 508},
                          {'country': 915, 'exchange': 608, 'id': 608}],
         'cfdSortColumns': [{'id': 'exchangeHiqAbbr'},
                            {'id': 'name'},
                            {'id': 'exchangeName'}],
         'combinationExchanges': [{'id': 1, 'name': 'Euronext Amsterdam'},
                                  {'id': 2, 'name': 'Euronext Brussels'},
                                  {'id': 3, 'name': 'Euronext Paris'}],
         'countries': [{'id': 908,
                        'name': 'FI',
                        'region': 1,
                        'translation': 'list.country.908'},
                       {'id': 906,
                        'name': 'DE',
                        'region': 1,
                        'translation': 'list.country.906'}],
         'etfAggregateTypes': [{'id': 'quoteCurrency',
                                'name': 'quoteCurrency'},
                               {'id': 'totalExpenseRatioInterval',
                                'name': 'totalExpenseRatioInterval'},
                               {'id': 'administrator',
                                'name': 'administrator'},
                               {'id': 'etpType', 'name': 'etpType'},
                               {'id': 'exchange', 'name': 'exchange'},
                               {'id': 'region', 'name': 'region'},
                               {'id': 'assetAllocation',
                                'name': 'assetAllocation'},
                               {'id': 'issuer', 'name': 'issuer'},
                               {'id': 'benchmark', 'name': 'benchmark'}],
         'etfFeeTypes': [{'id': 1,
                          'name': 'Trackers',
                          'translation': 'contract.type.131'},
                         {'id': 2,
                          'name': 'Free',
                          'translation': 'translation.label.388'}],
         'etfSortColumns': [{'id': 'quoteCurrency'},
                            {'id': 'administrator'},
                            {'id': 'etpType'},
                            {'id': 'exchangeHiqAbbr'},
                            {'id': 'name'},
                            {'id': 'exchangeName'},
                            {'id': 'region'},
                            {'id': 'assetAllocation'},
                            {'id': 'benchmark'}],
         'eurexCountries': [{'exchanges': [{'city': 'Helsinki',
                                            'code': 'HE',
                                            'country': 'FI',
                                            'hiqAbbr': 'HSE',
                                            'id': 1001,
                                            'micCode': 'XHEL',
                                            'name': 'OMX Helsinki'}],
                             'id': 908,
                             'name': 'FI',
                             'underlyingExchangeIds': [1001]},
                            {'exchanges': [{'city': 'Frankfurt',
                                            'code': 'XETR',
                                            'country': 'DE',
                                            'hiqAbbr': 'XET',
                                            'id': 194,
                                            'micCode': 'XETR',
                                            'name': 'Xetra'}],
                             'id': 906,
                             'name': 'DE',
                             'underlyingExchangeIds': [194]}],
         'exchanges': [{'city': 'Frankfurt',
                        'code': 'CATS',
                        'country': 'DE',
                        'hiqAbbr': 'CAT',
                        'id': 190,
                        'micCode': 'CATS',
                        'name': 'CATS'},
                       {'city': 'Amsterdam',
                        'country': 'XX',
                        'hiqAbbr': 'FSM',
                        'id': 10000,
                        'name': 'FundShare Matching'},
                       {'city': 'Copenhagen',
                        'code': 'CO',
                        'country': 'DK',
                        'hiqAbbr': 'OMK',
                        'id': 508,
                        'micCode': 'XCSE',
                        'name': 'OMX Copenhagen'}],
         'futureExchanges': [{'id': 1, 'name': 'Euronext Liffe'},
                             {'eurexCountries': [908,
                                                 915,
                                                 906],
                              'id': 2,
                              'name': 'Eurex'},
                             {'id': 9, 'name': 'COMEX'}],
         'futureSortColumns': [{'id': 'exchangeHiqAbbr'},
                               {'id': 'name'},
                               {'id': 'exchangeName'},
                               {'id': 'expirationDate'}],
         'indices': [{'id': 106002, 'name': 'SDAX'},
                     {'id': 106001, 'name': 'MDAX'},
                     {'id': 121003, 'name': 'SMIM', 'productId': 11875105},
                     {'id': 114003, 'name': 'ISEQ Overall'},
                     {'id': 121002, 'name': 'SLI', 'productId': 11875104}],
         'investmentFundAggregateTypes': [{'id': 'issuer', 'name': 'issuer'}],
         'investmentFundFeeTypes': [{'id': 0,
                                     'name': 'Rebate-free',
                                     'translation': 'translation.label.387'},
                                    {'id': 3,
                                     'name': 'Rebate-free FREE',
                                     'translation': 'translation.label.386'}],
         'investmentFundSortColumns': [{'id': 'exchangeHiqAbbr'},
                                       {'id': 'name'},
                                       {'id': 'exchangeName'}],
         'leveragedAggregateTypes': [{'id': 'shortLong', 'name': 'shortLong'},
                                     {'id': 'underlyingProductId',
                                      'name': 'underlyingProductId'},
                                     {'id': 'exchange', 'name': 'exchange'},
                                     {'id': 'underlying', 'name': 'underlying'},
                                     {'id': 'issuer', 'name': 'issuer'},
                                     {'id': 'expirationDateRange',
                                      'name': 'expirationDateRange'}],
         'leveragedSortColumns': [{'id': 'leverage'},
                                  {'id': 'financingLevel'},
                                  {'id': 'stoploss'},
                                  {'id': 'exchangeHiqAbbr'},
                                  {'id': 'name'},
                                  {'id': 'exchangeName'},
                                  {'id': 'expirationDate'}],
         'lookupSortColumns': [{'id': 'exchangeHiqAbbr'},
                               {'id': 'name'},
                               {'id': 'exchangeName'},
                               {'id': 'productType'}],
         'optionAggregateTypes': [{'id': 'month', 'name': 'month'},
                                  {'id': 'derivativeExchange',
                                   'name': 'derivativeExchange'},
                                  {'id': 'year', 'name': 'year'},
                                  {'id': 'strike', 'name': 'strike'}],
         'optionExchanges': [{'exchangeId': 365, 'id': 11, 'name': 'NYMEX'},
                             {'exchangeId': 1006,
                              'id': 1,
                              'name': 'Euronext Amsterdam',
                              'underlyingExchangeIds': [200, 212, 3001]},
                             {'eurexCountries': [908,
                                                 982,
                                                 906],
                              'exchangeId': 185,
                              'id': 5,
                              'name': 'Eurex',
                              'underlyingExchangeIds': [1001,
                                                        320,
                                                        608,
                                                        194]},
                             {'exchangeId': 359, 'id': 9, 'name': 'CME'}],
         'optionSortColumns': [{'id': 'strike'}, {'id': 'expirationDate'}],
         'productTypes': [{'briefTranslation': 'contract.type.brief.13',
                           'contractType': 'FND',
                           'id': 13,
                           'name': 'fund',
                           'translation': 'contract.type.13'},
                          {'briefTranslation': 'contract.type.brief.8',
                           'contractType': 'OPT',
                           'id': 8,
                           'name': 'option',
                           'translation': 'contract.type.8'}],
         'regions': [{'id': 1,
                      'name': 'Europe',
                      'translation': 'translation.label.117'},
                     {'id': 2,
                      'name': 'America',
                      'translation': 'translation.label.118'},
                     {'id': 3,
                      'name': 'Other',
                      'translation': 'translation.label.121'}],
         'stockCountries': [{'country': 908,
                             'id': 908,
                             'indices': [112002, 16, 112001, 120005]},
                            {'country': 849, 'id': 849, 'indices': [124001]},
                            {'country': 905, 'id': 905, 'indices': [123001]},
                            {'country': 906,
                             'id': 906,
                             'indices': [6, 106002, 106003, 106001]}],
         'stockSortColumns': [{'id': 'exchangeHiqAbbr'},
                              {'id': 'name'},
                              {'id': 'exchangeName'}]}
        ```
    """
    check_session_config(session)
    url = URLs.get_product_dictionary_url(session)
    params = dict(
        intAccount=session.client.int_account,
        sessionId=session.config.session_id
    )
    async with session as client:
        response = await client.get(url,
                                    cookies=session._cookies,
                                    params=params
                                    )
    check_response(response)
    LOGGER.debug("webapi.get_product_dictionary response| %s", response.json())
    return response.json()


###########
# Helpers #
###########

def _check_active_session(session: SessionCore):
    """
    Check that session id has been populated. Raise AssertionError if not.
    """
    if SessionCore.JSESSIONID not in session._cookies:
        raise AssertionError("No JSESSIONID in session.cookies")


def _get_totp_token(secret_key: str) -> str:
    "Get one-time-password from secret key"
    key = base64.b32decode(secret_key)
    message = struct.pack(">Q", int(time.time()) // 30)
    message_hash = hmac.new(key, message, hashlib.sha1).digest()
    o = message_hash[19] & 15
    message_hash = (struct.unpack(">I",
                    message_hash[o:o + 4])[0] & 0x7fffffff) % 1000000
    return message_hash


__all__ = [
    login.__name__,
    get_account_info.__name__,
    get_config.__name__
]
