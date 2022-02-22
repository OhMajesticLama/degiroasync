from typing import Union, List
import functools
import logging
import pprint

from jsonloader import JSONclass

from ..core import LOGGER_NAME
from ..core import SessionCore
from ..core import Credentials
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
    countryName: str  # renamed from 'country' as it is country name
    hiqAbbr: str
    micCode: Union[str, None] = None


class ExchangeDictionary:
    """
    Usage:

    >>>> exchangedict = await ExchangeDictionary(session)
    >>>> exchangedict.exchange_by(hiqAbbr='EPA')
    {''}  # TODO

    """

    exchanges: List[Exchange]
    countries: List[Country]
    regions: List[Region]

    async def __new__(cls, session: SessionCore):
        self = super().__new__(cls)

        resp = await webapi.get_product_dictionary(session)
        product_dictionary = resp.json()
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
            self._exchanges[exchange['id']] = Exchange(exchange)

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
            hiqAbbr: Union[str, None] = None,
            micCode: Union[str, None] = None) -> Exchange:
        """Get Exchange by *either* name, hiqAbbr (e.g. EPA),
        micCode (e.g. XPAR)."""
        if sum(attr is not None for attr in (name, id, hiqAbbr, micCode)) != 1:
            raise AssertionError(
                "Exactly one of (name, id, hiqAbbr, micCode) "
                "must be not None.")
        if id is not None:
            return self._exchanges[id]
        for exc in self._exchanges.values():
            if name is not None and exc.name == name:
                return exc
            elif hiqAbbr is not None and exc.hiqAbbr == hiqAbbr:
                return exc
            elif micCode is not None and exc.micCode == micCode:
                return exc
        raise KeyError("No exchange found with search attributes: {}",
                       (name, id, hiqAbbr, micCode))

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
    exchange_dictionary: Union[ExchangeDictionary, None] = None


async def get_exchange_dictionary(session: Session) -> Session:
    """
    Populate session with exchange_dictionary.
    """
    session.exchange_dictionary = await ExchangeDictionary(session)
    return session


async def login(
        credentials: Credentials,
        session: Union[Session, None] = None) -> Session:
    """
    Authentify with Degiro API and populate basic information that'll be needed
    for further calls.

    `session` will be updated with required data for further connections.

    Strictly equivalent to:

    >>>> session = await degiroasync.webapi.login(credentials)
    >>>> await webapi.get_config(session)
    >>>> await webapi.get_client_info(session)

    If no `session` is provided, create one.
    """
    if session is None:
        session = Session()
    await webapi.login(credentials, session)
    await webapi.get_config(session)
    await webapi.get_client_info(session)
    await get_exchange_dictionary(session)
    return session


def check_session_exchange_dictionary(session: Session):
    """
    Check that session exchange dictionary has been populated.
    Raise AssertionError if not.
    """
    if session.exchange_dictionary is None:
        raise AssertionError(
            "session.exchange_dictionary is not set. "
            "Use api.login to build your session or call "
            "api.get_exchange_dictionary on it.")
