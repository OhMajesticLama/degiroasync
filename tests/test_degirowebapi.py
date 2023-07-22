import unittest
import logging
import os
import pprint
import asyncio
import datetime
from typing import Optional
import unittest.mock
from unittest.mock import MagicMock

import httpx

import degiroasync
import degiroasync.webapi
import degiroasync.core
import degiroasync.core.helpers
from degiroasync.core import Credentials
from degiroasync.core import SessionCore
from degiroasync.core.constants import PRODUCT
from degiroasync.core.constants import PRICE
from degiroasync.core.constants import ORDER
from degiroasync.core.constants import LOGIN
from degiroasync.core import ResponseError
from degiroasync.core import BadCredentialsError
from degiroasync.core.helpers import ThrottlingClient
from degiroasync.webapi import get_config
from degiroasync.webapi import get_products_info
from degiroasync.webapi import get_company_profile
from degiroasync.webapi import get_news_by_company


LOGGER = logging.getLogger(degiroasync.core.LOGGER_NAME)

RUN_INTEGRATION_TESTS = 0
try:
    _env_var = os.environ.get('DEGIROASYNC_INTEGRATION')
    RUN_INTEGRATION_TESTS = int(_env_var)
except (ValueError, TypeError):
    LOGGER.info('degiroasync integration tests will *not* run.')

RUN_BAD_CREDENTIALS = 0
try:
    _env_var = os.environ.get('DEGIROASYNC_INTEGRATION_BAD_CREDENTIALS')
    RUN_BAD_CREDENTIALS = int(_env_var)
except (ValueError, TypeError):
    LOGGER.info('degiroasync Bad Credentials integration test will *not* run.')


class TestDegiroAsyncWebAPI(unittest.IsolatedAsyncioTestCase):
    @unittest.mock.patch('degiroasync.core.helpers.ThrottlingClient.post')
    async def test_login_bad_credentials(
            self,
            post_m
            ):
        """
        Verify that BadCredentialsError is raised when endpoint returns a bad
        credentials error.
        """
        post_m.return_value = MagicMock()
        response = post_m.return_value
        response.json = MagicMock(
                return_value={
                    'status': LOGIN.BAD_CREDENTIALS,
                    'content': 'badCredentials'})
        response.status_code = httpx.codes.BAD_REQUEST

        credentials = Credentials(
            username='dummyaccount123456',
            password='dummydummy'
                )
        with self.assertRaises(BadCredentialsError):
            await degiroasync.webapi.login(credentials)


