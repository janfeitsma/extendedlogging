#!/usr/bin/env python


'''ttviewer: visualize logging/tracing/timing data as Gantt charts using Google Chrome built-in viewer (catapult).

Several kinds of data files are supported.

The browser (cli) needs a .html file, produced by catapult trace2html.
All necessary conversions are done/attempted:
If a trace .json file is given, then it is converted to .html using catapult trace2html.
If one or more .log files are given, then they are parsed under the assumption the content is python (auto)logging, merged into .json.

More converters to .json could be registered in ttconvert.
'''

__author__ = 'Jan Feitsma'


# system imports
import sys
import os
import argparse
import subprocess
import traceback
import ttconvert


# browser
DEFAULT_BROWSER = 'google-chrome'

# other defaults
DEFAULT_TMPDIR = '/tmp/ttviewer'



class TraceViewer(object):
    '''View given file in browser. Perform necessary conversions.'''

    def __init__(self, filename, browser=DEFAULT_BROWSER, tmpdir=DEFAULT_TMPDIR, view=True, verbose=True):
        self.filename = filename
        self.browser = browser
        self.tmpdir = tmpdir
        self.view = view
        self.verbose = verbose

    def run(self):
        '''Run the viewer: generate html and launch a browser.'''
        self._ensure_tmpdir()
        htmlfile = self._ensure_htmlfile()
        if self.view:
            self._launch_browser(htmlfile)

    def _message(self, message, newline=True):  
        if not self.verbose:
            return
        if not message.endswith('\n'):
            message += '\n'
        sys.stdout.write(message)
        sys.stdout.flush()

    @staticmethod
    def _filesize(filename):  
        size_mb = os.path.getsize(filename) / 1024.0 / 1024.0
        return '{:.1f}MB'.format(size_mb)

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
        self._message('Converting {} to {} ...'.format(srcfile, tgtfile), newline=False)
        converter(srcfile, tgtfile)
        self._message(' done ({})\n'.format(self._filesize(tgtfile)))
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
    exampleTxt = '''Example: TODO'''
    parser = argparse.ArgumentParser(description=descriptionTxt, epilog=exampleTxt, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-t', '--tmpdir', default=DEFAULT_TMPDIR, help='temporary folder to use')
    parser.add_argument('-n', '--noviewer', action='store_true', help='do not launch browser, stop after creating HTML')
    parser.add_argument('-b', '--browser', default=DEFAULT_BROWSER, type=str, help='which browser to use')
    parser.add_argument('-q', '--quiet', action='store_true', help='suppress progress messages')
    # TODO: intermediate size limits/checks? to prevent system locking up in swap
    parser.add_argument('filename', help='input file')
    # TODO: allow and merge multiple .json / .log files
    #parser.add_argument('filenames', help='input file(s)', nargs='+', metavar='filename')
    return parser.parse_args()


def run_viewer(filename, tmpdir=DEFAULT_TMPDIR, browser=DEFAULT_BROWSER, noviewer=False, quiet=False):
    # execute
    s = TraceViewer(filename, browser=browser, tmpdir=tmpdir, view=not noviewer, verbose=not quiet)
    s.run()


if __name__ == '__main__':
    run_viewer(**vars(parse_args()))

