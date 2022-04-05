.. _cookbook_quickstart:

Quickstart with degiroasync
===========================

If you're here, you're probably looking for a way to directly interact
with DEGIRO's endpoints, with Python, in an asynchronous way.

We'll focus on higher level abstractions as they were built to limit
headaches about rebuilding and linking useful objects from the endpoint
returned information.


.. contents::
    :depth: 2


.. _cookbook_login:

Log in the platform
+++++++++++++++++++

`degiroasync` provides helpers to log in the endpoints. They will build a
`Session` instance for you, that will need to be passed argument to most of
the functions of this API.


.. code-block:: python

    # First we need to get your credentials. In this example we'll prompt the
    # user for it.
    #
    # Be extremely mindful how you store and provide them to your code should
    # you want to automate login: plaintext passwords and lax permissions
    # will bite you back, hard. Your program and its dependencies
    # files permissions (e.g. write access) should also be limited as much as
    # possible.
    import getpass  # So your password doesn't show on screen while you type it
    from typing import Optional

    from degiroasync import api
    from degiroasync.core import Credentials

    username: str = input('username: ')
    password: str = getpass.getpass()

    # Let's ask for a one_time_password, in case the account is MFA-enabled
    one_time_password: Optional[str] = getpass.getpass(
        'One Time Password (leave blank if not applicable): '
        ).strip()
    # If user left one_time_password_blank, we want to disable MFA login: set
    # it to None.
    one_time_password = one_time_password or None

    async def my_login(
            username: str,
            password: str,
            one_time_password: Optional[str]
            ) -> api.Session:

        # api.login and Credentials also support totp_secret parameter
        # should you want to let degiroasync generate the one time password
        # from your secret. Check the Credentials class documentation for
        # details.
        # Doing so would make automation at your script level easier (no
        # need for manual inputs at start-up nor a separate service that
        # provides one time passwords) but lower security.
        credentials: Credentials = Credentials(
            username,
            password,
            one_time_password=one_time_password
            )

        # Let's log in. Don't forget await.
        session: api.Session = await api.login(credentials)
        print("We're logged in!")
        return session

    # Call your login function from your async code or directly
    # in an asyncio (or your favorite async framework) eventloop:
    import asyncio
    session = asyncio.get_event_loop().run_until_complete(
        my_login(username,
                 password)
    )


Get my Portfolio
++++++++++++++++

Here we assume you know how to log-in the endpoints and you have a valid Session
instance available. If you don't, check :ref:`cookbook_login`.

.. code-block:: python

    # Assumption: you're logged in and have a session, if that's not the
    # case, check the login section of this quick start.
    from typing import Optional

    from degiroasync import api

    session: api.Session

    async def my_portfolio(session: api.Session):
        positions: Sequence[api.Position] = await api.get_portfolio(session)

        # A position object contains a product attribute with product
        # information and various attributes on the position returned
        # by the endpoint.
        # Most notably, it includes:
        #   - size: quantity of the product that are held.
        #   - price: price of the product, in the currency of the product
        #   - average_fx_rate: fx rate if not in account currency - else 0.
        #   - value: price * size.
        total_portfolio: float = 0.
        for pos in positions:
            print("Symbol {} Exchange {}: Value {} (price {} * size {})".format(
                pos.product.symbol,
                pos.product.exchange,
                pos.value,
                pos.price,
                pos.size,
            ))
            total_portfolio += pos.value
        print('Total portfolio: {}', total_portfolio)


    # Call your login function from your async code or directly
    # in an asyncio (or your favorite async framework) eventloop:
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        my_get_portfolio(session)
    )


Find a product
++++++++++++++

There are two main ways to get a Product:

- The `get_portfolio` from the example above.
- The `search_product` call that we'll show here.


.. code-block:: python

    from typing import Iterable

    from degiroasync import api

    # Assumption: you're logged in and have a session, if that's not the
    # case, check the login section of this quick start.
    session: api.Session

    async def my_search_product(session: api.Session):
        # For example, we are looking for a symbol on an exchange place,
        # Airbus (AIR) on Paris stock exchange (EPA).
        # search_product supports other search criteria, check out its 
        # documentation for more details.
        products: Sequence[api.Product] = await api.search_product(
            session,
            by_symbol="AIR",
            by_exchange="EPA",
            product_type_id=None,
            )

        print("{} products were founds".format(len(products)))
        # Notice how we have more than 1 product?
        # Setting product_type_id will return all found products: this will
        # include stocks but also any obligation, futures or anything else
        # the endpoint is aware of.
        # By default, search_product will restrict its search to shares.
        products: Sequence[api.Product] = await api.search_product(
            session,
            by_symbol="AIR",
            by_exchange="EPA",
            )

        print("{} products were founds".format(len(products)))
        # Now we should have just the one.

        print("Product: {}".format(products[0]))
        return products[0]


    # Call your login function from your async code or directly
    # in an asyncio (or your favorite async framework) eventloop:
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        my_search_product(session)
    )


Get price data
++++++++++++++

Now that we know how to get Product instances, we may want to get price data
related to those products.

.. code-block:: python

    from typing import Iterable

    from degiroasync import api
    from degiroasync import api

    # Assumption: you're logged in and have a session, if that's not the
    # case, check the login section of this quick start.
    session: api.Session

    async def my_price_analysis(session: api.Session):
        # For example, we are looking for a symbol on an exchange place,
        # Airbus (AIR) on Paris stock exchange (EPA).
        # search_product supports other search criteria, check out its 
        # documentation for more details.
        products: Sequence[api.Product] = await api.search_product(
            session,
            by_symbol="AIR",
            by_exchange="EPA",
            )

        print("{} products were founds".format(len(products)))
        assert len(products) == 1, "We shouldn't have more than one here."
        product = products[0]

        # Let's get today price data
        # The endpoint expects request to be framed in terms of resolution
        # and period - how old data do we request, rather than a timeframe.
        # Also note that there is no guarantee data will be available and
        # returned at the resolution requested for the requested period.
        # For example requesting PT1M (1 minute) resolution for P50YEAR
        # (50 years) resolution will not return the requested result but
        # whatever best quality is available.
        # Only trust the date and price fields of the PriceSeriesTime
        priceseries = await api.get_price_data(
            session,
            product=product,
            resolution=PRICE.RESOLUTION.PT1M,
            period=PRICE.PERIOD.P1DAY
        )

        print('Returned resolution: {}'.format(priceseries.resolution))
        # priceseries.date is in ISO format '2022-01-20T09:00:00'

        # Now we could feed the pricesseries.date and priceseries.price in
        # a pandas dataframe. In this example we'll just do an average.
        average = sum(priceseries.price) / len(priceseries.price)
        print('Since {}, price average for {} has been: {}'.format(
                priceseries.times,
                product.symbol,
                average,
        ))


    # Call your login function from your async code or directly
    # in an asyncio (or your favorite async framework) eventloop:
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        my_search_product(session)
    )
