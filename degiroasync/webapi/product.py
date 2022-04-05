import logging
from typing import Union, Any, List, Dict

import httpx

from ..core import SessionCore, URLs
from ..core import join_url
from ..core import check_session_config
from ..core.constants import LOGGER_NAME
from ..core.constants import PRICE
from ..core.constants import PRODUCT
from ..core.constants import TIMEOUT
from ..core.helpers import check_response


LOGGER = logging.getLogger(LOGGER_NAME)


async def get_portfolio(session: SessionCore) -> Dict[str, Any]:
    """
    Get portfolio web call.

    Example return:

        {'portfolio': {'isAdded': True,
         'lastUpdated': 1088,
         'name': 'portfolio',
         'value': [
            {'id': '8614787',
             'isAdded': True,
             'name': 'positionrow',
             'value': [
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
                  'value': {'EUR': -6716.901595272}},
                 {'isAdded': True,
                  'name': 'todayPlBase',
                  'value': {'EUR': -7300.0}},
                 {'isAdded': True,
                  'name': 'portfolioValueCorrection',
                  'value': 0},
                 {'isAdded': True,
                  'name': 'breakEvenPrice',
                  'value': 68.15},
                 {'isAdded': True,
                  'name': 'averageFxRate',
                  'value': 1},
                 {'isAdded': True,
                  'name': 'realizedProductPl',
                  'value': 98.098404728},
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
            },
                    ...
        },
         {'id': 'EUR',
          'isAdded': True,
          'name': 'positionrow',
          'value': [
            {'isAdded': True,
            'name': 'id',
            'value': 'EUR'},
            {'isAdded': True,
            'name': 'positionType',
            'value': 'CASH'},
            {'isAdded': True,
            'name': 'size',
            'value': -53676.25},
            {'isAdded': True,
            'name': 'price',
            'value': 1},
            {'isAdded': True,
            'name': 'value',
            'value': -53676.25},
            {'isAdded': True,
            'name': 'accruedInterest'},
            {'isAdded': True,
            'name': 'plBase',
            'value': {'EUR': 53676.2467863145}},
            {'isAdded': True,
            'name': 'todayPlBase',
            'value': {'EUR': 53676.2467863145}},
            {'isAdded': True,
            'name': 'portfolioValueCorrection',
            'value': 0},
            {'isAdded': True,
            'name': 'breakEvenPrice',
            'value': 0},
            {'isAdded': True,
            'name': 'averageFxRate',
            'value': 1},
            {'isAdded': True,
            'name': 'realizedProductPl',
            'value': 0},
            {'isAdded': True,
            'name': 'realizedFxPl',
            'value': 0},
            {'isAdded': True,
            'name': 'todayRealizedProductPl',
            'value': 0},
            {'isAdded': True,
            'name': 'todayRealizedFxPl',
            'value': 0}]
         },
         {'id': 'USD',
          'isAdded': True,
          'name': 'positionrow',
          'value': [{'isAdded': True,
          'name': 'id',
          'value': 'USD'},
         {'isAdded': True,
          'name': 'positionType',
          'value': 'CASH'},
         {'isAdded': True,
          'name': 'size',
          'value': 0.0},
         {'isAdded': True,
         'name': 'price',
         'value': 1},
         {'isAdded': True,
         'name': 'value',
         'value': 0.0},
         {'isAdded': True,
         'name': 'accruedInterest'},
         {'isAdded': True,
         'name': 'plBase',
         'value': {'EUR': -4.216892111}},
         {'isAdded': True,
         'name': 'todayPlBase',
         'value': {'EUR': 0.0}},
         {'isAdded': True,
         'name': 'portfolioValueCorrection',
         'value': 0},
         {'isAdded': True,
         'name': 'breakEvenPrice',
         'value': 0},
         {'isAdded': True,
         'name': 'averageFxRate',
         'value': 1},
         {'isAdded': True,
         'name': 'realizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'realizedFxPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedFxPl',
         'value': 0}]},
         {'id': 'PLN',
         'isAdded': True,
         'name': 'positionrow',
         'value': [{'isAdded': True,
         'name': 'id',
         'value': 'PLN'},
         {'isAdded': True,
         'name': 'positionType',
         'value': 'CASH'},
         {'isAdded': True,
         'name': 'size',
         'value': 0.0},
         {'isAdded': True,
         'name': 'price',
         'value': 1},
         {'isAdded': True,
         'name': 'value',
         'value': 0.0},
         {'isAdded': True,
         'name': 'accruedInterest'},
         {'isAdded': True,
         'name': 'plBase',
         'value': {'EUR': 1.8128205}},
         {'isAdded': True,
         'name': 'todayPlBase',
         'value': {'EUR': 0.0}},
         {'isAdded': True,
         'name': 'portfolioValueCorrection',
         'value': 0},
         {'isAdded': True,
         'name': 'breakEvenPrice',
         'value': 0},
         {'isAdded': True,
         'name': 'averageFxRate',
         'value': 1},
         {'isAdded': True,
         'name': 'realizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'realizedFxPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedFxPl',
         'value': 0}]},
         {'id': 'GBP',
         'isAdded': True,
         'name': 'positionrow',
         'value': [{'isAdded': True,
         'name': 'id',
         'value': 'GBP'},
         {'isAdded': True,
         'name': 'positionType',
         'value': 'CASH'},
         {'isAdded': True,
         'name': 'size',
         'value': 0.0},
         {'isAdded': True,
         'name': 'price',
         'value': 1},
         {'isAdded': True,
         'name': 'value',
         'value': 0.0},
         {'isAdded': True,
         'name': 'accruedInterest'},
         {'isAdded': True,
         'name': 'plBase',
         'value': {'EUR': 0.0}},
         {'isAdded': True,
         'name': 'todayPlBase',
         'value': {'EUR': 0.0}},
         {'isAdded': True,
         'name': 'portfolioValueCorrection',
         'value': 0},
         {'isAdded': True,
         'name': 'breakEvenPrice',
         'value': 0},
         {'isAdded': True,
         'name': 'averageFxRate',
         'value': 1},
         {'isAdded': True,
         'name': 'realizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'realizedFxPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedFxPl',
         'value': 0}]},
         {'id': 'FLATEX_EUR',
         'isAdded': True,
         'name': 'positionrow',
         'value': [{'isAdded': True,
         'name': 'id',
         'value': 'FLATEX_EUR'},
         {'isAdded': True,
         'name': 'positionType',
         'value': 'CASH'},
         {'isAdded': True,
         'name': 'size',
         'value': 0.0},
         {'isAdded': True,
         'name': 'price',
         'value': 1},
         {'isAdded': True,
         'name': 'value',
         'value': 0.0},
         {'isAdded': True,
         'name': 'accruedInterest'},
         {'isAdded': True,
         'name': 'plBase',
         'value': {'EUR': 0.0}},
         {'isAdded': True,
         'name': 'todayPlBase',
         'value': {'EUR': 0.0}},
         {'isAdded': True,
         'name': 'portfolioValueCorrection',
         'value': 0},
         {'isAdded': True,
         'name': 'breakEvenPrice',
         'value': 0},
         {'isAdded': True,
         'name': 'averageFxRate',
         'value': 1},
         {'isAdded': True,
         'name': 'realizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'realizedFxPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedFxPl',
         'value': 0}]},
         {'id': 'FLATEX_USD',
         'isAdded': True,
         'name': 'positionrow',
         'value': [{'isAdded': True,
         'name': 'id',
         'value': 'FLATEX_USD'},
         {'isAdded': True,
         'name': 'positionType',
         'value': 'CASH'},
         {'isAdded': True,
         'name': 'size',
         'value': 0.0},
         {'isAdded': True,
         'name': 'price',
         'value': 1},
         {'isAdded': True,
         'name': 'value',
         'value': 0.0},
         {'isAdded': True,
         'name': 'accruedInterest'},
         {'isAdded': True,
         'name': 'plBase',
         'value': {'EUR': 0}},
         {'isAdded': True,
         'name': 'todayPlBase',
         'value': {'EUR': 0}},
         {'isAdded': True,
         'name': 'portfolioValueCorrection',
         'value': 0},
         {'isAdded': True,
         'name': 'breakEvenPrice',
         'value': 0},
         {'isAdded': True,
         'name': 'averageFxRate',
         'value': 1},
         {'isAdded': True,
         'name': 'realizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'realizedFxPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedFxPl',
         'value': 0}]},
         {'id': 'FLATEX_PLN',
         'isAdded': True,
         'name': 'positionrow',
         'value': [{'isAdded': True,
         'name': 'id',
         'value': 'FLATEX_PLN'},
         {'isAdded': True,
         'name': 'positionType',
         'value': 'CASH'},
         {'isAdded': True,
         'name': 'size',
         'value': 0.0},
         {'isAdded': True,
         'name': 'price',
         'value': 1},
         {'isAdded': True,
         'name': 'value',
         'value': 0.0},
         {'isAdded': True,
         'name': 'accruedInterest'},
         {'isAdded': True,
         'name': 'plBase',
         'value': {'EUR': 0}},
         {'isAdded': True,
         'name': 'todayPlBase',
         'value': {'EUR': 0}},
         {'isAdded': True,
         'name': 'portfolioValueCorrection',
         'value': 0},
         {'isAdded': True,
         'name': 'breakEvenPrice',
         'value': 0},
         {'isAdded': True,
         'name': 'averageFxRate',
         'value': 1},
         {'isAdded': True,
         'name': 'realizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'realizedFxPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedFxPl',
         'value': 0}]},
         {'id': 'FLATEX_GBP',
         'isAdded': True,
         'name': 'positionrow',
         'value': [{'isAdded': True,
         'name': 'id',
         'value': 'FLATEX_GBP'},
         {'isAdded': True,
         'name': 'positionType',
         'value': 'CASH'},
         {'isAdded': True,
         'name': 'size',
         'value': 0.0},
         {'isAdded': True,
         'name': 'price',
         'value': 1},
         {'isAdded': True,
         'name': 'value',
         'value': 0.0},
         {'isAdded': True,
         'name': 'accruedInterest'},
         {'isAdded': True,
         'name': 'plBase',
         'value': {'EUR': 0}},
         {'isAdded': True,
         'name': 'todayPlBase',
         'value': {'EUR': 0}},
         {'isAdded': True,
         'name': 'portfolioValueCorrection',
         'value': 0},
         {'isAdded': True,
         'name': 'breakEvenPrice',
         'value': 0},
         {'isAdded': True,
         'name': 'averageFxRate',
         'value': 1},
         {'isAdded': True,
         'name': 'realizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'realizedFxPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedProductPl',
         'value': 0},
         {'isAdded': True,
         'name': 'todayRealizedFxPl',
         'value': 0}]}]},
         'totalPortfolio': {'isAdded': True,
         'lastUpdated': 22,
         'name': 'totalPortfolio',
         'value': [{'isAdded': True,
         'name': 'degiroCash',
         'value': -53676.25},
         {'isAdded': True,
         'name': 'flatexCash',
         'value': 0.0},
         {'isAdded': True,
         'name': 'totalCash',
         'value': -53676.25},
         {'isAdded': True,
         'name': 'totalDepositWithdrawal',
         'value': 63950.27},
         {'isAdded': True,
         'name': 'todayDepositWithdrawal',
         'value': 0},
         {'isAdded': True,
         'name': 'cashFundCompensationCurrency',
         'value': 'EUR'},
         {'isAdded': True,
         'name': 'cashFundCompensation',
         'value': 0},
         {'isAdded': True,
         'name': 'cashFundCompensationWithdrawn',
         'value': 28.79},
         {'isAdded': True,
         'name': 'cashFundCompensationPending',
         'value': 0},
         {'isAdded': True,
         'name': 'todayNonProductFees',
         'value': 0},
         {'isAdded': True,
         'name': 'totalNonProductFees',
         'value': -657.242202735},
         {'isAdded': True,
         'name': 'freeSpaceNew',
         'value': {'EUR': 35136.647442}},
         {'isAdded': True,
         'name': 'reportMargin',
         'value': 35136.647442},
         {'isAdded': True,
         'name': 'reportCreationTime',
         'value': '12:48:31'},
         {'isAdded': True,
         'name': 'reportPortfValue',
         'value': 149223.516559},
         {'isAdded': True,
         'name': 'reportCashBal',
         'value': -53676.2465},
         {'isAdded': True,
         'name': 'reportNetliq',
         'value': 95547.270059},
         {'isAdded': True,
         'name': 'reportOverallMargin',
         'value': 60410.622617},
         {'isAdded': True,
         'name': 'reportTotalLongVal',
         'value': 104456.461592},
         {'isAdded': True,
         'name': 'reportDeficit',
         'value': 50780.215092},
         {'isAdded': True,
         'name': 'marginCallStatus',
         'value': 'NO_MARGIN_CALL'},
         {'isAdded': True, 'name': 'marginCallDeadline'}]}
        }
    """
    return await get_trading_update(
        session,
        params={'portfolio': 0})


