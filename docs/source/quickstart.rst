Quickstart with degiroasync
===========================

If you're here, you're probably looking for a way to directly interact
with DEGIRO's endpoints, with Python, in an asynchronous way.

We'll focus on higher level abstractions because they were built to limit
headaches about rebuilding and linking useful objects from the endpoint
returned data.

Should you 

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

    # Call your login function from your async code or just run it directly
    # in an asyncio (or your favorite async framework) eventloop:
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        my_login(username,
                 password)
    )


Get my Portfolio
++++++++++++++++

Here we assume you know how to log-in the endpoints and you have a valid Session
instance available. If you don't, check :ref:`cookbook_login`.

.. code-block:: python

    # TODO   



Find a product
++++++++++++++

TODO

Get price data
++++++++++++++

TODO
