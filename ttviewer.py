#!/usr/bin/env python


'''ttviewer: visualize logging/tracing/timing data as Gantt charts using Google Chrome built-in viewer (catapult).

Several kinds of data files are supported.

The browser (cli) needs a .html file, produced by catapult trace2html.
All necessary conversions are done/attempted:
If a trace .json file is given, then it is converted to .html using catapult trace2html.
If one or more .log files are given, then they are parsed under the assumption the content is python (auto)logging, merged into .json.
TODO: merge is not yet implemented.

More converters to .json could be registered in ttconvert.
'''

__author__ = 'Jan Feitsma'


# system imports
import sys
import os
import time
import argparse
import subprocess
import traceback
import ttconvert


# browser
DEFAULT_BROWSER = 'google-chrome'

# other defaults
DEFAULT_TMPDIR = '/tmp/ttviewer'
DEFAULT_INPUT_LIMIT_MB = 100.0



class TraceViewer(object):
    '''View given file in browser. Perform necessary conversions.'''

    def __init__(self, filename, view=True, verbose=True):
        self.filename = filename
        self.browser = DEFAULT_BROWSER
        self.tmpdir = DEFAULT_TMPDIR
        self.view = view
        self.verbose = verbose
        self.limit = DEFAULT_INPUT_LIMIT_MB
        # check input size once (not on intermediates)
        srcfile = filename
        if os.path.getsize(srcfile) / 1024.0**2 > self.limit:
            raise Exception('input file size ({}) of {} exceeds limit of {:.1f}MB'.format(srcfile, self._filesize(srcfile), self.limit))

    def run(self):
        '''Run the viewer: generate html and launch a browser.'''
        self._ensure_tmpdir()
        htmlfile = self._ensure_htmlfile()
        if self.view:
            self._launch_browser(htmlfile)

    def _message(self, message, newline=True):  
        if not self.verbose:
            return
        if not message.endswith('\n') and newline:
            message += '\n'
        sys.stdout.write(message)
        sys.stdout.flush()

    @staticmethod
    def _filesize(filename):
        numbytes = os.path.getsize(filename)
        if os.path.getsize(filename) < 1000:
            return '{:d}B'.format(numbytes)
        elif os.path.getsize(filename) < 1e6:
            return '{:.1f}KB'.format(numbytes / 1024.0)
        elif os.path.getsize(filename) < 1e9:
            return '{:.1f}MB'.format(numbytes / 1024.0**2)
        return '{:.1f}GB'.format(numbytes / 1024.0**3)

    def _ensure_tmpdir(self):
        if not os.path.isdir(self.tmpdir):
            os.mkdir(self.tmpdir)

    def _ensure_convert(self, given, tgt, src, converter, ensure_src):
        """
        'given' is a filename, if it already exists, then all is done
        otherwise: converter is called to convert from src extension to tgt extension
        """
        if given.endswith(tgt):
            # no action needed
            return given
        # otherwise: convert to temporary tgtfile
        tgtfile = os.path.join(self.tmpdir, 'ttviewer' + tgt)
        srcfile = ensure_src() # may also trigger convert
        # message
        def describe_converter(converter):
            if hasattr(converter, 'tool'):
                return 'tool: ' + os.path.basename(converter.tool)
            if hasattr(converter, 'parser'):
                return 'parser: ' + type(converter.parser).__name__
            # just show function name
            return converter.__name__
        self._message('Converting {} ({}) to {} using {} ...'.format(srcfile, self._filesize(srcfile), tgtfile, describe_converter(converter)), newline=False)
        t_start = time.time()
        n = converter(srcfile, tgtfile)
        elapsed = time.time() - t_start
        details = '{:.1f}s, {}'.format(elapsed, self._filesize(tgtfile))
        if n:
            details += ', n={}'.format(n)
        self._message(' done ({})\n'.format(details))
        return tgtfile

    def _ensure_htmlfile(self):
        return self._ensure_convert(self.filename, '.html', '.json', ttconvert.json2html, self._ensure_jsonfile)

    def _ensure_jsonfile(self):
        return self._ensure_convert(self.filename, '.json', '.log', ttconvert.log2json, self._ensure_logfile)

    def _ensure_logfile(self):
        if not self.filename.endswith('.log'):
            raise Exception('Cannot handle file: ' + self.filename) # should end with .html, .json or .log
        return self.filename

    def _launch_browser(self, htmlfile):
        self._message('Launching browser ...')
        cmd = '{} {}'.format(self.browser, htmlfile)
        subprocess.check_output(cmd, shell=True)



def parse_args():
    descriptionTxt = __doc__
    exampleTxt = '''Example: ttviewer.py tests/demo_fib.log --io
Converting tests/demo_fib.log (5.1KB) to /tmp/ttviewer/ttviewer.json using parser: LoggingParser ... done (0.0s, 13.3KB, n=82)
Converting /tmp/ttviewer/ttviewer.json (13.3KB) to /tmp/ttviewer/ttviewer.html using tool: trace2html ... done (1.5s, 4.0MB)
Launching browser ... # see tests/demo_fib.png

Example: ttviewer.py tests/demo_catapult.json
Converting tests/demo_catapult.json (13.2MB) to /tmp/ttviewer/ttviewer.html using tool: trace2html ... done (1.9s, 8.3MB)
Launching browser ... # see tests/demo_catapult.png
'''
    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        def __init__(self, prog):
            argparse.ArgumentDefaultsHelpFormatter.__init__(self, prog, max_help_position=36)
            argparse.RawDescriptionHelpFormatter.__init__(self, prog, max_help_position=36)
    parser = argparse.ArgumentParser(description=descriptionTxt, epilog=exampleTxt, formatter_class=CustomFormatter)
    parser.add_argument('-t', '--tmpdir', default=DEFAULT_TMPDIR, help='temporary folder to use')
    parser.add_argument('-n', '--noviewer', action='store_true', help='do not launch browser, stop after creating HTML')
    parser.add_argument('-L', '--limit', type=float, default=DEFAULT_INPUT_LIMIT_MB, help='input file size limit in MB')
    parser.add_argument('-b', '--browser', default=DEFAULT_BROWSER, type=str, help='which browser to use')
    parser.add_argument('--io', action='store_true', help='render with input->output labels')
    parser.add_argument('-q', '--quiet', action='store_true', help='suppress progress messages')
    parser.add_argument('filename', help='input file')
    # TODO: allow and merge multiple .json / .log files
    #parser.add_argument('filenames', help='input file(s)', nargs='+', metavar='filename')
    return parser.parse_args()


def run_viewer(filename, tmpdir=DEFAULT_TMPDIR, browser=DEFAULT_BROWSER, io=False, limit=DEFAULT_INPUT_LIMIT_MB, noviewer=False, quiet=False):
    # configure
    ttconvert.ttstore.INCLUDE_IO_IN_NAME = io
    s = TraceViewer(filename, view=not noviewer, verbose=not quiet)
    s.browser = browser
    s.tmpdir = tmpdir
    s.limit = limit
    # execute
    s.run()


if __name__ == '__main__':
    run_viewer(**vars(parse_args()))

