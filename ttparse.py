#!/usr/bin/env python

# parser for ttviewer

__author__ = 'Jan Feitsma'


# system imports
import re
import datetime

# own imports
import ttstore




class LoggingParser():
    def __init__(self):
        # default format produced by extendedlogging:
        # '%(asctime)s:%(levelname)s:%(filename)s,%(lineno)d:%(funcName)s:%(message)s'
        # (TODO: what if process- and thread id are included? need a standardized format in extendedlogging to keep things somewhat simple here)
        # if levelname is TRACE, then message either starts with CALL or RETURN - these lines come in pairs
        # otherwise it is an single-line event (INFO, DEBUG etc.)
        self.config = {
            'CALL': (re.compile("(.+):TRACE:(.*):(.*):CALL (.+)"), 'B'),
            'RETURN': (re.compile("(.+):TRACE:(.*):(.*):RETURN (.+)"), 'E')
        }

    def _select(self, line):
        '''Peek into line, figure out which regex to apply.'''
        for (k,v) in self.config.items():
            if k in line:
                return v
        raise Exception('_select failed on line: ' + line)

    def __call__(self, line):
        '''Parse given line and return TracingItem object.'''
        regex, itemtype = self._select(line)
        match = regex.search(line)
        if not match:
            raise Exception('parse error on line: ' + line)
        ts, where, funcname, io = match.groups()
        timestamp = self.parse_timestamp(ts)
        kwargs = {'where': where, 'io': io}
        result = ttstore.TracingItem(timestamp, itemtype, funcname, **kwargs)
        return result

    def parse_timestamp(self, ts):
        '''Parse timestamp string to seconds since epoch.'''
        # TODO: speedup using https://pypi.org/project/ciso8601/1.0.1/
        w = ts.split()
        ts = w[0] + ' ' + w[1]
        format_str = "%Y-%m-%d %H:%M:%S,%f"
        dt = datetime.datetime.strptime(ts, format_str)
        timestamp = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
        return timestamp


