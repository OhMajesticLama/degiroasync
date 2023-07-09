from __future__ import annotations
from typing import List, Dict, Any, Iterable, Callable, Union, Coroutine
from typing import Optional
import logging
import sys
import functools
import asyncio
import time


import asyncstdlib.functools as afunctools
import httpx

from .constants import LOGGER_NAME
from .constants import LOGIN
from .exceptions import ResponseError
from .exceptions import BadCredentialsError


LOGGER = logging.getLogger(LOGGER_NAME)
# Logs helpers
FORMAT_DEFAULT = '%(asctime)s-%(name)s-%(levelname)s- %(message)s'
STREAMHANDLER_DEFAULT = logging.StreamHandler(stream=sys.stdout)


class CoroCache:
    def __init__(self, coro: Coroutine):
        """
        Cache to allow awaiting coroutines several times.

        >>> async def f():
        ...     return 1
        ...
        >>> c = CoroCache(f())
        >>> await c
        1
        >>> await c
        1

        """
        self.coro = coro
        self.res: Optional[Any] = None
        self.wait: bool = True

    def __await__(self) -> Any:
        if self.wait:
            self.res = self.coro.__await__()
            self.wait = False
        return self.res


def lru_cache_timed(
        func: Optional[Callable] = None,
        /,
        maxsize: int = 128,
        typed: bool = False,
        seconds: Optional[float] = None,
):
    """
    Time-sensitive LRU cache that works with async functions.

    >>> @lru_cache_timed(seconds=120)
    ... async def foo():
    ...     asyncio.sleep(1)
    ...     return 1
    ...
    >>> import time
    >>> start = time.time()
    >>> await foo()
    1
    >>> time.time() - start > 1
    True
    >>> start = time.time()
    >>> await foo()
    1
    >>> time.time() - start < .1
    True
    """
    first_start: List[float] = []
    if func is not None:
        if asyncio.iscoroutinefunction(func):
            @afunctools.lru_cache(maxsize=maxsize, typed=typed)
            async def _in(time_key, *args, **kwargs):
                return await func(*args, **kwargs)

            @functools.wraps(func)
            async def _out(*args, **kwargs):
                if not len(first_start):
                    first_start.append(time.time())
                if seconds is None:
                    time_key = 1
                else:
                    time_key = (time.time() - first_start[0]) // seconds

                return await _in(time_key, *args, **kwargs)

            return _out

        else:
            @functools.lru_cache(maxsize=maxsize, typed=typed)
            def _in(time_key, *args, **kwargs):
                return func(*args, **kwargs)

            @functools.wraps(func)
            def _out(*args, **kwargs):
                if not len(first_start):
                    first_start.append(time.time())
                if seconds is None:
                    time_key = 1
                else:
                    time_key = (time.time() - first_start[0]) // seconds

                return _in(time_key, *args, **kwargs)

            return _out
    else:
        return lambda func: lru_cache_timed(func,
                                            maxsize=maxsize,
                                            typed=typed,
                                            seconds=seconds)


def camelcase_to_snake(text: str) -> str:
    """
    Convert a camelCase text to snake_case.

    This helper replace any capitalized character by its lowered version
    preceded by '_'.

    This helper does not check that input text is camel case or not.

    >>> s = 'iAmCamelCase'
    >>> camelcase_to_snake(s)
    'i_am_camel_case'
    >>> # Ignore fully uppercase text.
    >>> camelcase_to_snake("ALL_CAPS")
    'ALL_CAPS'
    """
    if text.isupper():
        return text
    return ''.join(map(lambda c: '_' + c.lower() if c.isupper() else c, text))


def camelcase_dict_to_snake(
        dict_in: Dict[str, Any],
        /,
        recursive: bool = True) -> Dict[str, Any]:
    """
    Convert keys of dictionary with `str` keys from camelCase to snake_case.

    This does not care for structures with depth: values dictionaries will not
    be updated to snake_case.

    >>> d = {'fooBar': 2, 'camelCase': {'camelCase': 1}}
    >>> camelcase_dict_to_snake(d)
    {'foo_bar': 2, 'camel_case': {'camel_case': 1}}
    >>> camelcase_dict_to_snake(d, recursive=False)
    {'foo_bar': 2, 'camel_case': {'camelCase': 1}}
    """
    if not recursive:
        return {
            camelcase_to_snake(k): v
            for k, v in dict_in.items()
        }
    else:
        return {
            camelcase_to_snake(k):
                camelcase_dict_to_snake(v, recursive=True)
                if isinstance(v, dict) else v
            for k, v in dict_in.items()
        }


