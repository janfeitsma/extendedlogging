#!/usr/bin/env python

# converters for ttviewer

__author__ = 'Jan Feitsma'


# system imports
import os
import shutil
import subprocess

# own imports
#import ttstore



# unfortunately Google catapult suite is not available via pip?
# https://chromium.googlesource.com/catapult/+/HEAD/tracing/README.md
# user could patch it via symlink, for example:
#    ln -s /pathto/catapult_py3/tracing/bin/trace2html
CATAPULT_TRACE_JSON2HTML = 'trace2html'

# for now: use an old external toolset
# TODO: migrate into here, call directly instead of via subprocess
TRACE2JSON = 'tracelog2json'



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


def log2json(tracefilename, tmpjsonfilename):
    cmd = 'python {} -o {} {}'.format(_find_utility(TRACE2JSON), tmpjsonfilename, tracefilename)
    subprocess.run(cmd, shell=True, check=True)


def json2html(jsonfile, htmlfile):
    cmd = '{} {} --quiet --output={}'.format(_find_utility(CATAPULT_TRACE_JSON2HTML), jsonfile, htmlfile)
    subprocess.run(cmd, shell=True, check=True)

