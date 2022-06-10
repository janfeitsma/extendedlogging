#!/usr/bin/env python


'''ttviewer: visualize logging/tracing/timing data as Gantt charts using Google Chrome built-in viewer (catapult).

Several kinds of data files are supported.

The browser (cli) needs a .html file, produced by catapult trace2html.
All necessary conversions are done/attempted:
If a trace .json file is given, then it is converted to .html using catapult trace2html.
If one or more .log files are given, then they are parsed under the assumption the content is python (auto)logging, merged into .json.

More converters to .json could be registered in ttlib/ttconvert.
'''

__author__ = 'Jan Feitsma'


# system imports
import sys
import os
import shutil
import argparse
import subprocess

# own imports
import ttlib



# browser
DEFAULT_BROWSER = 'google-chrome'

# other defaults
DEFAULT_TMPDIR = '/tmp/ttviewer' # will be wiped at the start!
DEFAULT_INPUT_LIMIT_MB = 100.0



class TraceViewer(object):
    '''View given file in browser. Perform necessary conversions.'''

    def __init__(self, filenames, view=True, verbose=True):
        self.filenames = filenames
        self.browser = DEFAULT_BROWSER
        self.tmpdir = DEFAULT_TMPDIR
        self.view = view
        self.verbose = verbose
        self.limit = DEFAULT_INPUT_LIMIT_MB
        self.dryrun = False
        self.runner_class = ttlib.ttconvert.Runner

    def run(self, dryrun=False):
        '''Run the viewer: generate html and launch a browser.'''
        self.dryrun = dryrun
        self._setup_tmpdir()
        htmlfile = os.path.join(self.tmpdir, 'ttviewer.html')
        runner = self.runner_class(self.tmpdir, self.filenames, htmlfile, self.limit)
        runner.dryrun = dryrun
        runner.messager = self._message
        runner.run()
        if self.view:
            self._launch_browser(htmlfile)

    def _message(self, message, newline=True):  
        if not self.verbose:
            return
        if not message.endswith('\n') and newline:
            message += '\n'
        sys.stdout.write(message)
        sys.stdout.flush()

    def _setup_tmpdir(self):
        if self.dryrun:
            self._message('dryrun: Wipe tmpdir {}'.format(self.tmpdir))
            return
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir) # careful, hard wipe! best to remove this from option interface
        os.mkdir(self.tmpdir)

    def _launch_browser(self, htmlfile):
        if self.dryrun:
            self._message('dryrun: Launch browser {} on {}'.format(self.browser, htmlfile))
            return
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
    parser.add_argument('-n', '--noviewer', action='store_true', help='do not launch browser, stop after creating HTML')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--dryrun', action='store_true', help='dryrun, just list the conversions without executing them')
    group.add_argument('-q', '--quiet', action='store_true', help='suppress progress messages')
    parser.add_argument('-L', '--limit', type=float, default=DEFAULT_INPUT_LIMIT_MB, help='input file size limit in MB')
    parser.add_argument('-b', '--browser', default=DEFAULT_BROWSER, type=str, help='which browser to use')
    parser.add_argument('--io', action='store_true', help='render with input->output labels')
    parser.add_argument('filenames', help='input file(s)', nargs='+', metavar='filename')
    return parser.parse_args()


def run_viewer(filenames, browser=DEFAULT_BROWSER, io=False, limit=DEFAULT_INPUT_LIMIT_MB, noviewer=False, quiet=False, dryrun=False):
    # configure
    ttlib.ttstore.INCLUDE_IO_IN_NAME = io
    s = TraceViewer(filenames, view=not noviewer, verbose=not quiet)
    s.browser = browser
    s.limit = limit
    # execute
    s.run(dryrun)


if __name__ == '__main__':
    run_viewer(**vars(parse_args()))

