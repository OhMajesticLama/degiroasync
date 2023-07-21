from typing import Union, List, Dict, Any
from typing import Set
import sys
from typing import Optional
import functools
import logging
import pprint
import dataclasses
import copy

from jsonloader import JSONclass

from ..core import LOGGER_NAME
from ..core import SessionCore
from ..core import Config
from ..core import PAClient
from ..core import Credentials
from ..core import camelcase_dict_to_snake
from ..core import BadCredentialsError
from ..core import lru_cache_timed
from ..core import PRODUCT
from .. import webapi


LOGGER = logging.getLogger(LOGGER_NAME)


@JSONclass(annotations=True, annotations_type=True)
class Region:
    id: int
    name: str


@JSONclass(annotations=True, annotations_type=True)
class Country:
    id: str
    name: str  # ISO 3166-1 alpha-2 country codename
    region: 'Region'


@JSONclass(annotations=True, annotations_type=True)
class Exchange:
    id: str
    name: str
    city: Optional[str] = None
    code: Optional[str] = None
    country_name: str  # renamed from 'country' as it is country name
    hiq_abbr: str
    mic_code: Optional[str] = None


@JSONclass(annotations=True, annotations_type=True)
class Index:
    # Example of JSON
    # {
    #   "data": {
    #     "4824940": {
    #       "id": "4824940",
    #       "name": "CAC 40",
    #       "isin": "FR0003500008",
    #       "symbol": "CAC INDEX",
    #       "contractSize": 1,
    #       "productType": "INDEX",
    #       "productTypeId": 180,
    #       "tradable": false,
    #       "category": "H",
    #       "currency": "EUR",
    #       "active": true,
    #       "exchangeId": "710",
    #       "onlyEodPrices": false,
    #       "orderTimeTypes": [],
    #       "buyOrderTypes": [],
    #       "sellOrderTypes": [],
    #       "productBitTypes": [],
    #       "closePrice": 7384.91,
    #       "closePriceDate": "2023-07-20",
    #       "feedQuality": "R",
    #       "orderBookDepth": 0,
    #       "vwdIdentifierType": "issueid",
    #       "vwdId": "360015511",
    #       "qualitySwitchable": false,
    #       "qualitySwitchFree": false,
    #       "vwdModuleId": 1
    #     }
    #   }
    # }
    @JSONclass(annotations=True)
    class Info:
        id: str
        isin: str
        name: str
        symbol: str
        product_type: PRODUCT.TYPE
        product_type_id: PRODUCT.TYPEID
        currency: str
        exchange_id: str
        exchange: Exchange
        close_price: Optional[float] = None
        close_price_date: Optional[str] = None
        vwd_id: Optional[str] = None
        vwd_identifier_type: Optional[str] = None

    id: str
    name: str
    product_id: Optional[str] = None
    info: Optional[Info] = None

    async def get_info(self, session: 'Session') -> Optional[Info]:
        """
        Populate and return Index.Info. Provides more information about Index,
        such as isin, symbol, exchange ...

        If no Info is available for this Index, returns None.

        In the event you need to instantiate all or most indices, you should
        use :class:`~degiroasync.api.Session.populate_indices_info` that
        will reduce web API calls.

        See :class:`~degiroasync.api.Index.Info` for details.
        """
        if self.info is None and self.product_id is None:
            return None
        elif self.info is None and self.product_id is not None:
            ind_id = self.product_id
            resp = await webapi.get_products_info(
                    session,
                    products_ids=[ind_id],
                    )
            # Info needs to be populated.
            LOGGER.debug("Index.get_info| %s", resp)
            self.info = self._dict2info(session, resp['data'][ind_id])
        return self.info

    @classmethod
    def _dict2info(
            cls: type,
            session: 'Session',
            web_response: Dict[str, Any]) -> Info:
        info_dict = camelcase_dict_to_snake(web_response)
        info_dict['product_type_id'] = PRODUCT.TYPEID(
                info_dict['product_type_id'])
        info_dict['product_type'] = PRODUCT.TYPE(
                info_dict['product_type'])
        info_dict['exchange'] = session.dictionary.exchange_by(
                id=info_dict['exchange_id'])
        return cls.Info(info_dict)


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
    indices: List[Index]

    _exchanges: Dict[str, Any]

    async def __new__(cls, session: SessionCore):
        self = super().__new__(cls)

        product_dictionary = await webapi.get_product_dictionary(session)
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

        self._indices = {}
        self._indices_name = {}
        for index in product_dictionary['indices']:
            index = camelcase_dict_to_snake(index)
            index['id'] = str(index['id'])
            if 'product_id' in index:
                index['product_id'] = str(index['product_id'])
            self._indices[index['id']] = Index(index)
            self._indices_name[index['name'].lower()] = Index(index)

        return self

    @property
    def exchanges(self):
        return [v for v in self._exchanges.values()]

    @property
    def countries(self):
        return [c for c in self._countries_name.values()]

    @property
    def regions(self):
        return [r for r in self._regions.values()]

    @property
    def indices(self):
        return [i for i in self._indices.values()]

    @functools.lru_cache(32)
    def index_by(
            self,
            name: Optional[str] = None,
            id: Optional[int] = None,
            ) -> Index:
        if name is not None and id is not None:
            raise AssertionError("Exactly one of (name, id) must be not None.")
        if name is not None:
            return self._indices_name[name.lower()]
        if id is not None:
            return self._indices[id]

    @functools.lru_cache(32)
    def exchange_by(
            self,
            *,
            name: Optional[str] = None,
            id: Optional[int] = None,
            hiq_abbr: Optional[str] = None,
            mic_code: Optional[str] = None) -> Exchange:
        """
        Get Exchange by *either* name, hiqAbbr (e.g. EPA),
        micCode (e.g. XPAR).
        """
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
            if name not in self._countries_name:
                raise KeyError(
                        "{} not found. List of available countries: {}".format(
                            name,
                            [c for c in self._countries_name]
                            ))
            return self._countries_name[name]
        if id is not None:
            return self._countries_id[id]

    async def populate_indices_info(self, session: 'Session'):
        """
        Populate info attribute for all indices.
        """
        # Get ids
        ids = [
                i.product_id
                for i in self._indices.values()
                if i.product_id
                ]
        # Query data
        resp = await webapi.get_products_info(session, ids)
        # Populate info parameter for all indices
        for index in self._indices.values():
            if index.product_id:
                index.info = Index._dict2info(
                        session,
                        resp['data'][index.product_id]
                        )


