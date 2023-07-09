# DegiroAsync

## Documentation

Check out the [online documentation](https://ohmajesticlama.github.io/degiroasync/index.html).

## Introduction

This project aims to provide an *unofficial* API for Degiro platform that works
asynchronously.


## Precautions

This software is *not* an official Degiro product, nor is it backed by a company.
It is made available to the users community, as a community effort to enable
automation of Degiro trading platform.


## A word on stability

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
the LICENSE file in this repository.

It is the responsability of the user of this library to ensure its
product is running and passing adequate tests before running it in production.


## Install

### User installation
```bash
# Create a virtualenv or equivalent, depending on your tool of choice
python3 -m virtualenv venv
. venv/bin/activate
# Install from PyPI
python3 -m pip install degiroasync
```

### Developer installation
```bash
# Clone this repository
git clone https://github.com/OhMajesticLama/degiroasync

# Create a virtualenv or equivalent, depending on your tool of choice
python3 -m virtualenv venv
. venv/bin/activate

# Install with dev dependencies
python3 -m pip install -e .[dev]

# To setup the project's git hooks:
git config --local core.hooksPath hooks
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
```bash
DEGIROASYNC_INTEGRATION  # must be set to 1 for integration tests to run
DEGIRO_USERNAME  # Your Degiro username
DEGIRO_PASSWORD  # Your Degiro password
DEGIRO_TOTP_SECRET  # Only if the account requires 2FA for login

```

```bash
# Unittests only
DEGIROASYNC_INTEGRATION=0 pytest --color yes
# Integration tests & Unittests
DEGIROASYNC_INTEGRATION=1 pytest --color yes
```

### Tests coverage
For example, leverage `coverage` module:
```bash
pytest --cov
```

Please note that the coverage will or will not include integration tests if
`DEGIROASYNC_INTEGRATION` environment variable is set to 1 or not set.


## Other Python Degiro Libraries

Check-out those other Python Degiro libraries - non-exhaustive list - to assess
which best fits your needs:
- https://github.com/Chavithra/degiro-connector
- https://github.com/lolokraus/DegiroAPI
- https://github.com/bramton/degiro
