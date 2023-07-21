import unittest
import itertools
import logging
import os
import pprint
import unittest.mock
import sys
import datetime
from unittest.mock import MagicMock
from typing import Sequence


import degiroasync
import degiroasync.webapi
import degiroasync.api
import degiroasync.webapi
import degiroasync.core
import degiroasync.core.helpers
from degiroasync.core import Credentials
from degiroasync.api import ProductFactory
from degiroasync.api import Order
from degiroasync.api import ORDER
from degiroasync.api import Exchange
from degiroasync.api import Index
from degiroasync.core.constants import PRODUCT
from degiroasync.core.constants import PRICE
from degiroasync.core import BadCredentialsError
from degiroasync.core import camelcase_dict_to_snake

from tests.integration_login import _get_credentials
from tests.integration_login import _IntegrationLogin


LOGGER = logging.getLogger(degiroasync.core.LOGGER_NAME)
LOGGER.setLevel(logging.DEBUG)

LOGGER.debug('Python Version: %s', sys.version)

RUN_INTEGRATION_TESTS = 0
try:
    _env_var = os.environ.get('DEGIROASYNC_INTEGRATION')
    RUN_INTEGRATION_TESTS = int(_env_var)
except (ValueError, TypeError):
    LOGGER.info('degiroasync integration tests will *not* run.')
del _env_var


#############
# Unittests #
#############

class TestDegiroAsyncLogin(unittest.IsolatedAsyncioTestCase):
    @unittest.mock.patch('degiroasync.webapi.get_client_info')
    @unittest.mock.patch('degiroasync.webapi.get_config')
    @unittest.mock.patch('degiroasync.webapi.login')
    async def test_bad_credentials(
            self,
            login_m: MagicMock,
            get_config_m: MagicMock,
            *stubs: Sequence[MagicMock]
            ):
        """
        Verify that BadCredentialsError is raised in case of bad credentials
        and that default behavior does not try to log in again with previously
        failed credentials.
        """
        login_m.side_effect = BadCredentialsError()
        # This should never be called as we're supposed to raise an exception
        # before. Raise exception in case we make it to get_config.
        get_config_m.side_effect = RuntimeError("This should not happen.")

        credentials = Credentials(
            username='dummyaccount123456',
            password='dummydummy'
                )
        with self.assertRaises(BadCredentialsError):
            await degiroasync.api.login(credentials)
        # There should be exactly one call made to webapi.login
        login_m.assert_called_once()

        # Attempt a second login with same credentials.
        credentials = Credentials(
            username='dummyaccount123456',
            password='dummydummy'
                )
        # BadCredentialsError should still be raised.
        with self.assertRaises(BadCredentialsError):
            await degiroasync.api.login(credentials)

        # There should be no new call to webapi.login.
        login_m.assert_called_once()


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


#class TestDegiroAsyncAPIHelpers(unittest.TestCase):
#    def test_convert_time_series(self):
#        data = {
#            "times": "2022-01-20T00:00:00/PT1M",
#            "expires": "2022-01-20T10:12:56+01:00",
#            "data": [
#                [
#                    540,
#                    114.0
#                ],
#                [
#                    541,
#                    114.08
#                ],
#                [
#                    542,
#                    114.12
#                ]
#            ]
#        }
#        data_out = convert_time_series(data)
#        self.maxDiff = None
#        self.assertEqual(
#                data_out,
#                {
#
#                    "type": "time",
#                    "times": "2022-01-20T00:00:00",
#                    "resolution": "PT1M",
#                    "expires": "2022-01-20T10:12:56+01:00",
#                    "data": {
#                        'price': [114.0, 114.08, 114.12],
#                        'date': [
#                            '2022-01-20T09:00:00',
#                            '2022-01-20T09:01:00',
#                            '2022-01-20T09:02:00']
#                    }
#                })


