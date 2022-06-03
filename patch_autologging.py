"""Monkey patch on autologging, needed to support trace closures when exceptions occur.
Ideally, this is solved directy in autologging, see:
* https://github.com/mzipay/Autologging/issues/20   # the feature request
* https://github.com/janfeitsma/Autologging         # a working solution
"""
__author__ = 'Jan Feitsma'


import logging
import autologging
from inspect import isgenerator




def patched_call(self, function, args, keywords):
    def _handle(level, msg, args):
        # wrapper around logger.handle, reducing code duplication
        self._logger.handle(logging.LogRecord(
            self._logger.name,   # name
            level,               # level
            self._func_filename, # pathname
            self._func_lineno,   # lineno
            msg,                 # msg
            args,                # args
            None,                # exc_info
            func=function.__name__))

    _handle(autologging.TRACE, "CALL *%r **%r", (args, keywords))

    try:
        value = function(*args, **keywords)
    except Exception as e:
        _handle(logging.ERROR, "%s", str(e))
        _handle(autologging.TRACE, "RETURN ERROR", None)
        raise

    _handle(autologging.TRACE, "RETURN %r", (value,))

    return (autologging._GeneratorIteratorTracingProxy(function, value, self._logger)
            if isgenerator(value) else value)

class original_FunctionTracingProxy(autologging._FunctionTracingProxy):
    pass

class patched_FunctionTracingProxy(autologging._FunctionTracingProxy):
    __call__ = patched_call
    __call__.__doc__ = original_FunctionTracingProxy.__call__.__doc__

def enable():
    autologging._FunctionTracingProxy = patched_FunctionTracingProxy

def disable():
    autologging._FunctionTracingProxy = original_FunctionTracingProxy

