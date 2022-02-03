import unittest
import logging
import os
import pprint
import asyncio


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
from degiroasync.api import convert_time_series
from degiroasync.api import Product
from degiroasync.constants import ProductConst
from .test_degirowebapi import _get_credentials


LOGGER = logging.getLogger(degiroasync.core.LOGGER_NAME)
degiroasync.helpers.set_logs(LOGGER, logging.DEBUG)

RUN_INTEGRATION_TESTS = 0
try:
    _env_var = os.environ.get('DEGIROASYNC_INTEGRATION')
    RUN_INTEGRATION_TESTS = int(_env_var)
except:
    LOGGER.info('degiroasync integration tests will *not* run.')


#############
# Unittests #
#############
class TestDegiroAsyncHelpers(unittest.TestCase):
    def test_join_url(self):
        url = join_url('https://foo.bar', '/rest/of/url')
        self.assertEquals(url, 'https://foo.bar/rest/of/url')
        url = join_url('https://foo.bar/product', '/rest/of/url')
        self.assertEquals(url, 'https://foo.bar/product/rest/of/url')
        url = join_url('https://foo.bar/product/', '/rest/of/url')
        self.assertEquals(url, 'https://foo.bar/product/rest/of/url')

    def test_set_params(self):
        class Foo:
            pass

        foo = Foo()

        set_params(foo, [
                 {'isAdded': True,
                  'name': 'id',
                  'value': '8614787'},
                 {'isAdded': True,
                  'name': 'positionType',
                  'value': 'PRODUCT'},
                 {'isAdded': True,
                  'name': 'size',
                  'value': 100},
                 {'isAdded': True,
                  'name': 'price',
                  'value': 73.0},
                 {'isAdded': True,
                  'name': 'value',
                  'value': 7300.0},
            ])
        
        self.assertEquals(foo.id, '8614787')
        self.assertEquals(foo.positionType, 'PRODUCT')
        self.assertEquals(foo.size, 100)
        self.assertEquals(foo.price, 73.0)
        self.assertEquals(foo.value, 7300.0)


class TestDegiroAsyncAPIHelpers(unittest.TestCase):
    def test_convert_time_series(self):
        data = {
            "times": "2022-01-20T00:00:00/PT1M",
            "expires": "2022-01-20T10:12:56+01:00",
            "data": [
                [
                    540,
                    114.0
                ],
                [
                    541,
                    114.08
                ],
                [
                    542,
                    114.12
                ]
            ]
        }
        data_out = convert_time_series(data)
        self.maxDiff = None
        self.assertEquals(data_out,
            {

                "type": "time",
                "times": "2022-01-20T00:00:00",
                "resolution": "PT1M",
                "expires": "2022-01-20T10:12:56+01:00",
                "data": {
                    'price': [114.0, 114.08, 114.12],
                    'date': [
                        '2022-01-20T09:00:00',
                        '2022-01-20T09:01:00',
                        '2022-01-20T09:02:00']
                }
            })


#####################
# Integration tests #
#####################
if RUN_INTEGRATION_TESTS:
    LOGGER.info('degiroasync.api integration tests will run.')
    class TestDegiroAPI(unittest.IsolatedAsyncioTestCase):
        async def _login(self, credentials : Credentials):
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

        async def test_get_portfolio_total(self):
            session = await self._login(_get_credentials())
            total, products = await degiroasync.api.get_portfolio(session)
            LOGGER.debug("test_get_portfolio_total: %s", total.__dict__)
            self.assertIsNotNone(total.degiroCash)
            self.assertIsNotNone(total.totalCash)
            self.assertIsNotNone(total.freeSpaceNew)
            self.assertIsNotNone(total.reportPortfValue)
            self.assertIsNotNone(total.reportCashBal)
            await asyncio.gather(*[p.await_product_info() for p in products])

        async def test_get_portfolio_products_info(self):
            session = await self._login(_get_credentials())
            _, products = await degiroasync.api.get_portfolio(session)
            LOGGER.debug("test_get_portfolio_products_info: %s",
                    pprint.pformat(tuple(p.__dict__ for p in products)))

            for product in products:
                self.assertIsNotNone(product.id)
                await product.await_product_info()
                self.assertIsInstance(product.name, str, f"{product.id}")
                self.assertIsInstance(product.isin, str, f"{product.id}:{product.name}")
                try:
                    # Note: vwdId looks to be only available for
                    # productType == 'STOCK'
                    product.vwdId
                except AttributeError as exc:
                    LOGGER.info("test_get_portfolio_products_info|"
                            "vwdId not found for product %s:%s:%s",
                            product.id, product.name, product.isin)

            LOGGER.debug("test_get_portfolio_products_info2: %s",
                    pprint.pformat(tuple(p.__dict__ for p in products)))

        async def test_get_price_data_bulk(self):
            raise NotImplementedError
            session = await self._login(_get_credentials())
            #degiroasync.api.Product
            _, products = await degiroasync.api.get_portfolio(session)
            # In a context where we'd want to optimize, we want to 
            # build the pipeline by awaiting on each product instead of a bulk
            # gather to not block execution while we wait for data on some
            # of the products.
            await asyncio.gather(await p.await_product_info() for p in products)
            products = filter(lambda p: p.info.productType == ProductConst.Type.STOCKS, products)
            price_data = degiroasync.api.get_price_data_bulk(session, products)

        async def test_get_price_data_bulk(self):
            raise NotImplementedError
            session = await self._login(_get_credentials())
            #degiroasync.api.Product
            _, products = await degiroasync.api.get_portfolio(session)
            # In a context where we'd want to optimize, we want to 
            # build the pipeline by awaiting on each product instead of a bulk
            # gather to not block execution while we wait for data on some
            # of the products.
            await asyncio.gather(await p.await_product_info() for p in products)
            products = filter(lambda p: p.info.productType == ProductConst.Type.STOCKS, products)
            price_data = degiroasync.api.get_price_data_bulk(session, products)


if __name__ == '__main__':
    import nose2
    nose2.main()