class TestExchangeDictionary(unittest.IsolatedAsyncioTestCase):
    "Unittest for api.ExchangeDictionary"
    def setUp(self):
        resp_mock = unittest.mock.MagicMock()
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
                    ],
                'indices': [{'id': '106002', 'name': 'SDAX'},
                            {'id': '106001', 'name': 'MDAX'},
                            {'id': '5',
                             'name': 'CAC 40',
                             'productId': 4824940},
                            {'id': '121003',
                             'name': 'SMIM',
                             'productId': 11875105},
                            {'id': 114003, 'name': 'ISEQ Overall'},
                            {'id': 121002, 'name': 'SLI',
                             'productId': 11875104}],
            }
        self.get_product_dictionary_mock = resp_mock

    @unittest.mock.patch('degiroasync.webapi.get_product_dictionary')
    async def test_dictionary_attributes(self, get_dict_mock):
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
    async def test_dictionary_exchange(self, get_dict_mock):
        # Mock webapi.get_product_dictionary
        get_dict_mock.return_value = self._product_dictionary_dummy
        session = object()  # dummy is enough, we mocked the class
        dictionary = await degiroasync.api.ExchangeDictionary(session)

        eam_exc = dictionary.exchange_by(hiq_abbr='EAM')
        self.assertEqual(eam_exc.mic_code, 'XAMS')
        self.assertEqual(eam_exc.country_name, 'NL')

    @unittest.mock.patch('degiroasync.webapi.get_product_dictionary')
    async def test_dictionary_country(self, get_dict_mock):
        # Mock webapi.get_product_dictionary
        get_dict_mock.return_value = self._product_dictionary_dummy
        session = object()  # dummy is enough, we mocked the class
        dictionary = await degiroasync.api.ExchangeDictionary(session)

        country = dictionary.country_by(name='FR')
        self.assertEqual(country.region.name, 'Europe')

        country = dictionary.country_by(name='NL')
        self.assertEqual(country.region.name, 'Europe')

    @unittest.mock.patch('degiroasync.webapi.get_product_dictionary')
    async def test_dictionary_index(self, get_dict_mock):
        # Mock webapi.get_product_dictionary
        get_dict_mock.return_value = self._product_dictionary_dummy
        session = object()  # dummy is enough, we mocked the class
        dictionary = await degiroasync.api.ExchangeDictionary(session)

        index = dictionary.index_by(name='CAC 40')
        self.assertEqual(index.name, 'CAC 40')
        index = dictionary.index_by(id='5')
        self.assertEqual(index.name, 'CAC 40')

    @unittest.mock.patch('degiroasync.webapi.get_products_info')
    async def test_dictionary_index_info(
            self,
            get_products_info_mock):
        # Mock webapi.get_product_dictionary
        get_products_info_mock.return_value = {
              "data": {
                "4824940": {
                  "id": "4824940",
                  "name": "CAC 40",
                  "isin": "FR0003500008",
                  "symbol": "CAC INDEX",
                  "contractSize": 1,
                  "productType": "INDEX",
                  "productTypeId": 180,
                  "tradable": False,
                  "category": "H",
                  "currency": "EUR",
                  "active": True,
                  "exchangeId": "710",
                  "onlyEodPrices": False,
                  "orderTimeTypes": [],
                  "buyOrderTypes": [],
                  "sellOrderTypes": [],
                  "productBitTypes": [],
                  "closePrice": 7384.91,
                  "closePriceDate": "2023-07-20",
                  "feedQuality": "R",
                  "orderBookDepth": 0,
                  "vwdIdentifierType": "issueid",
                  "vwdId": "360015511",
                  "qualitySwitchable": False,
                  "qualitySwitchFree": False,
                  "vwdModuleId": 1
                }
              }
            }

        session = MagicMock()  # dummy is enough, the call is mocked
        session.dictionary = MagicMock()
        session.dictionary.exchange_by = MagicMock(
                return_value=Exchange(dict(
                    id='id',
                    name='name',
                    country_name='COUNTRYCODE',
                    hiq_abbr='TDG'
                    ))
                )
        data = self._product_dictionary_dummy['indices'][2]
        data['productId'] = str(data['productId'])
        data = camelcase_dict_to_snake(data)
        index = Index(data)

        self.assertEqual(index.name, 'CAC 40')
        await index.get_info(session)
        self.assertEqual(index.info.isin, "FR0003500008")


