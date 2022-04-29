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
from .constants import ResponseError


LOGGER = logging.getLogger(LOGGER_NAME)


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
        func: Union[Callable, None] = None,
        *,
        maxsize: int = 128,
        typed: bool = False,
        seconds: Union[None, float] = None,
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
    first_start = []
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
    Raise an httpx.HTTPError if return code != 200
    """
    if response.status_code not in (httpx.codes.OK, httpx.codes.CREATED):
        raise ResponseError(
            f"Error on call: url {response.url}"
            f" | code {response.status_code} | content {response.content}")


def dict_from_attr_list(
        attributes_list: List[Dict[str, Any]],
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


# Logs helpers
FORMAT_DEFAULT = '%(asctime)s-%(name)s-%(levelname)s- %(message)s'
STREAMHANDLER_DEFAULT = logging.StreamHandler(stream=sys.stdout)