def join_url(*sections):
    """
    Helper to build urls, with slightly different behavior from
    urllib.parse.urljoin, see example below.

    >>> join_url('https://foo.bar', '/rest/of/url')
    'https://foo.bar/rest/of/url'
    >>> join_url('https://foo.bar/product', '/rest/of/url')
    'https://foo.bar/product/rest/of/url'
    >>> join_url('https://foo.bar/product/', '/rest/of/url')
    'https://foo.bar/product/rest/of/url'
    >>> # We need this helper because of below
    ... # urllib.parse.urljoin behavior that is not suitable
    ... # for our purpose.
    >>> import urllib.parse
    >>> urllib.parse.urljoin('https://foo.bar/product', '/rest//of/url')
    'https://foo.bar/rest/of/url'

    """
    return '/'.join(s.strip('/') for s in sections)


def check_response(response: httpx.Response):
    """
    Raises
    ------

    BadCredentialsError:
        If return code == 400 and web API status returns bad credentials code.
    ResponseError:
        If return code != 200
    """
    if response.status_code == httpx.codes.BAD_REQUEST:
        resp_json = response.json()
        if (
                'status' in resp_json
                and resp_json['status'] == LOGIN.BAD_CREDENTIALS
                ):
            raise BadCredentialsError(
                    f"Bad Credentials. Reponse content: "
                    f"{str(response.content)}")

    if response.status_code not in (httpx.codes.OK, httpx.codes.CREATED):
        raise ResponseError(
            f"Error on call: url {response.url}"
            f" | code {response.status_code} | "
            f"content {str(response.content)}")


def dict_from_attr_list(
        attributes_list: Iterable[Dict[str, Any]],
        ignore_error=False) -> Dict[str, Any]:
    """
    Helper to build a dict from an attribute list as returned by the web API.

    attributes_list is expected to be an iterable of dict with 'isAdded',
    'name', 'value'. See below for an example.
    ```
            [
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
                 {'isAdded': True,
                  'name': 'accruedInterest'},
                 {'isAdded': True,
                  'name': 'plBase',
                  'value': {'EUR': -6717.901595272}},
                 {'isAdded': True,
                  'name': 'todayPlBase',
                  'value': {'EUR': -7300.0}},
                 {'isAdded': True,
                  'name': 'portfolioValueCorrection',
                  'value': 0},
                 {'isAdded': True,
                  'name': 'breakEvenPrice',
                  'value': 68.01},
                 {'isAdded': True,
                  'name': 'averageFxRate',
                  'value': 1},
                 {'isAdded': True,
                  'name': 'realizedProductPl',
                  'value': 97.098302728},
                 {'isAdded': True,
                  'name': 'realizedFxPl',
                  'value': 0},
                 {'isAdded': True,
                  'name': 'todayRealizedProductPl',
                  'value': 0.0},
                 {'isAdded': True,
                  'name': 'todayRealizedFxPl',
                  'value': 0}
            ]
    ```

    """
    dict_out = {}
    for attr in attributes_list:
        if 'name' not in attr or 'value' not in attr:
            message = f"A provided params does not have a 'name' or 'value': {attr}"
            LOGGER.info(message)
            if not ignore_error:
                raise ValueError(message)
            else:
                continue
        name, value = attr['name'], attr['value']
        if not hasattr(name, int.__hash__.__name__):
            raise ValueError(f"{name} in {attr} is not hashable:"
                             " it can't be used as dict key.")
        dict_out[name] = value
        # TODO: above should never raise an error as long as attr['name'] is
        # hashable. May
        # try:
        #    dict_out[attr['name']] = attr['value']
        # except Exception as exc:
        #    LOGGER.error('dict_from_attr| %s: %s', type(exc), exc.args)
        #    if not ignore_error:
        #        raise exc
    return dict_out


def set_params(
        obj: Any,
        attributes_list: Iterable[Dict[str, str]],
        ignore_error=False) -> Any:
    """
    This is a helper to translate Degiro-format params to a Python object.

    Set `params` on `obj`.

    `params` is expected to be an iterable of dict with 'isAdded', 'name',
    'value'. See below for an example.

    ```
            [
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
                 {'isAdded': True,
                  'name': 'accruedInterest'},
                 {'isAdded': True,
                  'name': 'plBase',
                  'value': {'EUR': -6717.901595272}},
                 {'isAdded': True,
                  'name': 'todayPlBase',
                  'value': {'EUR': -7300.0}},
                 {'isAdded': True,
                  'name': 'portfolioValueCorrection',
                  'value': 0},
                 {'isAdded': True,
                  'name': 'breakEvenPrice',
                  'value': 68.01},
                 {'isAdded': True,
                  'name': 'averageFxRate',
                  'value': 1},
                 {'isAdded': True,
                  'name': 'realizedProductPl',
                  'value': 97.098302728},
                 {'isAdded': True,
                  'name': 'realizedFxPl',
                  'value': 0},
                 {'isAdded': True,
                  'name': 'todayRealizedProductPl',
                  'value': 0.0},
                 {'isAdded': True,
                  'name': 'todayRealizedFxPl',
                  'value': 0}
            ]
    ```

    """
    for k, v in dict_from_attr_list(
            attributes_list, ignore_error=ignore_error).items():
        setattr(obj, k, v)

    return obj