if RUN_INTEGRATION_TESTS:
    LOGGER.info('degiroasync.webapi integration tests will run.')
    from tests.integration_login import _IntegrationLogin

    class TestDegiroAsyncWebAPIIntegration(
            _IntegrationLogin,
            unittest.IsolatedAsyncioTestCase):

        async def test_login(self):
            session = await _IntegrationLogin._login()
            self.assertTrue('JSESSIONID' in session.cookies,
                            "No JSESSIONID found.")

        if RUN_BAD_CREDENTIALS:
            async def test_login_bad_credentials(self):
                credentials = Credentials(
                    username='dummyaccount123456',
                    password='dummydummy'
                        )
                with self.assertRaises(BadCredentialsError):
                    await degiroasync.webapi.login(credentials)

        async def test_config(self):
            session = await _IntegrationLogin._login()
            await get_config(session)
            LOGGER.debug('test_config| %s', session.config)
            self.assertTrue(
                    session.config.pa_url is not None,
                    "paUrl not defined.")
            self.assertTrue(
                    session.config.product_search_url is not None,
                    "productSearchUrl not defined.")
            self.assertTrue(
                    session.config.trading_url is not None,
                    "tradingUrl not defined.")

        async def test_portfolio(self):
            session = await _IntegrationLogin._login()

            resp_json = await degiroasync.webapi.get_portfolio(session)
            LOGGER.debug("test_portfolio| %s", resp_json)
            self.assertTrue('portfolio' in resp_json)
            self.assertTrue('value' in resp_json['portfolio'])

        async def test_portfolio_total(self):
            session = await _IntegrationLogin._login()

            resp_json = await degiroasync.webapi.get_portfolio_total(session)
            LOGGER.debug("test_portfolio_total| %s", resp_json)
            self.assertTrue('totalPortfolio' in resp_json)
            self.assertTrue('value' in resp_json['totalPortfolio'])

        async def test_get_products_info(self):
            session = await _IntegrationLogin._login()

            resp_json = await degiroasync.webapi.get_portfolio(session)
            portfolio = resp_json['portfolio']
            product_ids = filter(lambda x: x is not None,
                                 (product.get('id')
                                  for product in portfolio['value']))
            response = await get_products_info(session,
                                               [p for p in product_ids])
            self.assertIsInstance(response, dict)

            response = await degiroasync.webapi.get_products_info(session,
                                                                  ["72906"])
            self.assertIsInstance(response, dict)
            LOGGER.debug('webapi.test_get_products_info| %s',
                         pprint.pformat(response))

        async def test_get_company_profile(self):
            session = await _IntegrationLogin._login()

            isin = "NL0000235190"
            resp_json = await get_company_profile(session, isin)
            self.assertTrue('data' in resp_json, resp_json)
            self.assertTrue('businessSummary' in resp_json['data'], resp_json)
            LOGGER.debug('webapi.test_get_company_profile| %s',
                         pprint.pformat(resp_json))

        async def test_get_news_by_company(self):
            session = await _IntegrationLogin._login()

            isin = "NL0000235190"
            resp_json = await get_news_by_company(session, isin)
            self.assertTrue('data' in resp_json, resp_json)
            self.assertTrue('items' in resp_json['data'], resp_json)

        async def test_get_price_series(self):
            """
            Simply check that we don't have an error and data is not empty.
            """
            session = await _IntegrationLogin._login()

            vwdId = '360114899'

            resp_json = await degiroasync.webapi.get_price_series(
                    session,
                    vwdId=vwdId,
                    vwdIdentifierType='issueid')
            LOGGER.debug('get_price_series response: %s', resp_json)
            LOGGER.debug(resp_json)
            self.assertIn('series', resp_json)
            self.assertIn('data', resp_json['series'][0])

        async def test_get_price_series_month(self):
            session = await _IntegrationLogin._login()

            vwdId = '360114899'

            resp_json = await degiroasync.webapi.get_price_series(
                    session,
                    vwdId=vwdId,
                    period=PRICE.PERIOD.P1MONTH,
                    resolution=PRICE.RESOLUTION.PT1M,
                    vwdIdentifierType='issueid')
            LOGGER.debug(resp_json)
            self.assertIn('resolution', resp_json)
            self.assertEqual(resp_json['resolution'], PRICE.RESOLUTION.PT1M)
            self.assertIn('series', resp_json)
            self.assertIn('data', resp_json['series'][0])

        async def test_get_price_series_ohlc(self):
            session = await _IntegrationLogin._login()

            vwdId = '360114899'

            resp_json = await degiroasync.webapi.get_price_series(
                    session,
                    vwdId=vwdId,
                    period=PRICE.PERIOD.P1MONTH,
                    resolution=PRICE.RESOLUTION.PT1M,
                    vwdIdentifierType='issueid',
                    data_type=PRICE.TYPE.OHLC,
                    )
            LOGGER.debug(resp_json)
            self.assertIn('resolution', resp_json)
            self.assertEqual(resp_json['resolution'], PRICE.RESOLUTION.PT1M)
            self.assertIn('series', resp_json)
            self.assertIn('data', resp_json['series'][0])
            self.assertEqual(
                    len(resp_json['series'][0]['data'][0]), 5,
                    "We should have 5 entries per row (index + O H L C)")

        async def test_get_price_series_month_pt1d(self):
            session = await _IntegrationLogin._login()

            vwdId = '360114899'

            resp_json = await degiroasync.webapi.get_price_series(
                    session,
                    vwdId=vwdId,
                    period=PRICE.PERIOD.P1MONTH,
                    resolution=PRICE.RESOLUTION.PT1D,
                    vwdIdentifierType='issueid')
            LOGGER.debug('get_price_series_month_pt1d| response: %s',
                         resp_json)
            LOGGER.debug(resp_json)
            self.assertIn('resolution', resp_json)
            self.assertEqual(resp_json['resolution'], PRICE.RESOLUTION.PT1D)
            self.assertIn('series', resp_json)
            self.assertIn('data', resp_json['series'][0])

        async def test_search_product(self):
            session = await _IntegrationLogin._login()

            search = "AIRBUS"
            resp_json = await degiroasync.webapi.search_product(
                    session,
                    search)
            self.assertIn('products', resp_json, resp_json)
            self.assertGreaterEqual(len(resp_json['products']), 1)
            self.assertIn('id', resp_json['products'][0], resp_json)
            self.assertIn('isin', resp_json['products'][0], resp_json)
            self.assertIn('name', resp_json['products'][0], resp_json)

        #async def test_search_product_exchange(self):
        #    raise NotImplementedError()
        #    session = await _IntegrationLogin._login()

        #    search = "AIRBUS"
        #    resp_json = await degiroasync.webapi.search_product(
        #            session,
        #            search)
        #    self.assertIn('products', resp_json, resp_json)
        #    self.assertGreaterEqual(len(resp_json['products']), 1)
        #    self.assertIn('id', resp_json['products'][0], resp_json)
        #    self.assertIn('isin', resp_json['products'][0], resp_json)
        #    self.assertIn('name', resp_json['products'][0], resp_json)

        async def test_search_product_by_index(self):
            session = await _IntegrationLogin._login()
            resp_json = await degiroasync.webapi.get_product_dictionary(
                    session,
                    )

            index = session.dictionary.index_by(name='CAC 40')
            LOGGER.debug("test_search_product_by_index| Index: %s", index)
            resp_json = await degiroasync.webapi.search_product(
                    session,
                    index_id=index.id,
                    limit=100
                    )
            self.assertIn('products', resp_json, resp_json)
            # We should have 40 products in CAC 40
            self.assertGreaterEqual(len(resp_json['products']), 40)

        async def test_product_dictionary(self):
            session = await _IntegrationLogin._login()

            resp_json = await degiroasync.webapi.get_product_dictionary(
                    session
                    )

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
            _IntegrationLogin,
            unittest.IsolatedAsyncioTestCase):
        """
        Set Orders will *not* be tested: this would imply being charged every
        time tests are executed.
        """
        async def test_get_orders(self):
            session = await _IntegrationLogin._login()

            resp_json = await degiroasync.webapi.get_orders(session)
            LOGGER.debug("test_get_orders| %s", pprint.pformat(resp_json))
            self.assertIn('orders', resp_json)
            self.assertIsInstance(resp_json['orders'], list)

        async def test_check_order(self):
            session = await _IntegrationLogin._login()

            # Leverage api.search_product to get a specific product_id
            # as example for integration testing of check_order.
            # This is introducing a dependency on api module, but is easier
            # to manage. Future improvement opportunit for this test: implement
            # required query and filter here using only webapi.
            from degiroasync import api
            session.dictionary = await api.get_dictionary(
                    session)
            products = await api.search_product(
                    session,
                    by_symbol="AIR",
                    by_exchange="EPA",
                    product_type_id=PRODUCT.TYPEID.STOCK
                    )
            self.assertEqual(len(products), 1,
                             "We should only have one product here")
            product = products[0]
            # Reminder: typeId = 1 is STOCK
            LOGGER.debug("test_check_order| product: %s . %s . %s . %s",
                         product.info.symbol,
                         product.info.name,
                         product.info.product_type_id,
                         product.base.id)

            # This will *not* place the order: it would have to be confirmed
            # with `confirm_order` call.
            resp_json = await degiroasync.webapi.check_order(
                    session,
                    product_id=product.base.id,
                    buy_sell=ORDER.ACTION.BUY,
                    time_type=ORDER.TIME.DAY,
                    order_type=ORDER.TYPE.LIMITED,
                    size=1,
                    price=50
                    )
            LOGGER.debug("test_check_order| %s", pprint.pformat(resp_json))
            self.assertIn('data', resp_json)
            self.assertIn('confirmationId', resp_json['data'])
            self.assertIn('freeSpaceNew', resp_json['data'])
            self.assertIn('transactionFee', resp_json['data'])

            resp_json = await degiroasync.webapi.check_order(
                    session,
                    product_id=product.base.id,
                    buy_sell=ORDER.ACTION.SELL,
                    time_type=ORDER.TIME.DAY,
                    order_type=ORDER.TYPE.LIMITED,
                    size=1,
                    price=50
                    )
            LOGGER.debug("test_check_order| %s", pprint.pformat(resp_json))
            self.assertIn('data', resp_json)
            self.assertIn('confirmationId', resp_json['data'])
            self.assertIn('freeSpaceNew', resp_json['data'])
            self.assertTrue(
                    'transactionFee' in resp_json['data']
                    or 'transactionOppositeFee' in resp_json['data'],
                    resp_json['data'])

        async def test_get_account_info(self):
            session = await _IntegrationLogin._login()
            resp_json = await degiroasync.webapi.get_account_info(session)
            LOGGER.debug("test_get_account_info| response: %s", resp_json)

            self.assertIn('data', resp_json)
            self.assertIn('clientId', resp_json['data'])
            self.assertIn('baseCurrency', resp_json['data'])
            # Not sure what more to test here. To be extended when this call
            # usage has been identified.

        async def test_get_orders_history(self):
            session = await _IntegrationLogin._login()
            to_date = datetime.datetime.today()
            from_date = datetime.datetime.today() - datetime.timedelta(days=7)
            date_format = degiroasync.webapi.orders.ORDER_DATE_FORMAT
            resp_json = await degiroasync.webapi.get_orders_history(
                    session,
                    from_date=from_date.strftime(date_format),
                    to_date=to_date.strftime(date_format)
                    )
            LOGGER.debug("test_get_orders_history| response: %s", resp_json)

            self.assertIn('data', resp_json)
            data = resp_json['data']
            for order in data:
                self.assertIn('created', order)
                self.assertIn('productId', order)
                self.assertIn('size', order)
                self.assertIn('price', order)
                self.assertIn('buysell', order)
                self.assertIn(order['buysell'], ('B', 'S'))
                self.assertIn('orderTypeId', order)
                self.assertIn('orderTimeTypeId', order)
                self.assertIn('type', order)
                self.assertIn('status', order)
                self.assertIn('last', order)
                self.assertIn('isActive', order)
                self.assertIn('currentTradedSize', order)
                self.assertIn('totalTradedSize', order)

        async def test_get_orders_history_date_check(self):
            session = await _IntegrationLogin._login()
            with self.assertRaises(ValueError):
                await degiroasync.webapi.get_orders_history(
                    session,
                    from_date='garbage',
                    to_date='garbage')

        async def test_get_transactions(self):
            session = await _IntegrationLogin._login()
            to_date = datetime.datetime.today()
            from_date = datetime.datetime.today() - datetime.timedelta(days=7)
            date_format = degiroasync.webapi.orders.ORDER_DATE_FORMAT
            resp_json = await degiroasync.webapi.get_transactions(
                    session,
                    from_date=from_date.strftime(date_format),
                    to_date=to_date.strftime(date_format)
                    )
            LOGGER.debug("test_get_orders_history| response: %s", resp_json)

            self.assertIn('data', resp_json)
            data = resp_json['data']
            for trans in data:
                self.assertIn('id', trans)
                self.assertIn('productId', trans)
                self.assertIn('quantity', trans)
                self.assertIn('price', trans)
                self.assertIn('fxRate', trans)
                self.assertIn('nettFxRate', trans)
                self.assertIn('transfered', trans)
                self.assertIn('buysell', trans)
                self.assertIn(trans['buysell'], ('B', 'S'))
                self.assertIn('transactionTypeId', trans)

        async def test_get_transactions_date_check(self):
            session = await _IntegrationLogin._login()
            with self.assertRaises(ValueError):
                await degiroasync.webapi.get_orders_history(
                    session,
                    from_date='garbage',
                    to_date='garbage')


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
