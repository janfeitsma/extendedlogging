#!/usr/bin/env python

# standard converters for ttviewer

__author__ = 'Jan Feitsma'


# system imports
import os
import shutil
import subprocess

# own imports
import ttstore
import ttparse
import ttconvert.registry as registry



# unfortunately Google catapult suite is not available via pip?
# https://chromium.googlesource.com/catapult/+/HEAD/tracing/README.md
# user could patch it via symlink, for example:
#    ln -s /pathto/catapult_py3/tracing/bin/trace2html
CATAPULT_TRACE_JSON2HTML = 'trace2html'



def _find_utility(utility):
    # check if available already
    w = shutil.which(utility)
    if not w is None:
        return w
    # if not, then check current folder
    basedir = os.path.dirname(os.path.realpath(__file__))
    w = os.path.join(basedir, utility)
    if os.path.isfile(w):
        return w
    raise FileNotFoundError('could not find utility ' + utility)


def _convert_log(tracefilename, tmpjsonfilename):
    return parse_and_create_json(tracefilename, tmpjsonfilename, _convert_log.parser)
_convert_log.parser = ttparse.LoggingParser()


def _convert_json2html(jsonfile, htmlfile):
    cmd = '{} {} --quiet --output={}'.format(_convert_json2html.tool, jsonfile, htmlfile)
    subprocess.run(cmd, shell=True, check=True)
_convert_json2html.tool = _find_utility(CATAPULT_TRACE_JSON2HTML)


def parse_and_create_json(inputfilename, outputfilename, parser):
    s = ttstore.TracingJsonStore(outputfilename)
    with open(inputfilename, 'r') as f:
        lc = 0
        for line in f:
            lc += 1
            try:
                r = parser(line)
            except Exception as e:
                raise type(e)('at line {}: {}'.format(lc, str(e))) from None
            # r is None, for a to-be-ignored line
            if r:
                try:
                    s.add(r)
                except Exception as e:
                    raise type(e)('at line {}: {}'.format(lc, str(e))) from None
    return s.size


registry.add_file(_convert_log, '*.log')
registry.add_file(_convert_json2html, '*.json')

