# -*- coding: utf-8 -*-

__author__ = 'Jan Feitsma'

import logging
import autologging
import numpy


# export everything combined
from logging import *
from autologging import *


ARRAY_SIZE_LIMIT = None # TODO? not implemented.
STRING_SIZE_LIMIT = None

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


BASIC_FORMAT = "%(levelname)s:%(name)s:%(message)s"
EXTENDED_FORMATTER = ExtendedFormatter


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


