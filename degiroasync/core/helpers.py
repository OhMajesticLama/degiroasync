from __future__ import annotations
import typing
from typing import List, Dict, Any, Iterable
from typing import Coroutine
import logging
import sys
import asyncio
import concurrent.futures
import contextvars

import httpx

#from .core import Session
#from .core import ResponseError
from .constants import LOGGER_NAME



LOGGER = logging.getLogger(LOGGER_NAME)

class ResponseError(Exception):
    "Raised when bad response has been received from server."


def run_in_new_thread(
        coroutine: Coroutine,
        ) -> concurrent.futures.Future:
    """
    Use to stop async creep: when you need to run a coroutine and return in
    a synchronous call.
    """
    loop = asyncio.new_event_loop()
    #loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(1) as executor:
        future = executor.submit(
                loop.run_until_complete,
                coroutine)

    return future

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
    if not response.status_code in (httpx.codes.OK, httpx.codes.CREATED):
        raise ResponseError(f"Error on call: url {response.url}"
                f" | code {response.status_code} | content {response.content}")


def check_keys(data: dict, keys: Iterable[str]):
    """
    Helper to check keys are in data.
    """
    for attr in keys:
        if attr not in data:
            raise AssertionError(f'{attr} not found in config.'
                    ' Please try again later and open a bug ticket if the problem persits.')


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
        #try:
        #    dict_out[attr['name']] = attr['value']
        #except Exception as exc:
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
        setattr(obj,k, v)
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


def set_logs(
        logger: logging.Logger,
        logging_level: int,
        log_format: str = FORMAT_DEFAULT,
        handler: logging.Handler = STREAMHANDLER_DEFAULT
        ):
    "Configure logging for this module."
    # Configure logging
    logger.setLevel(logging_level)
    #handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging_level)
    # DEBUG: Will need to find where another handler is being added when running tests. nose2 catches loggers by default.
    #logger.addHandler(handler)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
