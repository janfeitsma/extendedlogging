"""Combine standard python logging with autologging/tracing."""
__author__ = 'Jan Feitsma'

import sys
import os
import time
import inspect
import logging
import logging.config
import autologging

# interface dealing
from logging import *
from autologging import *

# monkey patch to freeze the name, which enables consistent logging across multiple modules and over multiple reconfiguration runs
autologging._generate_logger_name = lambda *args, **kwargs: MAIN_LOGGER_NAME

# constants
DEFAULT_LOG_FILE = '/tmp/extendedlogging.txt'
BASIC_FORMAT = "%(levelname)s:%(name)s:%(message)s"
MAIN_LOGGER_NAME = ''
DEFAULT_NEWLINE_FOLDING = True
DEFAULT_TIMESTAMP_RESOLUTION = 6
DEFAULT_STRING_SIZE_LIMIT = 1000
DEFAULT_ARRAY_SIZE_LIMIT = 10
DEFAULT_ARRAY_TAIL_TRUNCATION = False # default inner


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
        self.timestamp_resolution = DEFAULT_TIMESTAMP_RESOLUTION
        self.level = autologging.TRACE
        self.fold_newlines = DEFAULT_NEWLINE_FOLDING
        self.string_size_limit = DEFAULT_STRING_SIZE_LIMIT
        self.array_size_limit = DEFAULT_ARRAY_SIZE_LIMIT
        self.array_tail_truncation = DEFAULT_ARRAY_TAIL_TRUNCATION
        # set overruled options, if any
        self.__dict__.update(kwargs)

    def get_formatter(self):
        # filter the arguments which are applicable
        kwargs = {k: getattr(self, k) for k in set.intersection(set(self.__dict__.keys()), set([m[0] for m in inspect.getmembers(TraceFormatter(''))]))}
        return TraceFormatter(self.format, **kwargs)

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
            continue
        # check if there is exactly one of the objects which has one of the parameters
        match = None
        for (p,o) in objects.items():
            if hasattr(o, k):
                if not match is None:
                    raise Exception('ambiguous option {} given'.format(k))
                match = objects[p]
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
        # bootstrap, connect the custom TraceFormatter
        if self.file_config.enabled:
            logging._handlers['tracehandler'].formatter = self.file_config.get_formatter()
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
        # file configuration
        cfg = self.file_config
        if cfg.enabled:
            result['formatters']['traceformatter'] = {'format': cfg.format} # NOTE: cannot yet use cfg.get_formatter()
            result['handlers']['tracehandler'] = {'class': 'logging.FileHandler', 'level': cfg.level, 'formatter': 'traceformatter', 'filename': cfg.filename}
            result['loggers'][self.name]['handlers'].append('tracehandler')
        return result


class RecursiveVisitor():
    """Helper, useful to fold long arrays."""
    def __init__(self, types, function):
        self.types = types
        self.function = function
    def apply(self, args):
        result = args
        t = type(args)
        if t in self.types:
            result = t([self.apply(arg) for arg in self.function(args)])
        return result


class TraceFormatter(logging.Formatter):
    """Custom formatter, intended for logging/tracing to file."""
    def __init__(self, fmt, **kwargs):
        logging.Formatter.__init__(self, fmt=fmt)
        self.fold_newlines = kwargs.get('fold_newlines', DEFAULT_NEWLINE_FOLDING)
        self.timestamp_resolution = int(kwargs.get('timestamp_resolution', DEFAULT_TIMESTAMP_RESOLUTION))
        self.string_size_limit = int(kwargs.get('string_size_limit', DEFAULT_STRING_SIZE_LIMIT))
        self.array_size_limit = int(kwargs.get('array_size_limit', DEFAULT_ARRAY_SIZE_LIMIT))
        self.array_tail_truncation = kwargs.get('array_tail_truncation', DEFAULT_ARRAY_TAIL_TRUNCATION)
        assert(self.timestamp_resolution >= 1)
        assert(self.timestamp_resolution <= 9)

    def format(self, record):
        # step: compress arrays in self.args a-la numpy
        if self.array_size_limit != None:
            def truncate_tail(arg):
                if len(arg) <= self.array_size_limit:
                    return arg
                return list(arg[:self.array_size_limit]) + ['...']
            def truncate_interior(arg):
                if len(arg) <= self.array_size_limit:
                    return arg
                n1 = int((1 + self.array_size_limit) / 2)
                n2 = n1 + len(arg) - self.array_size_limit
                arg1 = list(arg[:n1])
                arg2 = list(arg[n2:])
                return arg1 + ['...'] + arg2
            truncate_function = [truncate_interior, truncate_tail][self.array_tail_truncation]
            record.args = RecursiveVisitor(types=(tuple,list), function=truncate_function).apply(record.args)
        # step: build the message
        result_string = super(TraceFormatter, self).format(record)
        # step: remove newlines, ensure every entry is on a single line (to make post-processing easier)
        if self.fold_newlines:
            result_string = result_string.replace('\n', '\\n')
        # step: apply string size limit
        if self.string_size_limit != None:
            if len(result_string) > self.string_size_limit:
                num_characters_truncated = len(result_string) - self.string_size_limit
                last_part = '<{} characters truncated>'.format(num_characters_truncated)
                last_idx = self.string_size_limit - len(last_part)
                result_string = result_string[:last_idx] + last_part
        # done
        return result_string

    def formatTime(self, record, datefmt=None):
        if datefmt is not None:
            return super().formatTime(record, datefmt)
        ct = self.converter(record.created)
        t = time.strftime(self.default_time_format, ct)
        scale_factor = 10**self.timestamp_resolution
        fractional = int(scale_factor * (record.created % 1))
        t_format = '%s,%0' + str(self.timestamp_resolution) + 'd'
        s = t_format % (t, fractional)
        return s

