# DegiroAsync

This project aims to provide an *unofficial* API for Degiro platform that works
asynchronously.

## Install

```
python3 -m virtualenv venv
. venv/bin/activate
# Dev install, for non-dev, remove '-e'
pip3 install -e .
```

## Run Tests
Running integration tests will require environment set-up. As Degiro does not
provide a test environment, those tests will be run directly on an actual 
account.

This comes with limitations and concerns:
- Placing *order* integration test will not be implemented to avoid ending up placing
unwanted orders in the event automation fails to remove them.
- You must be particularly careful to minimize risk to leak your credentials.
  e.g. write a helper script that will ask to input your password to run integration tests and run the tests to avoid leaking your credentials in global environment.
  Access to your script folder must be restricted, as well as write rights to
  any file that is imported - that includes this module and all its dependencies.
  We recommend installing it in a Virtual Environment or a container and restrict
  access to it.

The following environment variables must be set:
```
DEGIROASYNC_INTEGRATION  # must be set to 1
DEGIRO_USERNAME
DEGIRO_PASSWORD
DEGIRO_TOTP_SECRET  # Only if the account requires 2FA for login

```


```
nose2 -t .
```
