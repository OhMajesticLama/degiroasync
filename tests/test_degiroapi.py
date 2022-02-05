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
from degiroasync.api import ProductBase
from degiroasync.api import Stock
from degiroasync.api import Currency
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
        async def asyncSetUp(self):
            self._lock = asyncio.Lock()

        async def _login(self):
            async with self._lock:
                if not hasattr(self, 'session'):
                    credentials = _get_credentials()
                    self.session = await degiroasync.api.login(credentials)
            return self.session

        async def test_login(self):
            credentials = _get_credentials()
            session = await degiroasync.api.login(credentials) 
            self.assertIsNotNone(session.config)
            self.assertIsNotNone(session.client)

        async def test_get_portfolio_total(self):
            session = await self._login()
            total, products = await degiroasync.api.get_portfolio(session)
            LOGGER.debug("test_get_portfolio_total: %s", total.__dict__)
            self.assertIsNotNone(total.degiroCash)
            self.assertIsNotNone(total.totalCash)
            self.assertIsNotNone(total.freeSpaceNew)
            self.assertIsNotNone(total.reportPortfValue)
            self.assertIsNotNone(total.reportCashBal)
            await asyncio.gather(*[p.await_product_info() for p in products])

        async def test_get_portfolio_products_info(self):
            session = await self._login()
            _, products = await degiroasync.api.get_portfolio(session)
            LOGGER.debug("test_get_portfolio_products_info: %s",
                    pprint.pformat(tuple(p.__dict__ for p in products)))

            for product in products:
                self.assertIsNotNone(product.base.id)
                await product.await_product_info()
                LOGGER.debug("test_get_portfolio_products_info2: %s",
                        pprint.pformat(product.info))
                self.assertNotEqual(product.info, None)
                self.assertIsInstance(product.info.name, str, f"{product.base.id}")
                self.assertIsInstance(product.info.isin, str, f"{product.base.id}:{product.info.name}")

        async def test_get_price_data(self):
            session = await self._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_isin='NL0000235190'
                    )
            #products_awaitable = [p.await_product_info() for p in products]
            #LOGGER.debug('test_get_price_data products_awaitable| %s', products_awaitable)

            # In a context where we'd want to optimize, we want to 
            # build the pipeline by awaiting on each product instead of a bulk
            # gather to not block execution while we wait for data on some
            # of the products.
            await asyncio.gather(*[p.await_product_info() for p in products])
            self.assertGreaterEqual(len(products), 1)

            LOGGER.debug('test_get_price_data products| %s', tuple(p.__dict__ for p in products))

            products = filter(
                    lambda p: (
                        p.info.productType == ProductConst.Type.STOCK
                        and p.info.tradable == True
                        and p.info.symbol == 'AIR'
                        ),
                    products)
            products = list(products)
            LOGGER.debug('test_get_price_data products filtered| %s',
                    pprint.pformat(tuple(p.__dict__ for p in products)))

            self.assertGreaterEqual(len(products), 1)
            # Select product
            for product in products:
                if product.base.productTypeId == ProductConst.TypeId.STOCK:
                    # Let's take the first stock as example
                    break

            LOGGER.debug('test_get_price_data price_data 1| %s', product.__dict__)
            price_data = await degiroasync.api.get_price_data(session, product)
            LOGGER.debug('test_get_price_data price_data 2| %s', price_data)

        #async def test_get_price_data_bulk(self):
        #    raise NotImplementedError
        #    session = await self._login()
        #    #degiroasync.api.Product
        #    _, products = await degiroasync.api.get_portfolio(session)
        #    # In a context where we'd want to optimize, we want to 
        #    # build the pipeline by awaiting on each product instead of a bulk
        #    # gather to not block execution while we wait for data on some
        #    # of the products.
        #    await asyncio.gather(await p.await_product_info() for p in products)
        #    products = filter(lambda p: p.info.productType == ProductConst.Type.STOCKS, products)
        #    price_data = await degiroasync.api.get_price_data_bulk(session, products)

        async def test_search_product_isin(self):
            session = await self._login()
            isin = 'NL0000235190'  # Airbus ISIN
            products = await degiroasync.api.search_product(session,
                    by_isin=isin)
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                await product.await_product_info()
                # We should only have airbus products here
                self.assertTrue('airbus' in product.info.name.lower())

        async def test_search_product_symbol(self):
            session = await self._login()
            symbol = 'AIR'  # Airbus symbol
            products = await degiroasync.api.search_product(session,
                    by_symbol=symbol)
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                await product.await_product_info()
                # We should only have airbus products here
                self.assertTrue('airbus' in product.info.name.lower())

        async def test_search_product_text(self):
            session = await self._login()
            products = await degiroasync.api.search_product(session,
                    by_text='airbus')
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                await product.await_product_info()
                # We should only have airbus products here
                self.assertTrue('airbus' in product.info.name.lower())

if __name__ == '__main__':
    import nose2
    nose2.main()

