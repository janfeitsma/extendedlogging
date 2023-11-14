#!/usr/bin/env python

# parser for ttviewer

__author__ = 'Jan Feitsma'


# system imports
import re
import datetime
from collections import defaultdict

# own imports
import ttvlib.ttstore as ttstore


# default format produced by extendedlogging:
FORMAT_SPEC_SEPARATOR = ':'
DEFAULT_FORMAT_SPEC = FORMAT_SPEC_SEPARATOR.join(['%(asctime)s', '%(levelname)s', '%(filename)s,%(lineno)d', '%(funcName)s', '%(message)s'])
TIME_FORMAT_STR_PYTHON = '%Y-%m-%d %H:%M:%S,%f'
TIME_FORMAT_STR_SPDLOG = '%Y-%m-%dT%H:%M:%S.%f'


class ParseError(Exception):
    pass
class FormatError(Exception):
    pass


class PythonLoggingParser():
    def __init__(self):
        self.configure()

    def configure(self, format_spec=DEFAULT_FORMAT_SPEC):
        field_to_regex = defaultdict(lambda: '([^' + FORMAT_SPEC_SEPARATOR + ']+)')
        field_to_regex['%(asctime)s'] = '([^A-Z]+)' # can have ':' separators
        field_to_type = {}
        field_to_type['%(asctime)s'] = 'timestamp'
        field_to_type['%(processName)s'] = 'pid'
        field_to_type['%(threadName)s'] = 'tid'
        field_to_type['%(levelname)s'] = 'eventlevel'
        field_to_type['%(filename)s,%(lineno)d'] = 'where'
        field_to_type['%(funcName)s'] = 'funcname'
        field_to_type['%(message)s'] = 'data'
        format_fields = format_spec.split(FORMAT_SPEC_SEPARATOR)
        self.tid_in_log = '%(threadName)s' in format_fields
        self.pid_in_log = '%(processName)s' in format_fields
        class FieldIndexMap(object):
            pass
        self.field_to_idx = FieldIndexMap()
        # if levelname is TRACE, then message either starts with CALL or RETURN - these lines come in pairs
        # otherwise it is an single-line event (INFO, DEBUG etc.), parse via fallback
        regex_trace_start_parts = []
        regex_trace_end_parts = []
        regex_fallback_parts = []
        for idx, f in enumerate(format_fields):
            if f not in field_to_type:
                raise FormatError('unrecognized format field specification: "{}"'.format(f))
            setattr(self.field_to_idx, field_to_type[f], idx)
            regex_fallback_parts.append(field_to_regex[f])
            if f == '%(message)s': # special trace start/end parsing
                regex_trace_start_parts.append('CALL ' + field_to_regex[f])
                regex_trace_end_parts.append('RETURN ' + field_to_regex[f])
            else:
                regex_trace_start_parts.append(field_to_regex[f])
                regex_trace_end_parts.append(field_to_regex[f])
        self.config = {
            'CALL': (re.compile(FORMAT_SPEC_SEPARATOR.join(regex_trace_start_parts)), 'B', self._handle_trace),
            'RETURN': (re.compile(FORMAT_SPEC_SEPARATOR.join(regex_trace_end_parts)), 'E', self._handle_trace)
        }
        self.config_fallback = (re.compile(FORMAT_SPEC_SEPARATOR.join(regex_fallback_parts)), 'i', self._handle_event)

    def _select(self, line):
        '''Peek into line, figure out which regex to apply.'''
        for (k,v) in self.config.items():
            if k in line:
                return v
        return self.config_fallback

    def __call__(self, line):
        '''Parse given line and return TracingItem object.'''
        regex, itemtype, handle = self._select(line)
        match = regex.search(line)
        if not match:
            raise ParseError('regex match failure: ' + str(regex))
        return handle(itemtype, match.groups())

    def _handle_trace(self, itemtype, regexmatch):
        ts = regexmatch[self.field_to_idx.timestamp]
        where = regexmatch[self.field_to_idx.where]
        funcname = regexmatch[self.field_to_idx.funcname]
        data = regexmatch[self.field_to_idx.data]
        timestamp = self.parse_timestamp(ts)
        kwargs = {'where': where}
        result = ttstore.TracingItem(timestamp, itemtype, funcname, data, **kwargs)
        # pid/tid
        if self.pid_in_log:
            result.pid = regexmatch[self.field_to_idx.pid]
        if self.tid_in_log:
            result.tid = regexmatch[self.field_to_idx.tid]
        # do some extra work in case the io labeling option is set
        if itemtype == 'B' and ttstore.INCLUDE_IO_IN_NAME:
            s = data
            # tracing input data is always logged in the following form: *(...) **{...}
            # this is because the autologging wrapper cannot conform to some fixed function signature
            # reverse-parsing seems too complex/costly/messy, so let's just remove some characters and hope the result is readable
            for c in '*(){},':
                s = s.replace(c, '')
            result.sdata = s
        return result

    def _handle_event(self, itemtype, regexmatch):
        ts = regexmatch[self.field_to_idx.timestamp]
        eventlevel = regexmatch[self.field_to_idx.eventlevel]
        where = regexmatch[self.field_to_idx.where]
        funcname = regexmatch[self.field_to_idx.funcname]
        data = regexmatch[self.field_to_idx.data]
        timestamp = self.parse_timestamp(ts)
        # from documentation: The s property specifies the scope of the event. There are four scopes available global (g), process (p) and thread (t)
        kwargs = {'where': where, 'level': eventlevel, 'funcname': funcname, 'snapshot': None}
        result = ttstore.TracingItem(timestamp, itemtype, 'EVENT', data, **kwargs)
        # pid/tid
        if self.pid_in_log:
            result.pid = regexmatch[self.field_to_idx.pid]
        if self.tid_in_log:
            result.tid = regexmatch[self.field_to_idx.tid]
        return result

    def parse_timestamp(self, ts):
        '''Parse timestamp string to seconds since epoch.'''
        # TODO: speedup using https://pypi.org/project/ciso8601/1.0.1/
        format_str = TIME_FORMAT_STR_PYTHON
        try:
            w = ts.split()
            ts = w[0] + ' ' + w[1]
            dt = datetime.datetime.strptime(ts, format_str)
            timestamp = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
        except Exception as e:
            raise ParseError('failed to parse timestamp "{}" using format "{}"'.format(ts, format_str)) from None
        return timestamp


