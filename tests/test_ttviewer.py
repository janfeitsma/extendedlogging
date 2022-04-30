# system imports
import os
import subprocess
import unittest

# own imports
import testcase
import ttviewer
import extendedlogging

# constants
TMPDIR = ttviewer.DEFAULT_TMPDIR
BROWSER = ttviewer.DEFAULT_BROWSER
LOGFILE = extendedlogging.DEFAULT_LOG_FILE
BASEDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
TTVIEWER = os.path.join(BASEDIR, 'ttviewer.py')



class TestTTViewer(testcase.TestCase):

    def test_helptext(self):
        '''Basic python syntax check, produce text.'''
        self._run_cmd(TTVIEWER, '-h')

    def test_demo(self):
        '''Show how the trace demo can be transformed to html.'''
        self._test_demo(quiet=False)

    def test_demo_quiet(self):
        '''Show how the trace demo can be transformed to html, without progress/info output.'''
        self._test_demo(quiet=True)

    def _test_demo(self, quiet=False):
        htmlfile = os.path.join(TMPDIR, 'ttviewer.html')
        # pre-clean
        if os.path.isfile(LOGFILE):
            os.remove(LOGFILE)
        if os.path.isfile(htmlfile):
            os.remove(htmlfile)
        # run demo to create tracing
        demo_script = os.path.join(BASEDIR, 'demo.py')
        self._run_cmd('python', demo_script)
        # create html
        args = ['-n', LOGFILE]
        if quiet:
            args.append('-q')
        actual_output = self._run_cmd(TTVIEWER, *args)
        # checks
        expected_output = """Converting /tmp/extendedlogging.log to /tmp/ttviewer/ttviewer.json using tracelog2json ... done \(...s, 0.0MB, n=8\)
Converting /tmp/ttviewer/ttviewer.json to /tmp/ttviewer/ttviewer.html using trace2html ... done \(...s, 4.0MB\)"""
        if quiet:
            expected_output = ''
        self.assertTrue(os.path.isfile(htmlfile))
        self.assertMultiLineRegexMatch(expected_output, actual_output)


    # helper functions below

    def _run_cmd(self, command, *args):
        cmd = '{} {}'.format(command, ' '.join(args))
        return subprocess.check_output(cmd, shell=True).strip().decode('utf-8')




if __name__ == '__main__':
    unittest.main()

