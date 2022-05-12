import unittest
import itertools
import logging
import os
import pprint
import asyncio
import unittest.mock
import sys
import datetime
from unittest.mock import MagicMock


import degiroasync
import degiroasync.webapi
import degiroasync.api
import degiroasync.core
import degiroasync.core.helpers
from degiroasync.core import join_url
from degiroasync.core import SessionCore
from degiroasync.core.helpers import set_params
from degiroasync.core.helpers import camelcase_to_snake
from degiroasync.core.helpers import camelcase_dict_to_snake
from degiroasync.webapi import get_config
from degiroasync.webapi import get_client_info
from degiroasync.webapi import get_products_info
from degiroasync.webapi import get_company_profile
from degiroasync.webapi import get_news_by_company
from degiroasync.api.product import convert_time_series
from degiroasync.api import ProductBase
from degiroasync.api import ProductFactory
from degiroasync.api import Stock
from degiroasync.api import Currency
from degiroasync.api import Order
from degiroasync.api import ORDER
from degiroasync.api import Exchange
from degiroasync.core.constants import PRODUCT
from degiroasync.core.constants import PRICE

from .test_degirowebapi import _get_credentials


LOGGER = logging.getLogger(degiroasync.core.LOGGER_NAME)
LOGGER.setLevel(logging.DEBUG)
#degiroasync.core.helpers.set_logs(LOGGER, logging.DEBUG)

LOGGER.debug('Python Version: %s', sys.version)

RUN_INTEGRATION_TESTS = 0
try:
    _env_var = os.environ.get('DEGIROASYNC_INTEGRATION')
    RUN_INTEGRATION_TESTS = int(_env_var)
except ValueError:
    LOGGER.info('degiroasync integration tests will *not* run.')
del _env_var


#############
# Unittests #
#############


