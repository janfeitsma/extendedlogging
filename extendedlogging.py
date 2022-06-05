"""Combine standard python logging with autologging/tracing.

The module deals the API's of both logging and autologging.
It also implements some extra features:
    * microsecond timestamp resolution
    * ensure tracing files have one logging/tracing entry per line
    * limit tracing line- and array sizes, to prevent excessive file growth

To enable/configure: just call configure(). It accepts the following options:
    tracing                # boolean, default disabled, when enabled logging (and tracing) is written to file
    filename               # trace file name, default {DEFAULT_LOG_FILE}
    timestamp_resolution   # tracing timestamp resolution, default {DEFAULT_TIMESTAMP_RESOLUTION}
    fold_newlines          # tracing newline folding, default {DEFAULT_NEWLINE_FOLDING}
    string_size_limit      # tracing string size limit, default {DEFAULT_STRING_SIZE_LIMIT}
    array_size_limit       # tracing array size limit, default {DEFAULT_ARRAY_SIZE_LIMIT}
    array_tail_truncation  # tracing array truncation option, to cut off arrays at the end instead of interior, default {DEFAULT_ARRAY_TAIL_TRUNCATION}
    error_handling         # tracing error handler, default {DEFAULT_ERROR_HANDLING}
    thread_names           # tracing option to also log thread id/name on each line, default {DEFAULT_LOG_THREAD_NAMES}
    process_names          # tracing option to also log process name on each line, default {DEFAULT_LOG_PROCESS_NAMES}
    write_format_header    # tracing option to write a header line with the format used, default {DEFAULT_WRITE_FORMAT_HEADER}
    *_format               # logging format to use
    *_level                # logging level to use
Where applicable (as marked with *_), the option prefix must be either 'file' or 'console'.
"""
__author__ = 'Jan Feitsma'

import sys
import os
import time
import inspect
import logging
import logging.config
import autologging
import patch_autologging

# interface dealing
from logging import *
from autologging import *

# monkey patch to freeze the name, which enables consistent logging across multiple modules and over multiple reconfiguration runs
autologging._generate_logger_name = lambda *args, **kwargs: MAIN_LOGGER_NAME


# constants
DEFAULT_LOG_FILE = '/tmp/extendedlogging.log'
MAIN_LOGGER_NAME = ''
DEFAULT_NEWLINE_FOLDING = True
DEFAULT_TIMESTAMP_RESOLUTION = 6
DEFAULT_STRING_SIZE_LIMIT = 1000
DEFAULT_ARRAY_SIZE_LIMIT = 10
DEFAULT_ARRAY_TAIL_TRUNCATION = False # default inner, not tail
DEFAULT_ERROR_HANDLING = True # log ERROR in tracing upon exception
DEFAULT_LOG_PROCESS_NAMES = False
DEFAULT_LOG_THREAD_NAMES = False
# TODO: try to auto-detect multiprocessing/threading, although that seems too complicated and error prone
DEFAULT_WRITE_FORMAT_HEADER = False



# main configure function, see doc above
def configure(**kwargs):
    c = MixedConfiguration(**kwargs)
    return c.apply()
configure.__doc__ = __doc__.format(**vars()) # trick to fill in the default values, although this might not be how __doc__ was intended


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
        self.format = '%(asctime)s:%(levelname)s:%(filename)s,%(lineno)d:%(funcName)s:%(message)s'
        self.timestamp_resolution = DEFAULT_TIMESTAMP_RESOLUTION
        self.level = autologging.TRACE
        self.fold_newlines = DEFAULT_NEWLINE_FOLDING
        self.string_size_limit = DEFAULT_STRING_SIZE_LIMIT
        self.array_size_limit = DEFAULT_ARRAY_SIZE_LIMIT
        self.array_tail_truncation = DEFAULT_ARRAY_TAIL_TRUNCATION
        self.error_handling = DEFAULT_ERROR_HANDLING
        self.process_names = DEFAULT_LOG_PROCESS_NAMES
        self.thread_names = DEFAULT_LOG_THREAD_NAMES
        self.write_format_header = DEFAULT_WRITE_FORMAT_HEADER
        # set overruled options, if any
        self.__dict__.update(kwargs)

    def apply(self):
        if self.thread_names and not 'threadName' in self.format:
            self.format = self.format.replace('%(levelname)s', '%(levelname)s:%(threadName)s')
        if self.process_names and not 'processName' in self.format:
            self.format = self.format.replace('%(levelname)s', '%(levelname)s:%(processName)s')
        patch_autologging.set_error_handling(self.error_handling)

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
        # optionally tweak autologging
        self.file_config.apply()
        # bootstrap, connect the custom TraceFormatter
        if self.file_config.enabled:
            logging._handlers['tracehandler'].formatter = self.file_config.get_formatter()
            # write tracing format header line
            if self.file_config.write_format_header or self.file_config.thread_names or self.file_config.process_names:
                logging._handlers['tracehandler'].stream.write('# format: ' + self.file_config.format + '\n')
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

