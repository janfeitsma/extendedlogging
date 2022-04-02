# Introduction

This module *extendedlogging* provides a layer on top of *autologging* which extends standard python *logging*.

The main purpose is to improve usability: make it *simpler* to configure tracing to file in combination with console logging.

Some extra features:
* tracing lines cannot be split over multiple lines - newlines in strings are logged as '\n'
* tracing lines have a configurable maximum size


# Demo

TODO

For more demo's, see the test suite.

# Testing, dependencies

* to install dependencies, run: 
  * `pip install -r REQUIREMENTS.pip`
* to run all tests locally, run: `nosetests3 -vsx --nologcapture` 
  * options `-s` and `--nologcapture` are needed to avoid conflicts with standard unittest stdout/logging
  * options `-v` and `-x` can be omitted - these are a matter of taste