class TestDegiroAsyncOrders(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.get_orders_mock = MagicMock()
        self._orders_dummy = {
                'orders': [
                        {
                            'created': '2022-02-23 09:00:00 CET',
                            'orderId': 'weiurpoiwejaklsj',
                            'productId': '123123',
                            'size': 50,
                            'price': 100.2,
                            'buysell': 'B',
                            'orderTypeId': 1,
                            'orderTimeTypeId': 1,
                            'currentTradedSize': 10,
                            'totalTradedSize': 10,
                            'type': 'CREATED',
                            'isActive': True,
                            'status': 'CONFIRMED',
                        }
                    ]
            }
        self.get_orders_history_mock = MagicMock()
        self._orders_history_dummy = {
                'data': [
                        {
                            'created': '2022-02-23 09:00:00 CET',
                            'orderId': 'weiurpoiwejaklsj',
                            'productId': '123123',
                            'size': 50,
                            'price': 100.2,
                            'buysell': 'B',
                            'orderTypeId': 1,
                            'orderTimeTypeId': 1,
                            'currentTradedSize': 50,
                            'totalTradedSize': 50,
                            'type': 'CREATED',
                            'isActive': True,
                            'status': 'CONFIRMED',
                        }
                    ]
            }

    @unittest.mock.patch('degiroasync.webapi.get_orders_history')
    @unittest.mock.patch('degiroasync.webapi.get_orders')
    async def test_get_orders(self,
                              get_orders_m,
                              get_orders_history_m):
        get_orders_m.return_value = self._orders_dummy
        get_orders_history_m.return_value = self._orders_history_dummy
        orders, orders_h = await degiroasync.api.get_orders(MagicMock())

        self.assertEqual(len(orders), 1)
        self.assertEqual(len(orders_h), 1)
        order = orders[0]
        orderh = orders_h[0]

        for o in (order, orderh):
            self.assertEqual(order.order_id, 'weiurpoiwejaklsj')
            self.assertEqual(order.size, 50)
            self.assertEqual(order.buysell, ORDER.ACTION.BUY)


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
        self.assertEqual(
                data_out,
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


class TestExchangeDictionary(unittest.IsolatedAsyncioTestCase):
    "Unittest for api.ExchangeDictionary"
    def setUp(self):
        resp_mock = unittest.mock.MagicMock()
        #resp_mock.json = unittest.mock.MagicMock()
        #resp_mock.return_value = {
        self._product_dictionary_dummy = {
                "regions": [
                    {
                        "id": 1,
                        "name": "Europe",
                        "translation": "translation.label.117"
                    },
                    {
                        "id": 2,
                        "name": "America",
                        "translation": "translation.label.118"
                    },
                    {
                        "id": 3,
                        "name": "Other",
                        "translation": "translation.label.121"
                    }
                ],
                'countries': [
                    {
                       "id": 978,
                       "name": "NL",
                       "region": 1,
                       "translation": "list.country.978"
                    },
                    {
                        "id": 886,
                        "name": "FR",
                        "region": 1,
                        "translation": "list.country.886"
                    },

                    ],
                'exchanges': [
                    {
                        'id': 710, 'code': 'XPAR', 'hiqAbbr': 'EPA',
                        'country': 'FR', 'city': 'Paris', 'micCode': 'XPAR',
                        'name': 'Euronext Paris'},
                    {
                        'id': 200, 'code': 'XAMS', 'hiqAbbr': 'EAM',
                        'country': 'NL', 'city': 'Amsterdam',
                        'micCode': 'XAMS', 'name': 'Euronext Amsterdam'}
                    ]
            }
        self.get_product_dictionary_mock = resp_mock

    @unittest.mock.patch('degiroasync.webapi.get_product_dictionary')
    async def test_exchange_dictionary_attributes(self, get_dict_mock):
        # Mock webapi.get_product_dictionary
        get_dict_mock.return_value = self._product_dictionary_dummy
        session = object()  # dummy is enough, we mocked the class
        dictionary = await degiroasync.api.ExchangeDictionary(session)

        regions = dictionary.regions
        self.assertIn('Europe', (r.name for r in regions))
        countries = dictionary.countries
        self.assertIn('NL', (c.name for c in countries))
        exchanges = dictionary.exchanges
        self.assertIn('XAMS', (e.mic_code for e in exchanges))

    @unittest.mock.patch('degiroasync.webapi.get_product_dictionary')
    async def test_exchange_dictionary_exchange(self, get_dict_mock):
        # Mock webapi.get_product_dictionary
        get_dict_mock.return_value = self._product_dictionary_dummy
        session = object()  # dummy is enough, we mocked the class
        dictionary = await degiroasync.api.ExchangeDictionary(session)

        eam_exc = dictionary.exchange_by(hiq_abbr='EAM')
        self.assertEqual(eam_exc.mic_code, 'XAMS')
        self.assertEqual(eam_exc.country_name, 'NL')

    @unittest.mock.patch('degiroasync.webapi.get_product_dictionary')
    async def test_exchange_dictionary_country(self, get_dict_mock):
        # Mock webapi.get_product_dictionary
        get_dict_mock.return_value = self._product_dictionary_dummy
        session = object()  # dummy is enough, we mocked the class
        dictionary = await degiroasync.api.ExchangeDictionary(session)

        country = dictionary.country_by(name='FR')
        self.assertEqual(country.region.name, 'Europe')

        country = dictionary.country_by(name='NL')
        self.assertEqual(country.region.name, 'Europe')


class TestProduct(unittest.IsolatedAsyncioTestCase):
    """
    Local tests for Product.
    """
    @unittest.mock.patch('degiroasync.api.ExchangeDictionary.exchange_by')
    @unittest.mock.patch('degiroasync.webapi.get_products_info')
    async def test_product(self, wapi_prodinfo_m, exchange_by_m):
        wapi_prodinfo_m.return_value = {'data': {
                '123': {
                    'id': '123',
                    'product_type_id': 99,
                    'name': 'foo',
                    'symbol': 'FOO',
                    'currency': 'EUR',
                    'exchangeId': 'exid',
                    'tradable': True,
                    'isin': 'isinexample',
                }
            }
        }
        exchange_by_m.return_value = Exchange(dict(
            id='idex',
            name='EuroNext',
            country_name='France',
            hiq_abbr='EPA'
            )
        )

        session = MagicMock()  # Don't care

        # Test that degiroasync.api returns properly initiated products
        products_gen = ProductFactory.init_batch(
                session,
                (
                    {
                        'id': '123',
                        'additional': 123,
                    },
                ))
        products = [p async for p in products_gen]
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].base.id, '123')
        self.assertEqual(products[0].info.name, 'foo')
        self.assertEqual(products[0].info.symbol, 'FOO')

    @unittest.mock.patch('degiroasync.webapi.get_products_info')
    async def test_product_no_batch(self, wapi_prodinfo_m):
        # Same as test_product but with size=1 to test corner case.
        # Mock get_products_info
        #resp = MagicMock()
        #resp.json = MagicMock(return_value={'data': {
        #    '123': {
        #        'id': '123',
        #        'product_type_id': 'UNKNOWNPRODUCTID',
        #        'name': 'foo',
        #        'symbol': 'FOO',
        #        'currency': 'EUR',
        #        'exchangeId': 'exid',
        #        'tradable': True,
        #        'isin': 'isinexample',
        #    }
        #    }})
        wapi_prodinfo_m.return_value = {'data': {
                '123': {
                    'id': '123',
                    'product_type_id': 99,
                    'name': 'foo',
                    'symbol': 'FOO',
                    'currency': 'EUR',
                    'exchangeId': 'exid',
                    'tradable': True,
                    'isin': 'isinexample',
                }
            }
        }

        # Test that degiroasync.api returns properly initiated products
        products_gen = ProductFactory.init_batch(
                MagicMock(),  # Don't care about session here
                [
                    {
                        'id': '123',
                        'additional': 123,
                    },
                ],
                size=1)
        products = [p async for p in products_gen]
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].base.id, '123')
        self.assertEqual(products[0].base.additional, 123)
        self.assertEqual(products[0].info.name, 'foo')
        self.assertEqual(products[0].info.symbol, 'FOO')


