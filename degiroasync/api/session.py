from typing import Union, List, Dict, Any
import functools
import logging
import pprint
import copy

from jsonloader import JSONclass

from ..core import LOGGER_NAME
from ..core import SessionCore
from ..core import Config
from ..core import PAClient
from ..core import Credentials
from ..core import camelcase_dict_to_snake
from .. import webapi


LOGGER = logging.getLogger(LOGGER_NAME)


@JSONclass(annotations=True, annotations_type=True)
class Region:
    id: int
    name: str


@JSONclass(annotations=True, annotations_type=True)
class Country:
    id: str
    name: str  # 2 letters country codename
    region: 'Region'


@JSONclass(annotations=True, annotations_type=True)
class Exchange:
    id: str
    name: str
    city: Union[str, None] = None
    code: Union[str, None] = None
    country_name: str  # renamed from 'country' as it is country name
    hiq_abbr: str
    mic_code: Union[str, None] = None


class ExchangeDictionary:
    """
    Usage:

    .. code-block:: python

        exchangedict = await ExchangeDictionary(session)
        exchangedict.exchange_by(hiqAbbr='EPA')

    """

    exchanges: List[Exchange]
    countries: List[Country]
    regions: List[Region]

    _exchanges: Dict[str, Any]

    async def __new__(cls, session: SessionCore):
        self = super().__new__(cls)

        product_dictionary = await webapi.get_product_dictionary(session)
        #product_dictionary = resp.json()
        LOGGER.debug("api.ExchangeDictionary| %s",
                     pprint.pformat(product_dictionary))
        self._regions = {p['id']: Region(p)
                         for p in product_dictionary['regions']}

        self._countries_id = {}
        self._countries_name = {}
        for country in product_dictionary['countries']:
            # Replace region dict by object.
            region = self._regions[country['region']]
            country['region'] = region
            country['id'] = str(country['id'])
            # Register country
            country_inst = Country(country)
            self._countries_id[country['id']] = country_inst
            self._countries_name[country['name']] = country_inst

        self._exchanges = {}
        for exchange in product_dictionary['exchanges']:
            # Some APIs call return id in int, others in str. Fix here as all
            # str.
            exchange['id'] = str(exchange['id'])
            # Replace region dict by object.
            exchange['countryName'] = exchange['country']
            del exchange['country']

            # Register country
            self._exchanges[exchange['id']] = Exchange(
                    camelcase_dict_to_snake(exchange))

        return self

    @property
    def exchanges(self):
        return self._exchanges.values()

    @property
    def countries(self):
        return self._countries_name.values()

    @property
    def regions(self):
        return self._regions.values()

    @functools.lru_cache(32)
    def exchange_by(
            self,
            *,
            name: Union[str, None] = None,
            id: Union[int, None] = None,
            hiq_abbr: Union[str, None] = None,
            mic_code: Union[str, None] = None) -> Exchange:
        """Get Exchange by *either* name, hiqAbbr (e.g. EPA),
        micCode (e.g. XPAR)."""
        if sum(attr is not None for attr in (name,
                                             id,
                                             hiq_abbr,
                                             mic_code)) != 1:
            raise AssertionError(
                "Exactly one of (name, id, hiqAbbr, micCode) "
                "must be not None.")
        if id is not None:
            return self._exchanges[id]
        for exc in self._exchanges.values():
            if name is not None and exc.name == name:
                return exc
            elif hiq_abbr is not None and exc.hiq_abbr == hiq_abbr:
                return exc
            elif mic_code is not None and exc.mic_code == mic_code:
                return exc
        raise KeyError("No exchange found with search attributes: {}",
                       (name, id, hiq_abbr, mic_code))

    def country_by(
            self,
            *,
            name: Union[str, None] = None,
            id: Union[int, None] = None) -> Country:
        if sum(attr is not None for attr in (name, id)) != 1:
            raise AssertionError(
                "Exactly one of (name, id) must be not None.")
        if name is not None:
            return self._countries_name[name]
        if id is not None:
            return self._countries_id[id]


class Session(SessionCore):
    config: Config
    client: PAClient
    exchange_dictionary: ExchangeDictionary

    def __init__(self,
                 session_core: SessionCore,
                 exchange_dictionary: ExchangeDictionary):
        """
        Use `api.login` to get a populated Session instance.

        Build a `Session` instance from a `SessionCore` and an
        exchange_dictionary.
        """
        LOGGER.debug("Session.__init__: session_core %s", session_core)
        if session_core.config is None:
            raise AssertionError("session_core.config not set.")
        if session_core.client is None:
            raise AssertionError("session_core.client not set.")
        self.__dict__.update(copy.copy(session_core.__dict__))
        self.config = session_core.config
        self.client = session_core.client
        self.exchange_dictionary = exchange_dictionary


async def get_exchange_dictionary(session: Session) -> ExchangeDictionary:
    """
    Populate session with exchange_dictionary.
    """
    return await ExchangeDictionary(session)


async def login(
        credentials: Credentials,
        session: Union[Session, None] = None) -> Session:
    """
    Authentify with Degiro API and populate basic information that'll be needed
    for further calls.

    `session` will be updated with required data for further connections.

    Strictly equivalent to:

    .. code-block:: python

        session = await degiroasync.webapi.login(credentials)
        await webapi.get_config(session)
        await webapi.get_client_info(session)

    If no `session` is provided, create one.
    """
    session_core = await webapi.login(credentials)
    await webapi.get_config(session_core)
    await webapi.get_client_info(session_core)
    exchange_dictionary = await get_exchange_dictionary(session_core)
    if session is not None:
        session.__dict__.update(copy.deepcopy(session_core))
        session.exchange_dictionary = exchange_dictionary
    else:
        return Session(session_core, exchange_dictionary)
    return session


def check_session_exchange_dictionary(session: Session):
    """
    Check that session exchange dictionary has been populated.
    Raise AssertionError if not.
    """
    if session.exchange_dictionary is None:
        raise AssertionError(
            "session.exchange_dictionary is not set. "
            "Use api.login to build your session or call ")
