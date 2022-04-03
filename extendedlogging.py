"""Combine standard python logging with autologging/tracing."""
__author__ = 'Jan Feitsma'

import sys
import os
import time
import numpy
import logging
import logging.config
import autologging

# interface dealing
from logging import *
from autologging import *

# constants
ARRAY_SIZE_LIMIT = None # TODO? not implemented.
STRING_SIZE_LIMIT = None
DEFAULT_LOG_FILE = '/tmp/extendedlogging.txt'
BASIC_FORMAT = "%(levelname)s:%(name)s:%(message)s"
#EXTENDED_FORMATTER = ExtendedFormatter


def configure(**kwargs):
    # TODO: module __doc__; describe all options (or write out kwargs?)
    c = Configuration(**kwargs)
    c.apply()

def remove_all_handlers():
    handlers = logging.root.handlers[:]
    for handler in handlers:
        logging.root.removeHandler(handler)
        handler.close()



class Configuration():
    def __init__(self, **kwargs):
        self.name = ''
        self.console = True # stdout
        self.tracing = False
        self.reset = True
        self.filename = DEFAULT_LOG_FILE
        self.format_stdout = '%(levelname)-7s:%(funcName)s:%(message)s'
        self.format_file = '%(asctime)s:%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s'
        self.level_stdout = logging.INFO
        self.level_file = autologging.TRACE
        self.config = None
        # set overruled options, if any
        self.__dict__.update(kwargs)

    def clear(self):
        """Reset/clear logging configuration / handlers."""
        remove_all_handlers()
        # cleanup log file if existing
        if os.path.exists(self.filename) and self.tracing:
            os.remove(self.filename)

    def apply(self):
        """Apply the configuration."""
        # check if autologging has been disabled (typically via environment variable)
        if autologging.traced == autologging._traced_noop:
            self.tracing = False
        # reset?
        if self.reset:
            self.clear()
        # configure logging
        self.config = self.make_config_dict()
        logging.config.dictConfig(self.config)
        #print(self.config)
        return logging.getLogger(self.name)

    def make_config_dict(self):
        result = {
            'version': 1,
            'formatters': {},
            'handlers': {},
            'loggers': {
                self.name: {
                    'level': autologging.TRACE,
                    'handlers': []
                },
            },
        }
        if self.console:
            result['formatters']['logformatter'] = {'format': self.format_stdout}
            result['handlers']['loghandler'] = {'class': 'logging.StreamHandler', 'stream': sys.stdout, 'level': self.level_stdout, 'formatter': 'logformatter'}
            result['loggers'][self.name]['handlers'].append('loghandler')
        if self.tracing:
            result['formatters']['traceformatter'] = {'format': self.format_file}
            result['handlers']['tracehandler'] = {'class': 'logging.FileHandler', 'level': self.level_file, 'formatter': 'traceformatter', 'filename': self.filename}
            result['loggers'][self.name]['handlers'].append('tracehandler')
        return result



class ExtendedFormatter(logging.Formatter):
    def format(self, record):
        # step: compress arrays in self.args a-la numpy
        if ARRAY_SIZE_LIMIT != None:
            raise Exception('ARRAY_SIZE_LIMIT is not implemented')
            modified_args = []
            for idx in range(len(record.args)):
                arg = record.args[idx]
                convert_to_numpy_array = False
                if isinstance(arg, list) or isinstance(arg, tuple):
                    if len(arg) > ARRAY_SIZE_LIMIT:
                        convert_to_numpy_array = True
                if convert_to_numpy_array:
                    try:
                        modified_args.append(numpy.array(arg)) # just reuse numpy awesomeness (__repr__)
                    except:
                        modified_args.append(arg)
                else:
                    modified_args.append(arg)
            record.args = tuple(modified_args)
        # step: build the message
        result_string = super(ExtendedFormatter, self).format(record)
        # step: remove newlines, ensure every entry is on a single line (to make post-processing easier)
        result_string = result_string.replace('\n', '\\n')
        # step: apply string size limit
        if STRING_SIZE_LIMIT != None:
            if len(result_string) > STRING_SIZE_LIMIT:
                num_characters_truncated = len(result_string) - STRING_SIZE_LIMIT
                result_string = result_string[:STRING_SIZE_LIMIT] + '<{} characters truncated>'.format(num_characters_truncated)
        # done
        return result_string




def extendedConfig(**kwargs):
    """
    Extension of logging.basicConfig.

    Customize the formatter and set default level to TRACE.
    """
    if len(logging.root.handlers) == 0:
        filename = kwargs.get("filename")
        if filename:
            mode = kwargs.get("filemode", 'a')
            hdlr = logging.FileHandler(filename, mode)
        else:
            stream = kwargs.get("stream")
            hdlr = logging.StreamHandler(stream)
        fs = kwargs.get("format", BASIC_FORMAT)
        dfs = kwargs.get("datefmt", None)
        fmt = EXTENDED_FORMATTER(fs, dfs) # TODO: make configurable via kwargs?
        hdlr.setFormatter(fmt)
        logging.root.addHandler(hdlr)
        level = kwargs.get("level", autologging.TRACE)
        if level is not None:
            logging.root.setLevel(level)


