#!/bin/bash

set -e

# main (fast) tests, both python3 and python2 supported
echo python3 tests/test_extendedlogging.py
python3 tests/test_extendedlogging.py
echo python2 tests/test_extendedlogging.py
python2 tests/test_extendedlogging.py

# this one is very slow due to HTML rendering tests; only python3 supported
echo python3 tests/test_ttviewer.py
python3 tests/test_ttviewer.py

# (useful during development: nosetests3 -vx)

