import unittest
import logging
import os


import degiroasync
import degiroasync.webapi
import degiroasync.core
from degiroasync.core import Credentials
from degiroasync.core import Session
from degiroasync.core import join_url
from degiroasync.webapi import get_config
from degiroasync.webapi import get_client_info
from degiroasync.webapi import get_products_info
from degiroasync.webapi import get_company_profile
from degiroasync.webapi import get_news_by_company

LOGGER = logging.getLogger(degiroasync.core.LOGGER_NAME)
degiroasync.core.set_logs(LOGGER, logging.DEBUG)

RUN_INTEGRATION_TESTS = 0
try:
    _env_var = os.environ.get('DEGIROASYNC_INTEGRATION')
    RUN_INTEGRATION_TESTS = int(_env_var)
except:
    LOGGER.info('degiroasync integration tests will *not* run.')

# Unittests
class TestDegiroAPI(unittest.TestCase):
    pass

class TestDegiroAsyncCore(unittest.TestCase):
    def test_join_url(self):
        url = join_url('https://foo.bar', '/rest/of/url')
        self.assertEquals(url, 'https://foo.bar/rest/of/url')
        url = join_url('https://foo.bar/product', '/rest/of/url')
        self.assertEquals(url, 'https://foo.bar/product/rest/of/url')
        url = join_url('https://foo.bar/product/', '/rest/of/url')
        self.assertEquals(url, 'https://foo.bar/product/rest/of/url')


# Integration tests
if RUN_INTEGRATION_TESTS:
    LOGGER.info('degiroasync integration tests will run.')
    class TestDegiroWebAPIIntegration(unittest.IsolatedAsyncioTestCase):
        def _get_credentials(self):
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

        async def _login(self, credentials : Credentials):
            credentials = self._get_credentials()

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
            session = await self._login(self._get_credentials())
            self.assertTrue('JSESSIONID' in session.cookies, "No JSESSIONID found.")

        async def test_config(self):
            session = await self._login(self._get_credentials())
            await get_config(session)
            self.assertTrue(session.config.paUrl is not None,
                    "paUrl not defined.")
            self.assertTrue(session.config.productSearchUrl is not None,
                    "productSearchUrl not defined.")
            self.assertTrue(session.config.tradingUrl is not None,
                    "tradingUrl not defined.")

        async def test_porfolio(self):
            session = await self._login(self._get_credentials())
            await get_config(session)
            await get_client_info(session)

            response = await degiroasync.webapi.get_portfolio(session)
            self.assertEquals(response.status_code, 200)
            resp_json = response.json()
            self.assertTrue('portfolio' in resp_json)
            self.assertTrue('value' in resp_json['portfolio'])

        async def test_get_products_info(self):
            session = await self._login(self._get_credentials())
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
            LOGGER.debug(response.content)
            self.assertEqual(response.status_code, 200)
                    

        async def test_get_company_profile(self):
            session = await self._login(self._get_credentials())
            await get_config(session)
            await get_client_info(session)

            isin = "FR0010242511"
            response = await get_company_profile(session, isin)
            resp_json = response.json()
            self.assertEquals(response.status_code, 200)
            self.assertTrue('data' in resp_json, resp_json)
            self.assertTrue('businessSummary' in resp_json['data'], resp_json)

        async def test_get_news_by_company(self):
            session = await self._login(self._get_credentials())
            await get_config(session)
            await get_client_info(session)

            isin = "FR0010242511"
            response = await get_news_by_company(session, isin)
            resp_json = response.json()
            self.assertEquals(response.status_code, 200)
            self.assertTrue('data' in resp_json, resp_json)
            self.assertTrue('items' in resp_json['data'], resp_json)


if __name__ == '__main__':
    import nose2
    nose2.main()
