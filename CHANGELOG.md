# CHANGELOG

All notable changes from **v0.22.0** to the current state.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) conventions.

---

---

## [1.0.0] - 2026-06-19

### Breaking Changes

**DEGIRO API Overhaul - Major Endpoint Updates**

DEGIRO updated their web API, requiring comprehensive changes. This is a **major version bump** due to breaking compatibility with v0.x, due to HTTP endpoint different returns. Some attributes in `degiroasync.api.Product` are now optional (`feed_quality`, `order_book_depth`, `quality_switchable`, `quality_switch_free`). 

#### API Endpoint Changes:
| Component | Change |
|-----------|--------|
| **Login** | Updated to meet new authentication requirements |
| **Product Search** | Migrated to `product_search_v2` endpoint (returns results grouped by ISIN) |
| **Product Info** | Updated to new endpoint structure |
| **Price Series** | Updated VWD charting API (requires new `callback` and `userToken` parameters) |
| **Company Profile** | Migrated to Refinitiv service endpoints |
| **Orders** | Adapted to new web API validation checks |

#### Other Breaking Changes:
- **Python Version**: Now requires **Python 3.13+** (previously supported 3.8+)
- **Build System**: Migrated from `setup.py` to `pyproject.toml`
- **Test Commands**: Updated to use explicit `tests/` path in README

---

### Bug Fixes

- Fixed `Index.info` population
- Fixed order placement to work with new API validation
- Fixed product search to handle new grouped-by-ISIN response format
- Fixed price data retrieval from updated VWD endpoints
- **Product Data** (2026-06-19):
  - Fixed `CFD` product type to use uppercase `'CFD'` (DEGIRO API now returns it in capital letters like other product types)
  - Made `feed_quality`, `order_book_depth`, `quality_switchable`, and `quality_switch_free` fields optional in `Leveraged` product to match API changes
- **Price Series** (2026-06-19):
  - Added resolution validation in `get_price_series()` - DEGIRO API doesn't support `PT1M` resolution with `P1MONTH` period
  - Added `ignore_resolution` parameter to bypass validation when needed
  - Updated integration tests to use `PT1D` instead of `PT1M` for monthly periods
- Fixed deprecated `LOGGER.warn()` to `LOGGER.warning()` in `get_price_data()`
- **Python 3.14 Compatibility** (2026-06-19):
  - Upgraded `jsonloader` dependency to `>=0.9.2, <1.0`
  - Replaced deprecated `asyncio.iscoroutinefunction()` with `inspect.iscoroutinefunction()` in `lru_cache_timed`

---


---

## [0.22.0] - 2026-02-11

*Starting point for this changelog*
