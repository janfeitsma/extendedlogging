#!/usr/bin/env python

# datastore for ttviewer


import datetime
import json


# the HTML viewer requires magic microsecond scaling
MAGIC_MICROSECOND_TIMESTAMP_SCALING = 1e6

# throw an error if the amount of data is getting large
# TODO: or just cut off and warn?
STORE_LIMIT = 1e7



class TracingJsonStore:
    """This data store holds trace items and can write them as json for the catapult traceviewer.
    
    Start- and end items form a duration; they come in pairs.

    Items must arrive in order, i.e. increasing timestamp and properly nested."""
    # TODO: events? can write at the end?
    def __init__(self, outputfilename):
        self.items = []
        self.stack = []
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
        assert item.timestamp > self.last_timestamp, 'timestamp out of order: got {}, last was {}'.format(item.timestamp, self.last_timestamp)
        self.last_timestamp = item.timestamp
        # handle item(s) and check stack integrity
        if item.type == 'B':
            self.handle_start_item(item)
        elif item.type == 'E':
            self.handle_end_item(item)
        else:
            raise Exception('unrecognized trace item type: {}'.format(item.type))

    def handle_start_item(self, item):
        self.stack.append(item)

    def handle_end_item(self, item):
        start_item = self.stack.pop()
        if item.name != start_item.name:
            raise Exception('item pop inconsistency: popped item is {}:{}, expected name is {}'.format(item.args['where'], item.name, start_item.name))
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
            raise Exception('store limit exceeded: {}'.format(self.limit))



class TracingItem:
    def __init__(self, timestamp, itemtype, name, **kwargs):
        '''A TracingItem represents a json line.'''
        self.timestamp = timestamp # float
        self.name = name
        self.type = itemtype
        # set placeholders for readable timestamps, to ensure they are shown first in detailed info pane
        self.args = {}
        self.args["StartTime"] = None
        self.args["EndTime"] = None
        for (k, v) in kwargs.items():
            self.args[k] = v

    def dict(self):
        '''Return dict for json conversion.'''
        t = self.timestamp
        ts = int(MAGIC_MICROSECOND_TIMESTAMP_SCALING * self.timestamp)
        d = {'name': self.name, 'ts': ts, 'ph': self.type, 'args': self.args}
        return d