class Session(SessionCore):
    config: Config
    client: PAClient
    dictionary: ExchangeDictionary

    def __init__(self,
                 session_core: SessionCore,
                 dictionary: ExchangeDictionary):
        """
        Use `api.login` to get a populated Session instance.

        Build a `Session` instance from a `SessionCore` and an
        ExchangeDictionary.
        """
        LOGGER.debug("Session.__init__: session_core %s", session_core)
        if session_core.config is None:
            raise AssertionError("session_core.config not set.")
        if session_core.client is None:
            raise AssertionError("session_core.client not set.")
        self.__dict__.update(copy.copy(session_core.__dict__))
        self.config = session_core.config
        self.client = session_core.client
        self.dictionary = dictionary

    @property
    def exchange_dictionary(self):
        print(
            'Session.exchange_dictionary is deprecated. Please use '
            'Session.dictionary instead.', file=sys.stderr)
        return self.dictionary


async def get_dictionary(session: Session) -> ExchangeDictionary:
    """
    Return a new ExchangeDictionary from Session.
    """
    return await ExchangeDictionary(session)


#: Singleton to store hash of failed attempts credentials.
_LOGIN_FAILURE_HASH: Set[str] = set()

#: Minimum time before new login attempt is allowed with bad credentials (s).
#: Default = 3 hours
_LOGIN_FAILURE_MINTIME = 60 * 60 * 3


@lru_cache_timed(maxsize=32, seconds=_LOGIN_FAILURE_MINTIME)
def _should_fail(credentials: Credentials) -> bool:
    if credentials in _LOGIN_FAILURE_HASH:
        # We can discard failure as it will be remembered by this function
        # cache.
        _LOGIN_FAILURE_HASH.discard(credentials)
        return True
    else:
        return False


async def login(
        credentials: Credentials,
        session: Union[Session, None] = None,
        /,
        safeguard_incorrect_credentials: bool = True
        ) -> Session:
    """
    Authentify with Degiro API and populate basic information that'll be needed
    for further calls.

    `session` will be updated with required data for further connections.

    Roughly equivalent to:

    .. code-block:: python

        session = await degiroasync.webapi.login(credentials)
        await webapi.get_config(session)
        await webapi.get_client_info(session)

    If no `session` is provided, create one.

    Parameters
    ----------

    credentials:
        Credentials with which we attempt login.

    session:
        If provided, populate with API config. If not a new Session will be
        created.

    safeguard_incorrect_credentials:
        Defaults to True. If `True`, store credentials hash in case of failure
        and do not allow new login attempts with same hash. This allows to
        avoid blocking account in case of inaccurate credentials.

    Raises
    ------

    BadCredentialsError:
        If login with those credentials returned a bad credentials response.

    ResponseError:
        Other response errors.

    """
    if safeguard_incorrect_credentials:
        if credentials in _LOGIN_FAILURE_HASH:
            LOGGER.error("Bad credentials, abort login.")
            raise BadCredentialsError(
                    "Abort. Login previously failed with these credentials."
                    " Provide `safeguard_incorrect_credentials=False` "
                    "if you want to override this behavior.")

    try:
        session_core = await webapi.login(credentials)
    except BadCredentialsError:
        LOGGER.error("Bad credentials, abort login.")
        _LOGIN_FAILURE_HASH.add(credentials)
        raise

    await webapi.get_config(session_core)
    await webapi.get_client_info(session_core)
    dictionary = await get_dictionary(session_core)
    if session is not None:
        session.__dict__.update(copy.deepcopy(session_core))
        session.dictionary = dictionary
    else:
        return Session(session_core, dictionary)
    return session


def check_session_dictionary(session: Session):
    """
    Check that session exchange dictionary has been populated.
    Raise AssertionError if not.
    """
    if session.dictionary is None:
        raise AssertionError(
            "session.dictionary is not set. "
            "Use api.login to build your session or call ")
