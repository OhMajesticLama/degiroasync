# DegiroAsync

*Current version is _ALPHA_ level of quality:
- essential features are still missing, see supported features section.
- external interface is still subject to change, even between minor version.
- while there are integration tests, coverage of integration and unit tests is
 not yet where we need it to be

DO NOT USE IN PRODUCTION. You have been warned.
 While in this _ALPHA_ state, code is made available in case it can be of use
 to other API developers.*


This project aims to provide an *unofficial* API for Degiro platform that works
asynchronously.

There are currently several Degiro Python Libraries that were
active in 2021, check the _Other Python Degiro Libraries_ section for a 
non-exhaustive list and assess which one best fits your needs.


## Supported Features

As its name suggests, `degiroasync` provides an asynchronous Python API to 
Degiro trading interface.

This module provides 2 APIs:
- `degiroasync.api`: API that abstracts Degiro HTTP API to be closer to
  a consummer needs. This is the recommended choice to start.
- `degiroasync.webapi`: API close to actual Degiro HTTP API. 
  This provides maximum flexibility and data availability, at the cost of
  accessibility.

`degiroasync.api` is built on top of `degiroasync.webapi`: the two of them
can work together should you want to leverage higher/lower level calls in a
specific cases of your program.


| Feature             | degiroasync.api    | degiroasync.webapi |
|---------------------|--------------------|--------------------|
| login               | :white_check_mark: | :white_check_mark: |
| login w/ 2FA        | :white_check_mark: | :white_check_mark: |
| get_config          | :white_check_mark: | :white_check_mark: |
| get_client_info     | :white_check_mark: | :white_check_mark: |
| get_portfolio       | :white_check_mark: | :white_check_mark: |
| get_products_info   | :white_check_mark: | :white_check_mark: |
| get_news_by_company |                    | :white_check_mark: |
| get_price_data      |                    | :white_check_mark: |
| get_company_profile |                    | :white_check_mark: |


## Precautions

This software is *not* an official Degiro product, nor is it backed by a company.
It is made available to the users community, as a community effort to enable
automation of Degiro trading platform.


## A word on stability
*degiroasync should be considered alpha quality.*

Until this project's version reaches 1.0, the API should be considered unstable
and may break even with minor versions increments.

Additionally, keep in mind that Degiro does *not* provide an official API
for its platform, that means there is no commitment their API should
be stable: it can change at any time and break this library. Potentially
incurring losses depending on how you use that library.


### Reminder from the License

```
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
The license under which this software is made available can be found in
the License file in this repository.

It is the responsability of the user of this library to ensure its 
product is running and passing adequate tests before running it in production.


## Install

### User installation
```
# This is an ALPHA
python3 -m virtualenv venv
. venv/bin/activate
pip3 install .
```

### Deveveloper installation
```
python3 -m virtualenv venv
. venv/bin/activate
pip3 install -e .[dev]
```

## Run Tests
Even if you don't intend to develop for degiroasync,
it is recommended to run tests, before using the library and regularly,
to catch a broken environment or a change in Degiro API as early
as possible and reduce the risk of a failure in your production environment.


Running integration tests will require environment set-up. As Degiro does not
provide a test environment, those tests will be run directly on an actual 
account.

This comes with limitations and concerns:
- Placing and cancelling *order* integration test will not be implemented to
  avoid ending up placing unwanted orders in the event automation fails to
  remove them.
- You must be particularly careful to minimize risk to leak your credentials.
  e.g. write a helper script that will ask to input your password to run 
  integration tests and run the tests to avoid leaking your credentials in 
  global environment.
  Access to your script folder must be restricted, as well as write rights to
  any file that is imported - that includes this module and all its dependencies.
  We recommend installing it in a Virtual Environment or a container and restrict
  access to it.

The following environment variables must be set:
```
DEGIROASYNC_INTEGRATION  # must be set to 1 for integration tests to run
DEGIRO_USERNAME  # Your Degiro username
DEGIRO_PASSWORD  # Your Degiro password
DEGIRO_TOTP_SECRET  # Only if the account requires 2FA for login

```

```
# Unittests only
DEGIROASYNC_INTEGRATION=0 nose2 -t .
# Integration tests & Unittests
DEGIROASYNC_INTEGRATION=1 nose2 -t .
```

### Tests coverage
For example, leverage `coverage` module:
`nose2 -t . -C --coverage-report html` 


## Other Python Degiro Libraries

Check-out those other Python Degiro libraries (updated in 2021) to assess which
best fits your needs:
- https://github.com/Chavithra/degiro-connector
- https://github.com/lolokraus/DegiroAPI
- https://github.com/bramton/degiro 