def setattrs(obj: Any, **attributes) -> Any:
    "Set all attributes on obj."
    for k, v in attributes.items():
        setattr(obj, k, v)
    return obj


def check_keys(data: dict, keys: Iterable[str]):
    """
    Helper to check keys are in data. Raise KeyError if that is not the case
    """
    for attr in keys:
        if attr not in data:
            name = 'data'
            if hasattr(data, '__name__'):
                name = data.__name__
            exc = KeyError(
                "{attr} not found in {name}. Data content: {data}.".format(
                    attr=attr,
                    name=name,
                    data=data
                ))
            raise exc


class ThrottlingClient:
    def __init__(
            self,
            *,
            max_requests=10,
            period_seconds=1,
            **kwargs
            ):
        """
        Wraps httpx.AsyncClient and throttle requests.


        Parameters
        ----------

        max_requests
            Maximum number of requests per `period_seconds` before throttling.
            If <= 0, no limit.

        period_seconds
            Period on which to count requests.

        kwargs
            Additional keywords are passed to httpx.AsyncClient

        """
        self._max_requests = max_requests
        self._period_s = period_seconds
        self._requests_times = []
        self._async_client: Optional[httpx.AsyncClient] = None
        self._client_open: Optional[httpx.AsyncClient] = None
        self._count_open = 0
        self._kwargs = kwargs

    def _throttle(method):
        "Decorator to wrap method to add throttling capabilities."
        @functools.wraps(method)
        async def wrapper(self, *args, **kwargs):
            LOGGER.debug(
                    "ThrottlingClient._throttle: "
                    "len(self._requests_times) %s",
                    len(self._requests_times))
            while (
                    self._max_requests > 0 and
                    len(self._requests_times) >= self._max_requests
                    ):
                # Clean register
                to_del = 0
                for ind, timestamp in enumerate(self._requests_times):
                    if time.time() - timestamp > self._period_s:
                        to_del += 1
                while to_del > 0:
                    self._requests_times.pop(0)
                    to_del -= 1
                # requests_times might be empty now.
                if len(self._requests_times) > 0:
                    time_delta = (self._requests_times[0] + self._period_s
                                  - time.time())
                    if time_delta > 0:
                        LOGGER.debug(
                                "Throttle %s call for %.2f",
                                method,
                                time_delta)
                        await asyncio.sleep(time_delta)
            if self._max_requests > 0:
                self._requests_times.append(time.time())
            return await method(self, *args, **kwargs)
        return wrapper

    async def __aenter__(self):
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(**self._kwargs)
        if self._client_open is None:
            self._client_open = await self._async_client.__aenter__()
        self._count_open += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._count_open -= 1
        if self._count_open <= 0:
            await self._async_client.__aexit__(exc_type, exc_val, exc_tb)
            self._async_client = None
            self._client_open = None

    @_throttle
    @functools.wraps(httpx.AsyncClient.get)
    async def get(self, *args, **kwargs):
        return await self._client_open.get(*args, **kwargs)

    @_throttle
    @functools.wraps(httpx.AsyncClient.put)
    async def put(self, *args, **kwargs):
        return await self._client_open.put(*args, **kwargs)

    @_throttle
    @functools.wraps(httpx.AsyncClient.post)
    async def post(self, *args, **kwargs):
        return await self._client_open.post(*args, **kwargs)

    @_throttle
    @functools.wraps(httpx.AsyncClient.request)
    async def request(self, *args, **kwargs):
        return await self._client_open.request(*args, **kwargs)

    @_throttle
    @functools.wraps(httpx.AsyncClient.head)
    async def head(self, *args, **kwargs):
        return await self._client_open.head(*args, **kwargs)

    @_throttle
    @functools.wraps(httpx.AsyncClient.options)
    async def options(self, *args, **kwargs):
        return await self._client_open.options(*args, **kwargs)

    @_throttle
    @functools.wraps(httpx.AsyncClient.delete)
    async def delete(self, *args, **kwargs):
        return await self._client_open.delete(*args, **kwargs)