class TestSearchProduct(unittest.IsolatedAsyncioTestCase):
    @unittest.mock.patch('degiroasync.webapi.get_products_info')
    @unittest.mock.patch('degiroasync.webapi.search_product')
    async def test_search_by_index(
            self,
            search_product_m,
            get_products_info_m,
            ):
        get_products_info_m.return_value = {'data': {
                '123': {
                    'id': '123',
                    'productTypeId': 99,
                    'name': 'foo',
                    'symbol': 'FOO',
                    'currency': 'EUR',
                    'exchangeId': 'exid',
                    'tradable': True,
                    'isin': 'isinexample',
                }
            }
        }
        session = MagicMock()
        session.dictionary = MagicMock()
        index = MagicMock()
        index.id = '123'
        index.name = 'CAC 40'
        session.dictionary.index_by = MagicMock(return_value=index)

        search_product_m.return_value = {
            "total": 1,
            "offset": 0,
            "products": [
                {
                    "active": True,
                    "buyOrderTypes": [
                        "LIMIT",
                        "MARKET",
                        "STOPLOSS",
                        "STOPLIMIT"
                    ],
                    "category": "B",
                    "closePrice": 113.3,
                    "closePriceDate": "2022-02-02",
                    "contractSize": 1.0,
                    "currency": "EUR",
                    "exchangeId": "710",
                    "feedQuality": "R",
                    "feedQualitySecondary": "CX",
                    "id": "123",
                    "isin": "NL0000235190",
                    "name": "AIRBUS",
                    "onlyEodPrices": False,
                    "orderBookDepth": 0,
                    "orderBookDepthSecondary": 0,
                    "orderTimeTypes": [
                        "DAY",
                        "GTC"
                    ],
                    "productBitTypes": [],
                    "productType": "STOCK",
                    "productTypeId": 1,
                    "qualitySwitchFree": False,
                    "qualitySwitchFreeSecondary": False,
                    "qualitySwitchable": False,
                    "qualitySwitchableSecondary": False,
                    "sellOrderTypes": [
                        "LIMIT",
                        "MARKET",
                        "STOPLOSS",
                        "STOPLIMIT"
                    ],
                    "strikePrice": -0.0001,
                    "symbol": "AIR",
                    "tradable": True,
                    "vwdId": "360114899",
                    "vwdIdSecondary": "955000256",
                    "vwdIdentifierType": "issueid",
                    "vwdIdentifierTypeSecondary": "issueid",
                    "vwdModuleId": 1,
                    "vwdModuleIdSecondary": 2
                }
            ]
        }

        products = await degiroasync.api.search_product(
                session,
                by_index='CAC 40'
                )
        # There should be only one product returned by the mock
        self.assertGreaterEqual(len(products), 1)


