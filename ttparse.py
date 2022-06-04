#!/usr/bin/env python

# parser for ttviewer

__author__ = 'Jan Feitsma'


# system imports
import re
import datetime

# own imports
import ttstore




class ParseError(Exception):
    pass


class LoggingParser():
    def __init__(self):
        # default format produced by extendedlogging:
        # '%(asctime)s:%(levelname)s:%(filename)s,%(lineno)d:%(funcName)s:%(message)s'
        # (TODO: what if process- and thread id are included? need a standardized format in extendedlogging to keep things somewhat simple here)
        # if levelname is TRACE, then message either starts with CALL or RETURN - these lines come in pairs
        # otherwise it is an single-line event (INFO, DEBUG etc.)
        self.config = {
            'CALL': (re.compile("(.+):TRACE:(.*):(.*):CALL (.+)"), 'B', self._handle_trace),
            'RETURN': (re.compile("(.+):TRACE:(.*):(.*):RETURN (.+)"), 'E', self._handle_trace)
        }
        self.config_fallback = (re.compile("([^A-Z]+):(.*):(.*):(.*):(.+)"), 'i', self._handle_event)

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
        ts, where, funcname, data = regexmatch
        timestamp = self.parse_timestamp(ts)
        kwargs = {'where': where}
        result = ttstore.TracingItem(timestamp, itemtype, funcname, data, **kwargs)
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
        ts, eventlevel, where, funcname, data = regexmatch
        timestamp = self.parse_timestamp(ts)
        # from documentation: The s property specifies the scope of the event. There are four scopes available global (g), process (p) and thread (t)
        kwargs = {'where': where, 'level': eventlevel, 'funcname': funcname, 'snapshot': None}
        result = ttstore.TracingItem(timestamp, itemtype, 'EVENT', data, **kwargs)
        return result

    def parse_timestamp(self, ts):
        '''Parse timestamp string to seconds since epoch.'''
        # TODO: speedup using https://pypi.org/project/ciso8601/1.0.1/
        try:
            w = ts.split()
            ts = w[0] + ' ' + w[1]
            format_str = "%Y-%m-%d %H:%M:%S,%f"
            dt = datetime.datetime.strptime(ts, format_str)
            timestamp = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
        except Exception as e:
            raise ParseError('failed to parse timestamp "{}" using format "{}"'.format(ts, format_str)) from None
        return timestamp


