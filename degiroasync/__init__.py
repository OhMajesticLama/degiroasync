import logging

from .core import Credentials
from .core import Config
from .core import ResponseError
from .core import LOGGER_NAME
from . import webapi
from . import api

LOGGER = logging.getLogger(LOGGER_NAME)
LOGGER.setLevel(logging.DEBUG)

__all__ = [
        # Choice between strings or import errors at this level.
        # An object missing __name__ will fail at module import, typos
        # in object names are flagged by editor's tools and easier to catch
        # than typos in a string.
        obj.__name__ for obj in (  # type: ignore
            Credentials,
            Config,
            api,
            webapi,
            ResponseError,
        )
] + ['LOGGER_NAME']
