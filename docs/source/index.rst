.. include:: symbols.txt

degiroasync's documentation
===========================

Table of Contents
+++++++++++++++++

.. toctree::
    :maxdepth: 1
    :caption: Contents:

    quickstart
    api
    core
    webapi

Documentation details for public API members can be found in the
:ref:`genindex`

A word on stability
+++++++++++++++++++
*degiroasync should be considered ALPHA quality.*

Until this project's version reaches 1.0, the API should be considered unstable
and may break even with minor versions increments.

Additionally, keep in mind that Degiro does *not* provide an official API
for its platform, that means there is no commitment their API should
be stable: it can change at any time and break this library. Potentially
incurring losses depending on how you use that library.


Quickstart
++++++++++

Also available in the Table of Contents section, check-out the
:ref:`cookbook_quickstart`.


degiroasync
+++++++++++

.. autosummary::
    degiroasync.api
    degiroasync.webapi
    degiroasync.core

Supported Features
++++++++++++++++++

As its name suggests, `degiroasync` provides an asynchronous Python API to
Degiro trading interface.

This module provides 2 APIs:
- `degiroasync.api`: API that abstracts Degiro HTTP API to be closer to
a consumer needs. This is the recommended choice to start.
- `degiroasync.webapi`: API close to actual Degiro HTTP API.
This provides maximum flexibility and data availability, at the cost of
less checks and more legwork to be used for higher-level logic.

`degiroasync.api` is built on top of `degiroasync.webapi`: it should be easy
to fall back to `webapi` should the need arise. For example, there is currently
no call for `confirm_order` in `degiroasync.api` as the `webapi` one is fairly
straightforward.


.. table:: Features coverage between degiraosync.api and degiroasync.webapi
    :widths: auto

    +---------------------+--------------------+--------------------+
    |Feature              | degiroasync.api    | degiroasync.webapi |
    +=====================+====================+====================+
    | login               | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | login w/ 2FA        | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_config          | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_client_info     | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_portfolio       | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_portfolio_total | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_products_info   | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_price_data      | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | search_product      | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_exchange        | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_news_by_company |                    | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_company_profile |                    | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | check_order         | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | confirm_order       |                    | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_orders          | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+
    | get_orders_history  | |checkmarklight|   | |checkmarklight|   |
    +---------------------+--------------------+--------------------+