class SpdlogParser():
    def __init__(self):
        pass

    def __call__(self, line):
        '''Parse given line and return TracingItem object.'''
        # example line:
        # [2023-11-09T20:52:05.180381] [34/34/FalconsVelocityControl] [info] [tick.cpp:24,tick] end {"tick":1,"error_value":0,"duration":0.000698,"output":{"velocity":{"x":0.0519729964,"y":0.0315867141,"rz":0.075}}}
        words = line.split(' ')
        if len(words) < 5:
            # TODO error handling
            return
        etype = words[2].lstrip('[').rstrip(']')
        if etype != 'trace':
            # TODO support also events
            return
        ts = words[0].lstrip('[').rstrip(']')
        timestamp = self.parse_timestamp(ts)
        pid, tid, component = words[1].lstrip('[').rstrip(']').split('/')
        where, funcname = words[3].lstrip('[').rstrip(']').split(',')
        filename, linenumber = where.split(':')
        data = ' '.join(words[4:])
        if data.startswith('>'):
            itemtype = 'B'
        elif data.startswith('<'):
            itemtype = 'E'
        else:
            raise ParseError('trace data should start with either > or < character')
        kwargs = {'where': where}
        result = ttstore.TracingItem(timestamp, itemtype, funcname, data, **kwargs)
        result.pid = pid
        result.tid = tid
        # TODO INCLUDE_IO_IN_NAME?
        return result

    def parse_timestamp(self, ts):
        '''Parse timestamp string to seconds since epoch.'''
        # TODO: speedup using https://pypi.org/project/ciso8601/1.0.1/
        format_str = TIME_FORMAT_STR_SPDLOG
        try:
            dt = datetime.datetime.strptime(ts, format_str)
            timestamp = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
        except Exception as e:
            raise ParseError('failed to parse timestamp "{}" using format "{}"'.format(ts, format_str)) from None
        return timestamp
