"""Monkey patch on autologging, needed to support trace closures when exceptions occur.
Ideally, this is solved directy in autologging, see:
* https://github.com/mzipay/Autologging/issues/20   # the feature request
* https://github.com/janfeitsma/Autologging         # a working solution
"""
__author__ = 'Jan Feitsma'


import logging
import autologging
from inspect import isgenerator


ERROR_HANDLING_ENABLED = True


class original_FunctionTracingProxy(autologging._FunctionTracingProxy):
    pass

class patched_FunctionTracingProxy(autologging._FunctionTracingProxy):
    def __call__(self, function, args, keywords):
        def _handle(level, msg, args):
            # try to make pretty function name (python version >= 3.3)
            fname = function.__name
            if hasattr(function, '__qualname__'):
                fname = function.__qualname__
            # wrapper around logger.handle, reducing code duplication
            self._logger.handle(logging.LogRecord(
                self._logger.name,   # name
                level,               # level
                self._func_filename, # pathname
                self._func_lineno,   # lineno
                msg,                 # msg
                args,                # args
                None,                # exc_info
                func=fname))

        _handle(autologging.TRACE, "CALL *%r **%r", (args, keywords))

        if ERROR_HANDLING_ENABLED:
            try:
                value = function(*args, **keywords)
            except Exception as e:
                # tag the exception, to prevent it being logged at each level in the stack
                if not hasattr(e, 'logged') or not e.logged:
                    _handle(logging.ERROR, "%s", str(e))
                e.logged = True
                _handle(autologging.TRACE, "RETURN ERROR", None)
                raise
        else:
            value = function(*args, **keywords)

        _handle(autologging.TRACE, "RETURN %r", (value,))

        return (autologging._GeneratorIteratorTracingProxy(function, value, self._logger)
                if isgenerator(value) else value)

    __call__.__doc__ = original_FunctionTracingProxy.__call__.__doc__



# apply the patch always, to enable runtime (re)configuration
autologging._FunctionTracingProxy = patched_FunctionTracingProxy

def set_error_handling(b):
    """Enable or disable the error handling feature."""
    global ERROR_HANDLING_ENABLED
    ERROR_HANDLING_ENABLED = b

