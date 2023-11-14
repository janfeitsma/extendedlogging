#!/usr/bin/env python

# standard converters for ttviewer

__author__ = 'Jan Feitsma'


# system imports
import os
import shutil
import subprocess

# own imports
import ttvlib.ttstore as ttstore
import ttvlib.ttparse as ttparse
import ttvlib.ttconvert.registry as registry



# unfortunately Google catapult suite is not available via pip?
# https://chromium.googlesource.com/catapult/+/HEAD/tracing/README.md
# user could patch it via symlink, for example:
#    ln -s /pathto/catapult_py3/tracing/bin/trace2html
CATAPULT_TRACE_JSON2HTML = 'trace2html'

# allow commenting lines
IGNORE_LINE_CHAR = '#'

# extendedlogging can write format spec as first line in the tracing file (option 'write_format_header')
LOGFILE_FORMAT_SPEC = '# format: '


def _find_utility(utility):
    # check if available already
    w = shutil.which(utility)
    if not w is None:
        return w
    # if not, then check environment variable
    envname = utility.upper()
    envvalue = os.getenv(envname)
    if envvalue:
        return envvalue
    # if not, then check current folder
    basedir = os.path.dirname(os.path.realpath(__file__))
    w = os.path.join(basedir, utility)
    if os.path.isfile(w):
        return w
    raise FileNotFoundError('could not find utility {}, either use symlink or environment variable {}'.format(utility, envname))


def _convert_log(tracefilename, tmpjsonfilename):
    return parse_and_create_json(tracefilename, tmpjsonfilename, _convert_log.parser)
_convert_log.parser = ttparse.PythonLoggingParser()


def _convert_spdlog(tracefilename, tmpjsonfilename):
    return parse_and_create_json(tracefilename, tmpjsonfilename, _convert_spdlog.parser)
_convert_spdlog.parser = ttparse.SpdlogParser()


def _convert_json2html(jsonfile, htmlfile):
    cmd = '{} {} --quiet --output={}'.format(_convert_json2html.tool, jsonfile, htmlfile)
    subprocess.run(cmd, shell=True, check=True)
_convert_json2html.tool = _find_utility(CATAPULT_TRACE_JSON2HTML)


def parse_and_create_json(inputfilename, outputfilename, parser):
    s = ttstore.TracingJsonStore(outputfilename)
    with open(inputfilename, 'r') as f:
        lc = 0
        for line in f:
            line = line.strip()
            lc += 1
            # optionally configure parser
            if line.startswith(LOGFILE_FORMAT_SPEC):
                parser.configure(line.replace(LOGFILE_FORMAT_SPEC, ''))
                continue
            # ignore line?
            if line.startswith(IGNORE_LINE_CHAR):
                continue
            # regular line parsing
            try:
                r = parser(line)
            except ttparse.ParseError as e:
                raise type(e)('at line {}: {}'.format(lc, str(e))) from None
            # r is None, for a to-be-ignored line
            if r:
                try:
                    s.add(r)
                except Exception as e:
                    raise type(e)('at line {}: {}'.format(lc, str(e))) from None
    return s.size


registry.add_file(_convert_log, '*.log')
registry.add_file(_convert_spdlog, '*.spdlog')
registry.add_file(_convert_json2html, '*.json')