async def get_portfolio_total(session: SessionCore) -> Dict[str, Any]:
    return await get_trading_update(
        session,
        params={'totalPortfolio': 0})


async def get_products_info(
        session: SessionCore,
        products_ids: List[str]) -> Dict[str, Any]:
    """
    Get Product info Web API call.
    """
    if session.config.product_search_url is None:
        raise AssertionError("productSearchUrl is None:"
                             " have you called get_config?")

    LOGGER.debug('get_products_info products_ids| %s', products_ids)
    url = join_url(session.config.product_search_url,
                   'v5/products/info')
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            url,
            cookies=session.cookies,
            params={
                'intAccount': session.client.int_account,
                'sessionId': session.config.session_id
            },
            json=products_ids
        )
        try:
            check_response(response)
        except Exception:
            LOGGER.error('get_products_info response| %s', response)
            LOGGER.error('get_products_info url| %s', url)
            LOGGER.error('get_products_info products_ids| %s', products_ids)
            LOGGER.error('get_products_info products_ids| %s', products_ids)
            raise
        resp_json = response.json()
        LOGGER.debug('get_products_info|', resp_json)
    return resp_json


async def get_company_profile(
        session: SessionCore,
        isin: str) -> Dict[str, Any]:
    """
    Get company profile.
    """
    # should this url be taken from config as well?

    # Look for dgtbxdsservice in network logs for financial statements etc.
    # might have intraday data as well
    url = join_url(URLs.BASE, 'dgtbxdsservice/company-profile/v2', isin)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            url,
            cookies=session.cookies,
            params={
                'intAccount': session.client.int_account,
                'sessionId': session.config.session_id
            })
    check_response(response)
    LOGGER.debug(response.json())
    return response.json()


