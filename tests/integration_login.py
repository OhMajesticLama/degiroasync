from typing import Optional
import logging
import os
import asyncio

import degiroasync.api
from degiroasync.api import Session
from degiroasync.core import ResponseError
from degiroasync.core import Credentials

LOGGER = logging.getLogger(degiroasync.core.LOGGER_NAME)

def _get_credentials():
    """
    Helper to get credentials for integration tests
    """
    username = os.environ.get('DEGIRO_USERNAME')
    password = os.environ.get('DEGIRO_PASSWORD')
    assert username is not None, (
        'DEGIRO_USERNAME environment variable not defined.')
    assert password is not None, (
        'DEGIRO_PASSWORD environment variable not defined.')
    totp_secret = os.environ.get('DEGIRO_TOTP_SECRET')

    return Credentials(username, password, totp_secret)


class _IntegrationLogin:
    """
    Internal helper, can be inherited to make login for integration tests
    easier.
    """

    _lock = asyncio.Lock()
    session: Optional[Session] = None
    _login_attempted: bool = False

    @classmethod
    async def _login(cls):
        async with cls._lock:
            if cls.session is None and not cls._login_attempted:
                LOGGER.debug("_IntegrationLogin: attempt login.")
                cls._login_attempted = True
                credentials = _get_credentials()
                cls.session = await degiroasync.api.login(credentials)
        if cls.session is None:
            raise ResponseError("No session available. Maybe Bad Credentials?")
        return cls.session
