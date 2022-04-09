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

# monkey patch to freeze the name, which enables consistent logging across multiple modules and over multiple reconfiguration runs
autologging._generate_logger_name = lambda *args, **kwargs: MAIN_LOGGER_NAME

# constants
ARRAY_SIZE_LIMIT = None # TODO? not implemented.
STRING_SIZE_LIMIT = None
DEFAULT_LOG_FILE = '/tmp/extendedlogging.txt'
BASIC_FORMAT = "%(levelname)s:%(name)s:%(message)s"
MAIN_LOGGER_NAME = ''
#EXTENDED_FORMATTER = ExtendedFormatter



def configure(**kwargs):
    # TODO: module __doc__; describe all options (or write out kwargs?)
    c = MixedConfiguration(**kwargs)
    c.apply()


def remove_all_handlers():
    """Blunt reset: remove all handlers registered in logging module."""
    handlers = logging.root.handlers[:]
    for handler in handlers:
        logging.root.removeHandler(handler)
        handler.close()


class ConsoleConfiguration():
    """Configuration for logging to console."""
    def __init__(self, **kwargs):
        self.enabled = True
        self.stream = sys.stdout
        self.format = '%(levelname)-7s:%(funcName)s:%(message)s'
        self.level = logging.INFO
        # set overruled options, if any
        self.__dict__.update(kwargs)


class FileConfiguration():
    """Configuration for logging/tracing to file."""
    def __init__(self, **kwargs):
        self.enabled = True
        self.filename = DEFAULT_LOG_FILE
        self.format = '%(asctime)s:%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s'
        self.level = autologging.TRACE
        # set overruled options, if any
        self.__dict__.update(kwargs)

    def clear_file(self):
        if os.path.exists(self.filename) and self.enabled:
            os.remove(self.filename)


def distribute_attributes(kv, objects):
    """Utility to distribute attributes over objects, dynamically figuring out which one is providing the option."""
    for (k,v) in kv.items():
        # check for a prefix
        match = False
        for (p,o) in objects.items():
            if k.startswith(p):
                setattr(o, k.replace(p, ''), v)
                match = True
                break
        if match:
            break
        # check if there is exactly one of the objects which has one of the parameters
        match = None
        for (p,o) in objects.items():
            if hasattr(o, k):
                if not match is None:
                    raise Exception('ambiguous option {} given'.format(k))
                match = o
        if match is None:
            raise Exception('non-existing option {} given'.format(k))
        setattr(match, k, v)


class MixedConfiguration():
    """Combine ConsoleConfiguration with FileConfiguration and configure the logging module."""
    def __init__(self, **kwargs):
        self.name = MAIN_LOGGER_NAME
        self.console_config = ConsoleConfiguration(enabled=True) # stdout
        self.file_config = FileConfiguration(enabled=False)
        self.config_dict = None
        self.file_config.enabled = kwargs.pop('tracing', False)
        distribute_attributes(kwargs, {'console_': self.console_config, 'file_': self.file_config})

    def clear(self):
        """Reset/clear logging configuration / handlers."""
        remove_all_handlers()
        # cleanup log file if existing
        self.file_config.clear_file()

    def apply(self):
        """Apply the configuration."""
        # check if autologging has been disabled (typically via environment variable)
        if autologging.traced == autologging._traced_noop:
            self.file_config.enabled = False
        # reset
        self.clear()
        # configure logging
        self.config_dict = self.make_config_dict()
        logging.config.dictConfig(self.config_dict)
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
        # console configuration
        cfg = self.console_config
        if cfg.enabled:
            result['formatters']['logformatter'] = {'format': cfg.format}
            result['handlers']['loghandler'] = {'class': 'logging.StreamHandler', 'stream': cfg.stream, 'level': cfg.level, 'formatter': 'logformatter'}
            result['loggers'][self.name]['handlers'].append('loghandler')
        cfg = self.file_config
        if cfg.enabled:
            result['formatters']['traceformatter'] = {'format': cfg.format}
            result['handlers']['tracehandler'] = {'class': 'logging.FileHandler', 'level': cfg.level, 'formatter': 'traceformatter', 'filename': cfg.filename}
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


