import unittest
import asyncio
import time

import degiroasync.core
from degiroasync.core import join_url
from degiroasync.core import camelcase_to_snake
from degiroasync.core import camelcase_dict_to_snake
from degiroasync.core import set_params


class TestLRUCacheTimed(unittest.IsolatedAsyncioTestCase):
    async def test_cached_time_async(self):
        delay = 0.1  # in s

        @degiroasync.core.lru_cache_timed(seconds=delay*2)
        async def dummy():
            await asyncio.sleep(delay)
            return 2

        start = time.time()
        res = await dummy()
        self.assertEqual(res, 2)
        self.assertGreaterEqual(time.time() - start, delay)

        start2 = time.time()
        res = await dummy()
        self.assertEqual(res, 2)
        self.assertLessEqual(time.time() - start2, delay*0.5,
                             "Looks like result was not cached.")

        await asyncio.sleep(10*delay)

        start3 = time.time()
        res = await dummy()
        self.assertEqual(res, 2)
        self.assertGreaterEqual(time.time() - start3, delay,
                                "Looks like old cached result was not removed."
                                )

    async def test_cached_time_sync(self):
        delay = 0.1  # in s

        @degiroasync.core.lru_cache_timed(seconds=delay*1.5)
        def dummy():
            time.sleep(delay)
            return 1

        start = time.time()
        dummy()
        self.assertGreaterEqual(time.time() - start, delay)

        start2 = time.time()
        dummy()
        self.assertLessEqual(time.time() - start2, delay * 0.5,
                             "Looks like result was not cached.")

        await asyncio.sleep(delay)
        start3 = time.time()
        dummy()
        self.assertGreaterEqual(time.time() - start3, delay,
                                "Looks like old cached result was not removed."
                                )


class TestDegiroAsyncJoinUrl(unittest.TestCase):
    def test_join_url(self):
        url = join_url('https://foo.bar', '/rest/of/url')
        self.assertEqual(url, 'https://foo.bar/rest/of/url')
        url = join_url('https://foo.bar/product', '/rest/of/url')
        self.assertEqual(url, 'https://foo.bar/product/rest/of/url')
        url = join_url('https://foo.bar/product/', '/rest/of/url')
        self.assertEqual(url, 'https://foo.bar/product/rest/of/url')

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

        self.assertEqual(foo.id, '8614787')
        self.assertEqual(foo.positionType, 'PRODUCT')
        self.assertEqual(foo.size, 100)
        self.assertEqual(foo.price, 73.0)
        self.assertEqual(foo.value, 7300.0)

    def test_camelcase_to_snake(self):
        inp = 'iAmCamelCase'
        out = camelcase_to_snake(inp)
        self.assertEqual(out, 'i_am_camel_case')

    def test_camelcase_dict_to_snake(self):
        d = {'fooBar': 2, 'camelCase': {'camelCase': 1}}
        out = camelcase_dict_to_snake(d, recursive=False)
        self.assertEqual(out, {'foo_bar': 2, 'camel_case': {'camelCase': 1}})

    def test_camelcase_dict_to_snake_recursive(self):
        d = {'fooBar': 2, 'camelCase': {'camelCase': 1}}
        out = camelcase_dict_to_snake(d, recursive=True)
        self.assertEqual(out, {'foo_bar': 2, 'camel_case': {'camel_case': 1}})
