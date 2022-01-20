"""
Async API for Degiro that is close to Degiro Web API.

For a higher level api, see `api` module.
"""
import json
import base64
import struct
import hmac
import hashlib
import time
import logging
from typing import Union
from typing import Any
from typing import List
from collections import namedtuple
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx


from .core import LOGGER_NAME
from .core import Credentials, Session, URLs, DegiroStatus, Config, PAClient
from .core import join_url

__name__ = [
    'login',
    'get_config'
        ]

LOGGER = logging.getLogger(LOGGER_NAME)


async def login(
        credentials : Credentials,
        session : Union[Session, None]) -> Session:
    """
    Authentify with Degiro API.
    `session` will be updated with required data for further connections.
    If no `session` is provided, create one.
    """
    url = URLs.LOGIN
    session = session or Session()
    payload = {
        "username": credentials.username,
        "password": credentials.password,
        "isRedirectToMobile": False,
        "isPassCodeReset": '',
        "queryParams": {"reason": "session_expired"}
        #"queryParams": {}
            }
    async with httpx.AsyncClient() as client:
        LOGGER.debug('url: %s | payload %s', url, payload)
        response = await client.post(url, data=json.dumps(payload))
        LOGGER.debug(response.__dict__)
        #session._cookies = response.cookies

        response_load = response.json()

        if response_load['status'] == DegiroStatus.TOTP_NEEDED:
            # totp needed
            if credentials.totp_secret is not None:
                payload["oneTimePassword"] = _get_totp_token(credentials.totp_secret)
                url = URLs.LOGIN_TOTP
                LOGGER.debug("run totp login at %s", url)
                response = await client.post(
                        url,
                        data=json.dumps(payload),
                        cookies=response.cookies)
                LOGGER.debug(response.__dict__)
                LOGGER.debug(response.json())
            else:
                raise AssertionError("Account has TOTP enabled, no TOTP secret provided.")

        _check_response(response)
        session._cookies = response.cookies

        if Session.JSESSIONID not in session._cookies:
            LOGGER.error("No JSESSIONID in response: %s", response)
            LOGGER.error("No JSESSIONID in response cookies: %s", response.cookies)
            raise AssertionError("No JSESSIONID in response.")

        return session


async def get_client_info(session : Session):
    async with httpx.AsyncClient() as client:
        raise NotImplementedError


async def get_config(session : Session) -> Session:
    """
    Populate session with configuration
    """
    _check_active_session(session)
    async with httpx.AsyncClient() as client:
        res = await client.get(URLs.CONFIG, cookies=session._cookies)

    _check_response(res)
    config = Config()
    config.set_data(res.json()['data'])

    session.config = config

    return session


async def get_client_info(session : Session) -> Session:
    """
    Get client information.
    """
    url = URLs.get_client_info_url(session)
    async with httpx.AsyncClient() as client:
        res = await client.get(url,
                params={'sessionId': session._cookies[session.JSESSIONID]},
                cookies=session._cookies)

    _check_response(res)
    session.client = PAClient().set_data(res.json()['data'])
    #session.int_account = resp_json['data']['intAccount']
    #session.client_id = resp_json['data']['id']
    return session


async def get_account_info(session: Session) -> Session:
    """
    
    """
    _check_active_session(session)
    url = '/'.join((URLs.ACCOUNT_INFO, session.client.intAccount))
    raise NotImplementedError
    async with httpx.AsyncClient() as client:
        res = await client.get(U)


async def get_portfolio(session : Session):
    """
    Get portfolio web call.
    """
    url = URLs.get_portfolio_url(session)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, cookies=session._cookies,
                params={'portfolio': 0, 'totalPortfolio': 0})

    _check_response(response)
    LOGGER.debug(response.json())
    return response


async def get_products_info(session : Session, products_ids : List[str]):
    """
    Get Product info Web API call.
    """
    if session.config.productSearchUrl is None:
        raise AssertionError("productSearchUrl is None:"
                " have you called get_config?")

    url = join_url(session.config.productSearchUrl,
            'v5/products/info')
    async with httpx.AsyncClient() as client:
        response = await client.post(url,
                cookies=session.cookies,
                params={
                    'intAccount': session.client.intAccount,
                    'sessionId': session.config.sessionId
                    },
                json=products_ids
                )
        _check_response(response)
        LOGGER.debug(response.json())
        return response


async def get_company_profile(session : Session, isin : str) -> httpx.Response:
    """
    Get company profile.

    Example return
    """
    # should this url be taken from config as well?

    # Look for dgtbxdsservice in network logs for financial statements etc.
    # might have intraday data as well
    url = join_url(URLs.BASE, 'dgtbxdsservice/company-profile/v2', isin)
    async with httpx.AsyncClient() as client:
        response = await client.get(url,
                cookies=session.cookies,
                params={
                    'intAccount': session.client.intAccount,
                    'sessionId': session.config.sessionId
                    })
    _check_response(response)
    LOGGER.debug(response.json())
    return response


async def get_news_by_company(
        session : Session,
        isin : str,
        limit : int = 10,
        languages : List[str] = ['en'],
        offset : int = 0
        ):
    """
    Get news for a company.
    """
    url = URLs.NEWS_BY_COMPANY
    async with httpx.AsyncClient() as client:
        response = await client.get(url,
                cookies=session.cookies,
                params={
                    'isin': isin,
                    'limit': limit,
                    'languages': languages,
                    'offset': offset,
                    'intAccount': session.client.intAccount,
                    'sessionId': session.config.sessionId
                    })
    _check_response(response)
    LOGGER.debug(response.json())
    return response


###########
# Helpers #
###########


def _check_active_session(session : Session):
    """
    Check that session id has been populated. Raise AssertionError if not.
    """
    if Session.JSESSIONID not in session._cookies:
        raise AssertionError("No JSESSIONID in session.cookies")


def _check_response(response : httpx.Response):
    """

    """
    if response.status_code != httpx.codes.OK:
        raise httpx.HTTPError(f"Error on call: url {response.url}"
                f" | code {response.status_code} | content {response.content}")


def _get_totp_token(secret_key : str) -> str:
    "Get one-time-password from secret key"
    key = base64.b32decode(secret_key)
    message = struct.pack(">Q", int(time.time()) // 30)
    message_hash = hmac.new(key, message, hashlib.sha1).digest()
    o = message_hash[19] & 15
    message_hash = (struct.unpack(">I", message_hash[o:o+4])[0] & 0x7fffffff) % 1000000
    return message_hash

