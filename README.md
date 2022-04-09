# Introduction

This module *extendedlogging* provides a layer on top of *autologging* which extends standard python *logging*.

The main purpose is to improve usability: make it *simpler* to configure tracing to file in combination with console logging.

Some extra features:
* tracing lines are by default never split over multiple lines - newlines in strings are logged as '\n'
* tracing timestamps are in microsecond resolution instead of milliseconds
* tracing lines have a configurable maximum size

# Demo

Given the following code:
```rb
# demo.py
```

With the given code, the logging to stdout looks something like:
```
INFO   :f:hi!
WARNING:<module>:done
```

With the given code, the tracing to file looks something like:
```
2022-04-09 14:06:00,855471:TRACE:demo.py,6:root.__init__:CALL *('some_argument',) **{}
2022-04-09 14:06:00,855649:TRACE:demo.py,9:root.f:CALL *() **{}
2022-04-09 14:06:00,855793:INFO:demo.py,10:root.f:hi!
2022-04-09 14:06:00,855901:TRACE:demo.py,9:root.f:RETURN None
2022-04-09 14:06:00,856035:DEBUG:demo.py,8:root.__init__:__init__ done
2022-04-09 14:06:00,856065:TRACE:demo.py,6:root.__init__:RETURN None
2022-04-09 14:06:00,856093:TRACE:demo.py,12:root.g:CALL *() **{}
2022-04-09 14:06:00,856115:TRACE:demo.py,12:root.g:RETURN 3
2022-04-09 14:06:00,856161:WARNING:demo.py,21:root.<module>:done
```

For more demo's, see the code snippets in the test suite.

# Testing, dependencies

* to install dependencies, run: 
  * `pip install -r REQUIREMENTS.pip`
* to run all tests locally, run: `python tests.py` 