class TestProduct(unittest.IsolatedAsyncioTestCase):
    """
    Local tests for Product.
    """
    @unittest.mock.patch('degiroasync.webapi.get_products_info')
    async def test_product(self, wapi_prodinfo_m):
        wapi_prodinfo_m.return_value = {'data': {
                '123': {
                    'id': '123',
                    'productTypeId': 99,
                    'name': 'foo',
                    'symbol': 'FOO',
                    'currency': 'EUR',
                    'exchangeId': 'exid',
                    'tradable': True,
                    'isin': 'isinexample',
                }
            }
        }

        session = MagicMock()  # Don't care
        session.dictionary = MagicMock()
        session.dictionary.exchange_by = MagicMock(
                return_value=Exchange(dict(
                    id='exid',
                    name='EuroNext',
                    country_name='France',
                    hiq_abbr='EPA',
                    )
                )
        )

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
        self.assertIsInstance(repr(products[0]), str)  # don't raise exception

    @unittest.mock.patch('degiroasync.webapi.get_products_info')
    async def test_product_no_batch(self, wapi_prodinfo_m):
        # Same as test_product but with size=1 to test corner case.
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
        session = MagicMock()  # Don't care
        session.dictionary = MagicMock()
        session.dictionary.exchange_by = MagicMock(
                return_value=Exchange(dict(
                    id='exid',
                    name='EuroNext',
                    country_name='France',
                    hiq_abbr='EPA',
                        )
                    )
            )

        # Test that degiroasync.api returns properly initiated products
        products_gen = ProductFactory.init_batch(
                session,  # Don't care about session here
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



class TestDegiroasyncPrice(
        unittest.IsolatedAsyncioTestCase):

    def test_priceseries_items(self):
        resp_json = {
                'requestid': '1',
                'start': '2023-06-29T00:00:00',
                'end': '2023-07-05T00:00:00',
                'resolution': 'P1D',
                'series': [
                    {
                        'times': '2023-06-29/P1D',
                        'expires': '2023-07-05T17:54:21.7030064+02:00',
                        'data': [
                            [0, 130.54, 131.64, 129.93, 130.46],
                            [1, 131.16, 132.68, 130.42, 132.36],
                            [4, 132.8, 133.7, 131.62, 132.61],
                            [5, 132.6, 132.98, 130.96, 131.32],
                            [6, 131.2, 133.5, 130.88, 132.82]],
                        'id': 'ohlc:issueid:350118230',
                        'type': 'ohlc'
                        }
                    ]
                }
        series = resp_json['series'][0]
        price_data = degiroasync.api.product.PriceSeries(
                start=datetime.datetime.fromisoformat(resp_json['start']),
                end=datetime.datetime.fromisoformat(resp_json['end']),
                resolution=PRICE.RESOLUTION(resp_json['resolution']),
                currency='EUR',
                series=series,
                )
        price_dict = dict(price_data.items())
        self.assertEqual(
                price_dict['open'],
                [130.54, 131.16, 132.8, 132.6, 131.2])
        self.assertEqual(
                price_dict['date'],
                [
                    datetime.datetime(2023, 6, 29),
                    datetime.datetime(2023, 6, 30),
                    datetime.datetime(2023, 7, 3),
                    datetime.datetime(2023, 7, 4),
                    datetime.datetime(2023, 7, 5),
                ])

    def test_priceseries_iterrows(self):
        resp_json = {
                'requestid': '1',
                'start': '2023-06-29T00:00:00',
                'end': '2023-07-05T00:00:00',
                'resolution': 'P1D',
                'series': [
                    {
                        'times': '2023-06-29/P1D',
                        'expires': '2023-07-05T17:54:21.7030064+02:00',
                        'data': [
                            [0, 130.54, 131.64, 129.93, 130.46],
                            [1, 131.16, 132.68, 130.42, 132.36],
                            [4, 132.8, 133.7, 131.62, 132.61],
                            [5, 132.6, 132.98, 130.96, 131.32],
                            [6, 131.2, 133.5, 130.88, 132.82]],
                        'id': 'ohlc:issueid:350118230',
                        'type': 'ohlc'
                        }
                    ]
                }
        series = resp_json['series'][0]
        price_data = degiroasync.api.product.PriceSeries(
                start=datetime.datetime.fromisoformat(resp_json['start']),
                end=datetime.datetime.fromisoformat(resp_json['end']),
                resolution=PRICE.RESOLUTION(resp_json['resolution']),
                currency='EUR',
                series=series,
                )

        data = series['data']
        for ind, row in enumerate(price_data.iterrows()):
            self.assertEqual(row['open'], data[ind][1])
            self.assertEqual(row['high'], data[ind][2])
            self.assertEqual(row['low'], data[ind][3])
            self.assertEqual(row['close'], data[ind][4])

        self.assertEqual(ind, 4)

    def test_priceseries_pandas(self):
        resp_json = {
                'requestid': '1',
                'start': '2023-06-29T00:00:00',
                'end': '2023-07-05T00:00:00',
                'resolution': 'P1D',
                'series': [
                    {
                        'times': '2023-06-29/P1D',
                        'expires': '2023-07-05T17:54:21.7030064+02:00',
                        'data': [
                            [0, 130.54, 131.64, 129.93, 130.46],
                            [1, 131.16, 132.68, 130.42, 132.36],
                            [4, 132.8, 133.7, 131.62, 132.61],
                            [5, 132.6, 132.98, 130.96, 131.32],
                            [6, 131.2, 133.5, 130.88, 132.82]],
                        'id': 'ohlc:issueid:350118230',
                        'type': 'ohlc'
                        }
                    ]
                }
        series = resp_json['series'][0]
        price_data = degiroasync.api.product.PriceSeries(
                start=datetime.datetime.fromisoformat(resp_json['start']),
                end=datetime.datetime.fromisoformat(resp_json['end']),
                resolution=PRICE.RESOLUTION(resp_json['resolution']),
                currency='EUR',
                series=series,
                )

        import pandas as pd
        df = pd.DataFrame(price_data.iterrows())
        self.assertEqual(df['open'][0], 130.54)
        self.assertEqual(df['open'][2], 132.8)
        self.assertEqual(df['close'][4], 132.82)

    @unittest.mock.patch('degiroasync.webapi.get_price_series')
    async def test_get_price_series_ohlc(self, price_m):
        resp_json = {
                'requestid': '1',
                'start': '2023-06-29T00:00:00',
                'end': '2023-07-05T00:00:00',
                'resolution': 'P1D',
                'series': [
                    {
                        'times': '2023-06-29/P1D',
                        'expires': '2023-07-05T17:54:21.7030064+02:00',
                        'data': [
                            [0, 130.54, 131.64, 129.93, 130.46],
                            [1, 131.16, 132.68, 130.42, 132.36],
                            [4, 132.8, 133.7, 131.62, 132.61],
                            [5, 132.6, 132.98, 130.96, 131.32],
                            [6, 131.2, 133.5, 130.88, 132.82]],
                        'id': 'ohlc:issueid:350118230',
                        'type': 'ohlc'
                        },
                    {
                        'type': 'object',
                        'data': {'currency': 'EUR'}
                    }
                    ]
                }
        price_m.return_value = resp_json
        product = MagicMock()
        product.info = MagicMock()
        product.info.product_type_id = PRODUCT.TYPEID.STOCK

        ohlc_series = await degiroasync.api.get_price_series(
                None,
                product,
                None,
                None,
                None,
                None,
                None
                )
        data = resp_json['series'][0]['data']
        for ind, row in enumerate(ohlc_series.iterrows()):
            self.assertEqual(row['open'], data[ind][1])
            self.assertEqual(row['high'], data[ind][2])
            self.assertEqual(row['low'], data[ind][3])
            self.assertEqual(row['close'], data[ind][4])


#####################
# Integration tests #
#####################
if RUN_INTEGRATION_TESTS:
    LOGGER.info('degiroasync.api integration tests will run.')

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
            session = await _IntegrationLogin._login()
            total = await degiroasync.api.get_portfolio_total(session)
            LOGGER.debug("test_get_portfolio_total: %s", total.__dict__)
            self.assertIsNotNone(total.degiro_cash)
            self.assertIsNotNone(total.total_cash)
            self.assertIsNotNone(total.free_space_new)
            self.assertIsNotNone(total.report_portf_value)
            self.assertIsNotNone(total.report_cash_bal)

        async def test_get_portfolio_products_info(self):
            session = await _IntegrationLogin._login()
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

        async def test_get_price_series(self):
            session = await _IntegrationLogin._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_isin='NL0000235190',
                    product_type_id=PRODUCT.TYPEID.STOCK
                    )

            # In a context where we'd want to optimize, we want to
            # build the pipeline by awaiting on each product instead of a bulk
            # gather to not block execution while we wait for data on some
            # of the products.
            self.assertGreaterEqual(len(products), 1, products)

            LOGGER.debug('test_get_price_series products| %s',
                         tuple(p.__dict__ for p in products))

            products = filter(
                    lambda p: (
                        p.info.product_type == PRODUCT.TYPE.STOCK
                        and p.info.tradable is True
                        and p.info.symbol == 'AIR'
                        ),
                    products)
            products = list(products)
            LOGGER.debug('test_get_price_series products filtered| %s',
                         pprint.pformat(tuple(p.__dict__ for p in products)))

            self.assertGreaterEqual(len(products), 1)
            # Select product
            for product in products:
                if product.base.product_type_id == PRODUCT.TYPEID.STOCK:
                    # Let's take the first stock as example
                    break

            LOGGER.debug('test_get_price_series price_data 1| %s',
                         product.__dict__)
            price_data = await degiroasync.api.get_price_series(session, product)
            LOGGER.debug('test_get_price_series price_data 2| %s',
                         price_data)
            self.assertGreaterEqual(len(price_data.price), 1)
            self.assertGreaterEqual(len(price_data.date), 1)

            price_data = await degiroasync.api.get_price_series(
                    session,
                    product,
                    period=PRICE.PERIOD.P1WEEK,
                    resolution=PRICE.RESOLUTION.PT1D,
                    data_type=PRICE.TYPE.OHLC)
            LOGGER.debug('test_get_price_series price_data ohlc 3| %s',
                         price_data)
            self.assertGreaterEqual(len(price_data.price), 1)
            self.assertEqual(len(price_data.price[0]), 4)
            self.assertGreaterEqual(
                    len(price_data.date),
                    len(price_data.price))

        async def test_get_price_series_symbol_exchange(self):
            # First get product
            session = await _IntegrationLogin._login()
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

            price_data = await degiroasync.api.get_price_series(session, product)
            LOGGER.debug("test_get_price_series| %s", price_data.price)
            LOGGER.debug("test_get_price_series| %s", price_data.date)
            self.assertGreaterEqual(len(price_data.price), 1)
            self.assertGreaterEqual(len(price_data.date), 1)

            date = price_data.date
            price = price_data.price
            self.assertEqual(len(date), len(price))

        async def test_get_price_series_day_resolution(self):
            session = await _IntegrationLogin._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_isin='NL0000235190',
                    by_exchange='EPA',
                    product_type_id=PRODUCT.TYPEID.STOCK
                    )
            LOGGER.debug('test_get_price_series_day_resolution| products %s',
                         pprint.pformat([p.__dict__ for p in products]))

            # In a context where we'd want to optimize, we want to
            # build the pipeline by awaiting on each product instead of a bulk
            # gather to not block execution while we wait for data on some
            # of the products.
            #await asyncio.gather(*[p.await_product_info() for p in products])
            #products = [p async for p in products_gen]
            self.assertEqual(len(products), 1)
            product = products[0]

            LOGGER.debug('test_get_price_series_day_resolution| product %s',
                         pprint.pformat(product.__dict__))

            self.assertEqual(product.info.product_type_id,
                             PRODUCT.TYPEID.STOCK)

            price_data = await degiroasync.api.get_price_series(
                    session,
                    product,
                    resolution=PRICE.RESOLUTION.PT1D,
                    period=PRICE.PERIOD.P1MONTH,
                    )
            LOGGER.debug('test_get_price_series_day_resolution| price_data %s',
                         price_data)
            self.assertGreaterEqual(len(price_data.price), 1)
            self.assertGreaterEqual(len(price_data.date), 1)
            date_series = price_data.date
            price_series = price_data.price
            self.assertEqual(len(date_series), len(price_series))
            LOGGER.debug("test_get_price_series_day_resolution| "
                         "date_series len %s", len(date_series))
            self.assertGreaterEqual(
                    len(date_series), 15,
                    "We should have daily data for a month with one sample "
                    "per day.")

            # We entered PT1D resolution, check that we have one data point
            # per day at most
            start = datetime.datetime.now() - datetime.timedelta(days=60)
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

    class TestDegiroasyncIntegrationSearch(
            _IntegrationLogin,
            unittest.IsolatedAsyncioTestCase):
        async def test_search_product_isin(self):
            session = await _IntegrationLogin._login()
            isin = 'NL0000235190'  # Airbus ISIN
            products = await degiroasync.api.search_product(
                    session,
                    by_isin=isin)
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                # We should only have airbus products here
                self.assertTrue('airbus' in product.info.name.lower())

        async def test_search_product_symbol(self):
            session = await _IntegrationLogin._login()
            symbol = 'AIR'
            products = await degiroasync.api.search_product(session,
                                                            by_symbol=symbol)
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                self.assertEqual(symbol, product.info.symbol, product.info)

        async def test_search_product_symbol_air(self):
            session = await _IntegrationLogin._login()
            symbol = 'AIR'  # GE symbol on EPA
            products = await degiroasync.api.search_product(session,
                                                            by_symbol=symbol,
                                                            by_exchange='EPA')
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                # We should only have airbus products here
                self.assertTrue(
                        'airbus' in product.info.name.lower())

        async def test_search_product_text(self):
            session = await _IntegrationLogin._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_text='airbus')
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                # We should only have airbus products here
                self.assertTrue('airbus' in product.info.name.lower())

        async def test_search_product_symbol_exchange(self):
            session = await _IntegrationLogin._login()
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

        async def test_search_product_country(self):
            session = await _IntegrationLogin._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_country='FR',
                    max_iter=1,  # We don't need every product for this test.
                    )
            # The point of implementing filtering on symbol and exchange
            # is to target one specific product. Raise an error if it doesn't
            # work.
            self.assertGreaterEqual(len(products), 1)
            for product in products:
                self.assertEqual(
                        session.dictionary.exchange_by(
                            id=product.info.exchange_id).country_name,
                        'FR'
                        )

        async def test_search_product_index(self):
            session = await _IntegrationLogin._login()
            products = await degiroasync.api.search_product(
                    session,
                    by_index='CAC 40',
                    max_iter=1,  # We don't need every product for this test.
                    )
            LOGGER.debug("Integration Test search_product_index| %s", products)
            # The point of implementing filtering on symbol and exchange
            # is to target one specific product. Raise an error if it doesn't
            # work.
            self.assertEqual(len(products), 40)

    class TestDegiroasyncIntegrationExchangeDictionary(
            unittest.IsolatedAsyncioTestCase):
        async def test_product_dictionary_attributes(self):
            session = await _IntegrationLogin._login()
            dictionary = await degiroasync.api.ExchangeDictionary(session)

            regions = dictionary.regions
            self.assertIn('Europe', (r.name for r in regions))
            countries = dictionary.countries
            self.assertIn('NL', (c.name for c in countries))
            exchanges = dictionary.exchanges
            self.assertIn('XAMS', (e.mic_code for e in exchanges))

        async def test_product_dictionary_exchange_by(self):
            session = await _IntegrationLogin._login()
            dictionary = await degiroasync.api.ExchangeDictionary(session)
            eam_exc = dictionary.exchange_by(hiq_abbr='EAM')
            self.assertEqual(eam_exc.mic_code, 'XAMS')
            self.assertEqual(eam_exc.country_name, 'NL')

        async def test_index_populate_indices(self):
            session = await _IntegrationLogin._login()
            await session.dictionary.populate_indices_info(session)

            index = session.dictionary.index_by(name='CAC 40')
            self.assertEqual(index.info.symbol, 'CAC INDEX')

        async def test_index_info(self):
            session = await _IntegrationLogin._login()
            index = session.dictionary.index_by(name='CAC 40')
            await index.get_info(session)

            self.assertEqual(index.info.symbol, 'CAC INDEX')

    class TestDegiroasyncIntegrationOrders(
            unittest.IsolatedAsyncioTestCase):
        async def test_get_orders(self):
            session = await _IntegrationLogin._login()
            orders, orders_hist = await degiroasync.api.get_orders(session)
            LOGGER.debug("test_get_orders orders| %s", orders)
            LOGGER.debug("test_get_orders orders hist| %s", orders_hist)
            for o in itertools.chain(orders, orders_hist):
                self.assertTrue(isinstance(o, Order))

        async def test_get_transactions(self):
            session = await _IntegrationLogin._login()
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
            session = await _IntegrationLogin._login()
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


if __name__ == '__main__':
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
            "%(asctime)s-%(name)s-%(levelname)s-%(message)",
            "%Y%m%d"
            )
    if handler not in LOGGER.handlers:
        LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG)
    unittest.main()