#####################
# Integration tests #
#####################
if RUN_INTEGRATION_TESTS:
    LOGGER.info('degiroasync.api integration tests will run.')

    class _IntegrationLogin:
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
                    self.session = await degiroasync.api.login(credentials)
            return self.session

    class TestDegiroasyncIntegrationLogin(
            _IntegrationLogin,
            unittest.IsolatedAsyncioTestCase):
        async def test_login(self):
            credentials = _get_credentials()
            session = await degiroasync.api.login(credentials)
            self.assertIsNotNone(session.config)
            self.assertIsNotNone(session.client)

    class TestDegiroasyncIntegrationPortfolio(
            _IntegrationLogin,
            unittest.IsolatedAsyncioTestCase):
        async def test_get_portfolio_total(self):
            session = await self._login()
            total = await degiroasync.api.get_portfolio_total(session)
            LOGGER.debug("test_get_portfolio_total: %s", total.__dict__)
            self.assertIsNotNone(total.degiro_cash)
            self.assertIsNotNone(total.total_cash)
            self.assertIsNotNone(total.free_space_new)
            self.assertIsNotNone(total.report_portf_value)
            self.assertIsNotNone(total.report_cash_bal)

        async def test_get_portfolio_products_info(self):
            session = await self._login()
            positions = await degiroasync.api.get_portfolio(session)
            LOGGER.debug("test_get_portfolio_products_info: %s",
                         pprint.pformat(tuple(p.__dict__ for p in positions)))

            self.assertGreaterEqual(
                    len(positions), 1,
                    "If there is no product in portfolio, this is expected to "
                    "fail. Otherwise: this is an issue to be fixed.")
            for pos in positions:
                product = pos.product
                self.assertIsNotNone(product.base.id)
                LOGGER.debug("test_get_portfolio_products_info2: %s",
                             pprint.pformat(product.info))
                self.assertNotEqual(product.info, None)
                self.assertIsInstance(product.info.name, str,
                                      f"{product.base.id}")
                self.assertIsInstance(product.info.isin, str,
                                      f"{product.base.id}:{product.info.name}")

    class TestDegiroasyncIntegrationPrice(
            _IntegrationLogin,
            unittest.IsolatedAsyncioTestCase):

        async def test_get_price_data(self):
            session = await self._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_isin='NL0000235190',
                    product_type_id=PRODUCT.TYPEID.STOCK
                    )
            #products_awaitable = [p.await_product_info() for p in products]
            #LOGGER.debug('test_get_price_data products_awaitable| %s', products_awaitable)

            # In a context where we'd want to optimize, we want to
            # build the pipeline by awaiting on each product instead of a bulk
            # gather to not block execution while we wait for data on some
            # of the products.
            #await asyncio.gather(*[p.await_product_info() for p in products])
            #products = [p async for p in products_gen]
            self.assertGreaterEqual(len(products), 1, products)

            LOGGER.debug('test_get_price_data products| %s',
                         tuple(p.__dict__ for p in products))

            products = filter(
                    lambda p: (
                        p.info.product_type == PRODUCT.TYPE.STOCK
                        and p.info.tradable is True
                        and p.info.symbol == 'AIR'
                        ),
                    products)
            products = list(products)
            LOGGER.debug('test_get_price_data products filtered| %s',
                         pprint.pformat(tuple(p.__dict__ for p in products)))

            self.assertGreaterEqual(len(products), 1)
            # Select product
            for product in products:
                if product.base.product_type_id == PRODUCT.TYPEID.STOCK:
                    # Let's take the first stock as example
                    break

            LOGGER.debug('test_get_price_data price_data 1| %s',
                         product.__dict__)
            price_data = await degiroasync.api.get_price_data(session, product)
            LOGGER.debug('test_get_price_data price_data 2| %s',
                         price_data)
            self.assertGreaterEqual(len(price_data.price), 1)
            self.assertGreaterEqual(len(price_data.date), 1)

        async def test_get_price_data_symbol_exchange(self):
            # First get product
            session = await self._login()
            symbol = 'FGR'
            exchange = 'EPA'
            products = await degiroasync.api.search_product(
                    session,
                    by_symbol=symbol,
                    by_exchange=exchange,
                    product_type_id=PRODUCT.TYPEID.STOCK)
            self.assertEqual(len(products), 1)
            product = products[0]
            self.assertEqual(symbol, product.info.symbol, product.info)

            price_data = await degiroasync.api.get_price_data(session, product)
            LOGGER.debug("test_get_price_data| %s", price_data.price)
            LOGGER.debug("test_get_price_data| %s", price_data.date)
            self.assertGreaterEqual(len(price_data.price), 1)
            self.assertGreaterEqual(len(price_data.date), 1)

            date = price_data.date
            price = price_data.price
            self.assertEqual(len(date), len(price))

        async def test_get_price_data_day_resolution(self):
            session = await self._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_isin='NL0000235190',
                    by_exchange='EPA',
                    product_type_id=PRODUCT.TYPEID.STOCK
                    )
            LOGGER.debug('test_get_price_data_day_resolution| products %s',
                         pprint.pformat([p.__dict__ for p in products]))
            #LOGGER.debug('test_get_price_data products_awaitable| %s', products_awaitable)

            # In a context where we'd want to optimize, we want to
            # build the pipeline by awaiting on each product instead of a bulk
            # gather to not block execution while we wait for data on some
            # of the products.
            #await asyncio.gather(*[p.await_product_info() for p in products])
            #products = [p async for p in products_gen]
            self.assertEqual(len(products), 1)
            product = products[0]

            LOGGER.debug('test_get_price_data_day_resolution| product %s',
                         pprint.pformat(product.__dict__))

            self.assertEqual(product.info.product_type_id,
                             PRODUCT.TYPEID.STOCK)

            price_data = await degiroasync.api.get_price_data(
                    session,
                    product,
                    resolution=PRICE.RESOLUTION.PT1D,
                    period=PRICE.PERIOD.P1MONTH,
                    )
            LOGGER.debug('test_get_price_data_day_resolution| price_data %s',
                         price_data)
            self.assertGreaterEqual(len(price_data.price), 1)
            self.assertGreaterEqual(len(price_data.date), 1)
            date_series = price_data.date
            price_series = price_data.price
            self.assertEqual(len(date_series), len(price_series))
            LOGGER.debug("test_get_price_data_day_resolution| "
                         "date_series len %s", len(date_series))
            self.assertGreaterEqual(
                    len(date_series), 15,
                    "We should have daily data for a month with one sample "
                    "per day.")

            # We entered PT1D resolution, check that we have one data point
            # per day at most
            start = datetime.datetime.now() - datetime.timedelta(days=32)
            prior_day = datetime.datetime(start.year, start.month, start.day)
            for date_str in date_series:
                date = datetime.datetime.fromisoformat(date_str)
                day = datetime.datetime(date.year, date.month, date.day)
                delta_days = (day - prior_day).days
                self.assertGreaterEqual(
                        delta_days, 1,
                        "day {}, prior_day {}".format(
                            day.isoformat(),
                            prior_day.isoformat()
                            ))

                prior_day = day


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

    class TestDegiroasyncIntegrationSearch(
            _IntegrationLogin,
            unittest.IsolatedAsyncioTestCase):
        async def test_search_product_isin(self):
            session = await self._login()
            isin = 'NL0000235190'  # Airbus ISIN
            products = await degiroasync.api.search_product(session,
                    by_isin=isin)
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                # We should only have airbus products here
                self.assertTrue('airbus' in product.info.name.lower())

        async def test_search_product_symbol(self):
            session = await self._login()
            symbol = 'AIR'
            products = await degiroasync.api.search_product(session,
                                                            by_symbol=symbol)
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                self.assertEqual(symbol, product.info.symbol, product.info)
                # We should only have airbus products here
                #self.assertTrue('airbus' in product.info.name.lower(),
                #               product.info)

        async def test_search_product_symbol_gne(self):
            session = await self._login()
            symbol = 'GNE'  # GE symbol on EPA
            products = await degiroasync.api.search_product(session,
                                                            by_symbol=symbol,
                                                            by_exchange='EPA')
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                # We should only have airbus products here
                self.assertTrue(
                        'general electric' in product.info.name.lower())

        async def test_search_product_text(self):
            session = await self._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_text='airbus')
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                # We should only have airbus products here
                self.assertTrue('airbus' in product.info.name.lower())

        async def test_search_product_symbol_exchange(self):
            session = await self._login()
            symbol = 'AIR'  # Airbus symbol
            exchange_hiq = 'EPA'
            products = await degiroasync.api.search_product(
                    session,
                    by_symbol=symbol,
                    by_exchange=exchange_hiq)
            # The point of implementing filtering on symbol and exchange
            # is to target one specific product. Raise an error if it doesn't
            # work.
            self.assertEqual(len(products), 1)
            for product in products:
                # We should only have airbus products here
                self.assertTrue('airbus' in product.info.name.lower())

    class TestDegiroasyncIntegrationExchangeDictionary(
            _IntegrationLogin,
            unittest.IsolatedAsyncioTestCase):
        async def test_product_dictionary_attributes(self):
            session = await self._login()
            dictionary = await degiroasync.api.ExchangeDictionary(session)

            regions = dictionary.regions
            self.assertIn('Europe', (r.name for r in regions))
            countries = dictionary.countries
            self.assertIn('NL', (c.name for c in countries))
            exchanges = dictionary.exchanges
            self.assertIn('XAMS', (e.mic_code for e in exchanges))

        async def test_product_dictionary_exchange_by(self):
            session = await self._login()
            dictionary = await degiroasync.api.ExchangeDictionary(session)
            eam_exc = dictionary.exchange_by(hiq_abbr='EAM')
            self.assertEqual(eam_exc.mic_code, 'XAMS')
            self.assertEqual(eam_exc.country_name, 'NL')

    class TestDegiroasyncIntegrationOrders(
            _IntegrationLogin,
            unittest.IsolatedAsyncioTestCase):
        async def test_get_orders(self):
            session = await self._login()
            orders, orders_hist = await degiroasync.api.get_orders(session)
            LOGGER.debug("test_get_orders orders| %s", orders)
            LOGGER.debug("test_get_orders orders hist| %s", orders_hist)
            for o in itertools.chain(orders, orders_hist):
                self.assertTrue(isinstance(o, Order))

        async def test_get_transactions(self):
            session = await self._login()
            to_date = datetime.datetime.today()
            from_date = datetime.datetime(year=to_date.year - 2,
                                          month=1,
                                          day=1)
            LOGGER.debug("test_get_transactions params| %s",
                         (from_date, to_date))
            transactions = await degiroasync.api.get_transactions(
                    session,
                    from_date=from_date,
                    to_date=to_date
                    )
            LOGGER.debug("test_get_transactions results| %s", transactions)
            self.assertGreaterEqual(
                    len(transactions), 1,
                    "No transaction found in the last 2 years. "
                    "It's possible the account had no activity."
                    )

            for trans in transactions:
                self.assertTrue(hasattr(trans, 'product'))
                self.assertTrue(hasattr(trans, 'price'))
                self.assertTrue(hasattr(trans, 'quantity'))
                self.assertTrue(hasattr(trans, 'fx_rate'))

        async def test_check_orders(self):
            session = await self._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_symbol='AIR',
                    by_exchange='EPA',
                    product_type_id=PRODUCT.TYPEID.STOCK
            )
            self.assertEqual(len(products), 1)

            product = products[0]
            order_check = await degiroasync.api.check_order(
                    session,
                    product=product,
                    buy_sell=ORDER.ACTION.BUY,
                    time_type=ORDER.TIME.DAY,
                    order_type=ORDER.TYPE.LIMITED,
                    size=1,
                    price=80
            )
            self.assertIn('confirmation_id', order_check)
