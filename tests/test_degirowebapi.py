import unittest
import logging
import os
import pprint


import degiroasync
import degiroasync.webapi
import degiroasync.api
import degiroasync.core
import degiroasync.helpers
from degiroasync.core import Credentials
from degiroasync.core import Session
from degiroasync.core import join_url
from degiroasync.webapi import get_config
from degiroasync.webapi import get_client_info
from degiroasync.webapi import get_products_info
from degiroasync.webapi import get_company_profile
from degiroasync.webapi import get_news_by_company
from degiroasync.api import set_params


LOGGER = logging.getLogger(degiroasync.core.LOGGER_NAME)
degiroasync.helpers.set_logs(LOGGER, logging.DEBUG)

RUN_INTEGRATION_TESTS = 0
try:
    _env_var = os.environ.get('DEGIROASYNC_INTEGRATION')
    RUN_INTEGRATION_TESTS = int(_env_var)
except:
    LOGGER.info('degiroasync integration tests will *not* run.')


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
    try:
        totp_secret = os.environ.get('DEGIRO_TOTP_SECRET')
    except:
        LOGGER.info('DEGIRO_TOTP_SECRET environment variable'
                ' not defined, skip 2FA.')
        totp_secret = None

    return Credentials(username, password, totp_secret)

if RUN_INTEGRATION_TESTS:
    LOGGER.info('degiroasync.webapi integration tests will run.')
    class TestDegiroWebAPIIntegration(unittest.IsolatedAsyncioTestCase):
        async def _login(self, credentials : Credentials):
            # Duplicated between TestDegiroAPI and this class, might 
            # be worth doing in a cleaner way
            credentials = _get_credentials()

            #quick & dirty caching
            try:
                session = Session()
                session.cookies = {
                        Session.JSESSIONID:
                        self._session._cookies[Session.JSESSIONID]}
            except AttributeError:
                session = await degiroasync.webapi.login(credentials, session)
            self._session = session

            return session

        async def test_login(self):
            session = await self._login(_get_credentials())
            self.assertTrue('JSESSIONID' in session.cookies, "No JSESSIONID found.")

        async def test_config(self):
            session = await self._login(_get_credentials())
            await get_config(session)
            self.assertTrue(session.config.paUrl is not None,
                    "paUrl not defined.")
            self.assertTrue(session.config.productSearchUrl is not None,
                    "productSearchUrl not defined.")
            self.assertTrue(session.config.tradingUrl is not None,
                    "tradingUrl not defined.")

        async def test_porfolio(self):
            session = await self._login(_get_credentials())
            await get_config(session)
            await get_client_info(session)

            response = await degiroasync.webapi.get_portfolio(session)
            self.assertEquals(response.status_code, 200)
            resp_json = response.json()
            self.assertTrue('portfolio' in resp_json)
            self.assertTrue('value' in resp_json['portfolio'])

        async def test_get_products_info(self):
            session = await self._login(_get_credentials())
            await get_config(session)
            await get_client_info(session)

            response = await degiroasync.webapi.get_portfolio(session)
            portfolio = response.json()['portfolio']
            product_ids = filter(lambda x: x is not None,
                    (product.get('id')
                    for product in portfolio['value']))
            response = await get_products_info(session, [p for p in product_ids])
            self.assertEquals(response.status_code, 200)

            response = await degiroasync.webapi.get_products_info(session, ["72906"])
            self.assertEqual(response.status_code, 200)
            LOGGER.debug('webapi.test_get_products_info| %s',
                    pprint.pformat(response.json()))
                    

        async def test_get_company_profile(self):
            session = await self._login(_get_credentials())
            await get_config(session)
            await get_client_info(session)

            isin = "FR0010242511"
            response = await get_company_profile(session, isin)
            resp_json = response.json()
            self.assertEquals(response.status_code, 200)
            self.assertTrue('data' in resp_json, resp_json)
            self.assertTrue('businessSummary' in resp_json['data'], resp_json)

        async def test_get_news_by_company(self):
            session = await self._login(_get_credentials())
            await get_config(session)
            await get_client_info(session)

            isin = "FR0010242511"
            response = await get_news_by_company(session, isin)
            resp_json = response.json()
            self.assertEquals(response.status_code, 200)
            self.assertTrue('data' in resp_json, resp_json)
            self.assertTrue('items' in resp_json['data'], resp_json)

        async def test_get_price_data(self):
            session = await self._login(_get_credentials())
            await get_config(session)
            await get_client_info(session)
            # TODO: test with search product once implemented

            #response = await degiroasync.webapi.get_portfolio(session)
            #portfolio = response.json()['portfolio']
            #product_ids = filter(lambda x: x is not None,
            #        (product.get('id')
            #        for product in portfolio['value']))

            # get product vwdId from get_products_info
            # vwdId can be obtained from get_products_info
            #response = await get_products_info(session, [p for p in product_ids])
            #self.assertEquals(response.status_code, 200)

            vwdId = 360114899

            response = await degiroasync.webapi.get_price_data(session, vwdId)
            LOGGER.debug('get_price_data response: %s', response.content)
            self.assertEqual(response.status_code, 200)
            resp_json = response.json()
            LOGGER.debug(resp_json)
            self.assertTrue('series' in resp_json)
            self.assertTrue('data' in resp_json['series'][0])


