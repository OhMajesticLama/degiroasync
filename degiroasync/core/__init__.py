"""
Contains core data structures and helpers for degiroasync.

Key structures that are reused regularly through degiroasync API the below:
    - Credentials
    - SessionCore
    - ORDER
    - PRODUCT
    - TRANSACTION
    - POSITION
    - ResponseError

Check out their respective documentation for more details.
"""
from .helpers import join_url
from .helpers import lru_cache_timed
from .helpers import camelcase_to_snake
from .helpers import camelcase_dict_to_snake
from .helpers import set_params
from .constants import ORDER
from .constants import PRODUCT
from .constants import TRANSACTION
from .constants import PRICE
from .constants import POSITION
from .constants import LOGGER_NAME
from .core import check_session_client
from .core import check_session_config
from .core import Credentials
from .core import Config
from .core import SessionCore
from .core import URLs
from .core import PAClient
from .exceptions import ResponseError
from .exceptions import BadCredentialsError
from .exceptions import ContextError


# Fail at module import if an attribute is missing __name__: ignore mypy here.
__all__ = [obj.__name__ for obj in (  # type: ignore
    join_url,
    lru_cache_timed,
    camelcase_to_snake,
    camelcase_dict_to_snake,
    set_params,
    PRODUCT,
    ORDER,
    TRANSACTION,
    POSITION,
    PRICE,
    Credentials,
    Config,
    check_session_client,
    check_session_config,
    ResponseError,
    BadCredentialsError,
    ContextError,
    SessionCore,
    PAClient,
    URLs,
    )] + [
        LOGGER_NAME
    ]
