# system imports
import os
import subprocess
import unittest

# own imports
import ttviewer
import extendedlogging

# constants
TMPDIR = ttviewer.DEFAULT_TMPDIR
BROWSER = ttviewer.DEFAULT_BROWSER
LOGFILE = extendedlogging.DEFAULT_LOG_FILE
BASEDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
TTVIEWER = os.path.join(BASEDIR, 'ttviewer.py')



class TestTTViewer(unittest.TestCase):

    def test_helptext(self):
        '''Basic python syntax check, produce text.'''
        self._run_cmd(TTVIEWER, '-h')

    def test_demo(self):
        '''Show how the trace demo can be transformed to html.'''
        # pre-clean
        if os.path.isfile(LOGFILE):
            os.remove(LOGFILE)
        # run demo to create tracing
        demo_script = os.path.join(BASEDIR, 'demo.py')
        self._run_cmd('python', demo_script)
        # create html
        actual_output = self._run_cmd(TTVIEWER, '-n', LOGFILE)
        expected_output = """Converting /tmp/extendedlogging.log to /tmp/ttviewer/ttviewer.json ... done (0.0MB)
Converting /tmp/ttviewer/ttviewer.json to /tmp/ttviewer/ttviewer.html ... done (4.0MB)"""
        self.assertEqual(actual_output, expected_output)


    # helper functions below

    def _run_cmd(self, command, *args):
        cmd = '{} {}'.format(command, ' '.join(args))
        return subprocess.check_output(cmd, shell=True).strip().decode('utf-8')




if __name__ == '__main__':
    unittest.main()