async def get_news_by_company(
        session: SessionCore,
        isin: str,
        limit: int = 10,
        languages: List[str] = ['en'],
        offset: int = 0
) -> Dict[str, Any]:
    """
    Get news for a company.
    """
    url = URLs.get_news_by_company_url(session)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(
            url,
            cookies=session.cookies,
            params={
                'isin': isin,
                'limit': limit,
                'languages': languages,
                'offset': offset,
                'intAccount': session.client.int_account,
                'sessionId': session.config.session_id
            })
    check_response(response)
    resp_json = response.json()
    LOGGER.debug("get_news_by_company| %s", resp_json)
    return resp_json


async def get_price_data(
        session: SessionCore,
        vwdId: str,
        vwdIdentifierType: str,
        resolution: PRICE.RESOLUTION = PRICE.RESOLUTION.PT1M,
        period: PRICE.PERIOD = PRICE.PERIOD.P1DAY,
        timezone: str = 'Europe/Paris',
        culture: str = 'fr-FR',
        data_type: PRICE.TYPE = PRICE.TYPE.PRICE
) -> Dict[str, Any]:
    """
    Get price data for a company.

    data_type = 'ohlc' provides access to 'Open', 'High', 'Low', 'Close' in
    that order for each period, instead of price data.

    vwdIdentifierType can be 'issueid' or 'vwdkey'

    Example returned JSON:
    {
        "requestid": "1",
        "start": "2022-01-20T00:00:00",
        "end": "2022-01-20T14:12:24",
        "resolution": "PT1M",
        "series": [
            {
                "expires": "2022-01-20T10:12:56+01:00",
                "data": {
                    "issueId": 360114899,
                    "companyId": 1001,
                    "name": "AIRBUS",
                    "identifier": "issueid:360114899",
                    "isin": "NL0000235190",
                    "alfa": "AIR15598",
                    "market": "XPAR",
                    "currency": "EUR",
                    "type": "AAN",
                    "quality": "REALTIME",
                    "lastPrice": 113.1,
                    "lastTime": "2022-01-21T14:12:24",
                    "absDiff": -2.62,
                    "relDiff": -0.02264,
                    "highPrice": 114.46,
                    "highTime": "2022-01-21T10:31:14",
                    "lowPrice": 112.78,
                    "lowTime": "2022-01-21T13:56:36",
                    "openPrice": 114.0,
                    "openTime": "2022-01-21T09:00:19",
                    "closePrice": 114.0,
                    "closeTime": "2022-01-21T09:00:19",
                    "cumulativeVolume": 857092.0,
                    "previousClosePrice": 115.72,
                    "previousCloseTime": "2022-01-20T17:35:03",
                    "tradingStartTime": "09:00:00",
                    "tradingEndTime": "17:40:00",
                    "tradingAddedTime": "00:10:00",
                    "lowPriceP1Y": 81.84,
                    "highPriceP1Y": 121.1,
                    "windowStart": "2022-01-20T00:00:00",
                    "windowEnd": "2022-01-20T10:11:22",
                    "windowFirst": "2022-01-20T09:00:00",
                    "windowLast": "2022-01-20T10:11:00",
                    "windowHighTime": "2022-01-20T10:11:00",
                    "windowHighPrice": 114.46,
                    "windowLowTime": "2022-01-20T10:16:00",
                    "windowLowPrice": 112.78,
                    "windowOpenTime": "2022-01-20T09:00:19",
                    "windowOpenPrice": 114.0,
                    "windowPreviousCloseTime": "2022-01-19T17:35:03",
                    "windowPreviousClosePrice": 115.72,
                    "windowTrend": -0.02264
                },
                "id": "issueid:360114899",
                "type": "object"
                "times": "2022-01-20T00:00:00",
                "expires": "2022-01-20T10:12:56+01:00",
                "data": [
                    [
                    540,
                    114.0
                    ],
                    [
                    541,
                    114.08
                    ],
                    [
                    542,
                    113.62
                    ],
                    [
                    543,
                    113.8
                    ],
                    ...
                    [
                    552,
                    113.7
                    ]],
            "id":"price:issueid:360114899",
            "type":"time"}]
        }
    """
    if vwdIdentifierType not in ('issueid', 'vwdkey'):
        raise ValueError("vwdIdentifierType must be 'issueid' or 'vwdkey'")

    check_session_config(session)
    url = URLs.get_price_data_url(session)
    LOGGER.debug('get_price_data url| %s', url)
    params = {
        'requestid': 1,
        'resolution': resolution,
        'culture': culture,
        'period': period,
        'series': f'price:{vwdIdentifierType}:{vwdId}',
        'format': 'json',
        'userToken': session.config.client_id
    }
    LOGGER.debug('get_price_data params| %s', params)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(url,
                                    cookies=session.cookies,
                                    params=params)
    check_response(response)
    resp_json = response.json()
    LOGGER.debug('get_price_data response| %s', resp_json)
    return resp_json


