import unittest
import logging
import os
import pprint
import asyncio


import degiroasync
import degiroasync.webapi
import degiroasync.core
import degiroasync.core.helpers
from degiroasync.core import Credentials
from degiroasync.webapi import get_config
from degiroasync.webapi import get_products_info
from degiroasync.webapi import get_company_profile
from degiroasync.webapi import get_news_by_company


LOGGER = logging.getLogger(degiroasync.core.LOGGER_NAME)
degiroasync.core.helpers.set_logs(LOGGER, logging.DEBUG)

RUN_INTEGRATION_TESTS = 0
try:
    _env_var = os.environ.get('DEGIROASYNC_INTEGRATION')
    RUN_INTEGRATION_TESTS = int(_env_var)
except ValueError:
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
    totp_secret = os.environ.get('DEGIRO_TOTP_SECRET')

    return Credentials(username, password, totp_secret)


#def mock_asyncclient(mock):
#    pass
#
#
#class TestDegiroWebAPIUnit(unittest.IsolatedAsyncioTestCase):
#    @unittest.mock.patch('httpx.AsyncClient')
#    async def test_confirm_order(self, asyncclient_mock):
#        pass


if RUN_INTEGRATION_TESTS:
    LOGGER.info('degiroasync.webapi integration tests will run.')

    class _IntegrationWebLogin:
        """
        Internal helper, can be inherited to make login for integration tests
        easier.
        """
        async def asyncSetUp(self):
            self._lock = asyncio.Lock()

        async def _login(self):
            async with self._lock:
                if not hasattr(self, 'session'):
                    credentials = _get_credentials()
                    self.session = await degiroasync.webapi.login(credentials)
                    await degiroasync.webapi.get_config(self.session)
                    await degiroasync.webapi.get_client_info(self.session)
            return self.session

    class TestDegiroWebAPIIntegration(
            _IntegrationWebLogin,
            unittest.IsolatedAsyncioTestCase):

        async def test_login(self):
            session = await self._login()
            self.assertTrue('JSESSIONID' in session.cookies,
                            "No JSESSIONID found.")

        async def test_config(self):
            session = await self._login()
            await get_config(session)
            LOGGER.debug('test_config| %s', session.config)
            self.assertTrue(session.config.paUrl is not None,
                    "paUrl not defined.")
            self.assertTrue(session.config.productSearchUrl is not None,
                    "productSearchUrl not defined.")
            self.assertTrue(session.config.tradingUrl is not None,
                    "tradingUrl not defined.")

        async def test_porfolio(self):
            session = await self._login()

            response = await degiroasync.webapi.get_portfolio(session)
            self.assertEquals(response.status_code, 200)
            resp_json = response.json()
            self.assertTrue('portfolio' in resp_json)
            self.assertTrue('value' in resp_json['portfolio'])

        async def test_get_products_info(self):
            session = await self._login()

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
            session = await self._login()

            isin = "FR0010242511"
            response = await get_company_profile(session, isin)
            resp_json = response.json()
            self.assertEquals(response.status_code, 200)
            self.assertTrue('data' in resp_json, resp_json)
            self.assertTrue('businessSummary' in resp_json['data'], resp_json)
            LOGGER.debug('webapi.test_get_company_profile| %s',
                    pprint.pformat(resp_json))

        async def test_get_news_by_company(self):
            session = await self._login()

            isin = "FR0010242511"
            response = await get_news_by_company(session, isin)
            resp_json = response.json()
            self.assertEquals(response.status_code, 200)
            self.assertTrue('data' in resp_json, resp_json)
            self.assertTrue('items' in resp_json['data'], resp_json)

        async def test_get_price_data(self):
            session = await self._login()

            vwdId = '360114899'

            response = await degiroasync.webapi.get_price_data(
                    session,
                    vwdId=vwdId,
                    vwdIdentifierType='issueid')
            LOGGER.debug('get_price_data response: %s', response.content)
            self.assertEqual(response.status_code, 200)
            resp_json = response.json()
            LOGGER.debug(resp_json)
            self.assertTrue('series' in resp_json)
            self.assertTrue('data' in resp_json['series'][0])

        async def test_search_product(self):
            session = await self._login()

            search = "AIRBUS"
            response = await degiroasync.webapi.search_product(session, search)
            resp_json = response.json()
            self.assertEqual(response.status_code, 200, resp_json)
            self.assertIn('products', resp_json, resp_json)
            self.assertGreaterEqual(len(resp_json['products']), 1)
            self.assertIn('id', resp_json['products'][0], resp_json)
            self.assertIn('isin', resp_json['products'][0], resp_json)
            self.assertIn('name', resp_json['products'][0], resp_json)

        async def test_product_dictionary(self):
            session = await self._login()

            response = await degiroasync.webapi.get_product_dictionary(session)
            resp_json = response.json()

            self.assertIn('exchanges', resp_json)
            self.assertIn('countries', resp_json)
            self.assertIn('regions', resp_json)

            # Not used by degiroasync.api at the time this test was written.
            self.assertIn('bondExchanges', resp_json)
            self.assertIn('cfdExchanges', resp_json)
            self.assertIn('combinationExchanges', resp_json)
            self.assertIn('etfAggregateTypes', resp_json)
            self.assertIn('etfFeeTypes', resp_json)
            self.assertIn('eurexCountries', resp_json)

    class TestDegiroWebAPIOrdersIntegration(
            _IntegrationWebLogin,
            unittest.IsolatedAsyncioTestCase):
        """
        Set Orders will *not* be tested: this would imply being charged every
        time tests are executed.
        """
        async def test_get_orders(self):
            session = await self._login()

            response = await degiroasync.webapi.get_orders(session)
            resp_json = response.json()
            LOGGER.debug("test_get_orders| %s", pprint.pformat(resp_json))
            self.assertIn(response.status_code, (200, 201))
            self.assertIn('orders', resp_json)
            self.assertIn('value', resp_json['orders'])

        async def test_check_order(self):
            raise NotImplementedError
