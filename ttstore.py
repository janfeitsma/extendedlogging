#!/usr/bin/env python

# datastore for ttviewer
# documentation: https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/preview#
# (retrieved via: https://github.com/catapult-project/catapult/blob/main/tracing/README.md)

import datetime
import json
from collections import defaultdict


# the HTML viewer requires magic microsecond scaling
MAGIC_MICROSECOND_TIMESTAMP_SCALING = 1e6

# throw an error if the amount of data is getting large
# (alternative could be to just cut off and warn?)
STORE_LIMIT = 1e7

# format of timestamp to display in detailed info pane of browser
READABLE_TIMESTAMP_FORMAT = "%Y-%m-%d,%H:%M:%S.%f"

# module option to include i/o in name
INCLUDE_IO_IN_NAME = False
CUTOFF_IO_IN_NAME = 100



class StackError(Exception): # could occur when not logging different thread id's
    pass
class ItemTypeError(Exception):
    pass
class OutOfMemoryError(Exception):
    pass


class TracingJsonStore:
    """This data store holds trace items and can write them as json for the catapult traceviewer.
    
    Start- and end items form a duration; they come in pairs.

    Items must arrive in order, i.e. increasing timestamp and properly nested."""
    def __init__(self, outputfilename):
        self.items = []
        self.stack = defaultdict(lambda: [])
        self.last_timestamp = 0
        self.size = 0
        self.limit = STORE_LIMIT
        self.output = open(outputfilename, 'w')

    def __del__(self):
        # TODO: autoclose to ensure json file integrity, prevent browser complaints
        self.output.write(']\n')
        self.output.close()

    def add(self, item):
        # check timestamp order integrity
        # TODO: what if timestamps are equal? with millisecond resolution this is not uncommon
        #assert item.timestamp > self.last_timestamp, 'timestamp out of order: got {}, last was {}'.format(item.timestamp, self.last_timestamp)
        self.last_timestamp = item.timestamp
        # handle item(s) and check stack integrity
        if item.type == 'B':
            self.handle_start_item(item)
        elif item.type == 'E':
            self.handle_end_item(item)
        elif item.type == 'i':
            self.handle_event_item(item)
        else:
            raise ItemTypeError('unrecognized trace item type: {}'.format(item.type))

    def handle_event_item(self, item):
        self.write_item(item)

    def handle_start_item(self, item):
        key = (item.pid, item.tid)
        self.stack[key].append(item)

    def handle_end_item(self, item):
        key = (item.pid, item.tid)
        start_item = self.stack[key].pop()
        if item.name != start_item.name:
            thread_detail = ''
            if item.tid:
                thread_detail = ' at thread {}'.format(item.tid)
            raise StackError('item pop inconsistency{}: popped item is "{}:{}", expected name is "{}"'.format(thread_detail, item.args['where'], item.name, start_item.name))
        # set a reference so the rendered label ('name') can be adapted
        start_item.end = item
        # write
        self.write_item(start_item)
        self.write_item(item)

    def write_item(self, item):
        # file header?
        if self.size == 0:
            self.output.write('[\n')
        # json item separator
        if self.size > 0:
            self.output.write(',')
        # json item line
        self.output.write(json.dumps(item.dict()))
        self.output.write('\n')
        # file end is handled at closure
        self.size += 1
        if self.size > self.limit:
            raise OutOfMemoryError('store limit exceeded: {}'.format(self.limit))



class TracingItem:
    def __init__(self, timestamp, itemtype, name, data, **kwargs):
        '''A TracingItem represents a json line.'''
        self.timestamp = timestamp # float
        self.name = name
        self.pid = None
        self.tid = None
        self.type = itemtype
        self.data = data # string, raw (for detail pane)
        self.sdata = data # string, pretty (for io labeling)
        self.args = {}
        for (k, v) in kwargs.items():
            self.args[k] = v

    def dict(self):
        '''Return dict for json conversion.'''
        t = self.timestamp
        ts = int(MAGIC_MICROSECOND_TIMESTAMP_SCALING * self.timestamp)
        name = self.name
        d = {'name': name, 'ts': ts, 'ph': self.type, 'pid': self.pid, 'tid': self.tid, 'args': self.args}
        if self.type == 'B':
            if INCLUDE_IO_IN_NAME:
                end_item = self.end
                def cutoff(s):
                    if len(s) > CUTOFF_IO_IN_NAME:
                        return s[:CUTOFF_IO_IN_NAME] + '...'
                    return s
                name += ' ' + cutoff(self.sdata) # inputs
                if self.end.sdata != 'None':
                    name += '-> ' + cutoff(self.end.sdata) # to outputs
                d['name'] = name
            d['args']['starttime'] = datetime.datetime.fromtimestamp(t).strftime(READABLE_TIMESTAMP_FORMAT)
            d['args']['inputs'] = self.data
        if self.type == 'E':
            d['args']['endtime'] = datetime.datetime.fromtimestamp(t).strftime(READABLE_TIMESTAMP_FORMAT)
            d['args']['outputs'] = self.data
        return d