async def get_trading_update(
        session: SessionCore,
        params: Dict[str, int]
) -> Dict[str, Any]:
    """
    Common call to target {tradingUrl}/v5/update/{intAccount}

    This is used by other calls leveraging the same endpoint in webapi.

    Known params:
    - 'portfolio': 0
        Current portfolio information.
    - 'totalPortfolio': 0
        Aggregate values about portfolio.
    - 'orders': 0
        Current orders.
    - 'historicalOrders': 0
        Closed orders.
    - 'transactions': 0
        Executed transactions.
    """
    url = URLs.get_portfolio_url(session)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(url,
                                    cookies=session._cookies,
                                    params=params)

    check_response(response)
    LOGGER.debug("get_trading_update| %s", response.json())
    return response.json()


async def search_product(
        session: SessionCore,
        search_txt: str,
        product_type_id: Union[PRODUCT.TYPEID, None] = None,
        limit: int = 10,
        offset: int = 0) -> Dict[str, Any]:
    """
    Access `product_search` endpoint.

    Example JSON response:
    {
        "offset": 0,
        "products": [
            {
                "active": true,
                "buyOrderTypes": [
                    "LIMIT",
                    "MARKET",
                    "STOPLOSS",
                    "STOPLIMIT"
                ],
                "category": "B",
                "closePrice": 113.3,
                "closePriceDate": "2022-02-02",
                "contractSize": 1.0,
                "currency": "EUR",
                "exchangeId": "710",
                "feedQuality": "R",
                "feedQualitySecondary": "CX",
                "id": "96008",
                "isin": "NL0000235190",
                "name": "AIRBUS",
                "onlyEodPrices": false,
                "orderBookDepth": 0,
                "orderBookDepthSecondary": 0,
                "orderTimeTypes": [
                    "DAY",
                    "GTC"
                ],
                "productBitTypes": [],
                "productType": "STOCK",
                "productTypeId": 1,
                "qualitySwitchFree": false,
                "qualitySwitchFreeSecondary": false,
                "qualitySwitchable": false,
                "qualitySwitchableSecondary": false,
                "sellOrderTypes": [
                    "LIMIT",
                    "MARKET",
                    "STOPLOSS",
                    "STOPLIMIT"
                ],
                "strikePrice": -0.0001,
                "symbol": "AIR",
                "tradable": true,
                "vwdId": "360114899",
                "vwdIdSecondary": "955000256",
                "vwdIdentifierType": "issueid",
                "vwdIdentifierTypeSecondary": "issueid",
                "vwdModuleId": 1,
                "vwdModuleIdSecondary": 2
            }
        ]
    }

    """
    check_session_config(session)
    url = URLs.get_product_search_url(session, product_type_id)
    # TODO: Implement to target specialized URLs
    # Example query for stocks:
    # indexId=5&stockCountryId=886&requireTotal=true&offset=0&limit=100&sortColumns=name&sortTypes=asc&intAccount=123123123&sessionId=sdfasdfasdf
    params = dict(
        offset=offset,
        limit=limit,
        searchText=search_txt,
        intAccount=session.client.int_account,
        sessionId=session.config.session_id
    )
    if product_type_id is not None:
        params['productTypeId'] = product_type_id
    LOGGER.debug("webapi.search_product params| %s", params)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(url,
                                    cookies=session._cookies,
                                    params=params)
    check_response(response)
    LOGGER.debug("webapi.search_product response| %s", response.json())
    return response.json()


__all__ = [
    get_portfolio.__name__,
    get_portfolio_total.__name__,
    get_news_by_company.__name__,
    get_company_profile.__name__,
    get_price_data.__name__,
]
