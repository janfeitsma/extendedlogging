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
        expected_output = """Converting /tmp/extendedlogging.log \(.*B\) to /tmp/ttviewer/ttviewer.json using parser: LoggingParser ... done \(.*B, n=6\)
Converting /tmp/ttviewer/ttviewer.json \(.*B\) to /tmp/ttviewer/ttviewer.html using tool: trace2html ... done \(...s, 4.0MB\)"""
        if quiet:
            expected_output = ''
        self.assertTrue(os.path.isfile(htmlfile))
        self.assertMultiLineRegexMatch(expected_output, actual_output)

    def test_json_html_render(self):
        '''Operate on a sample json file and render webpage using selenium, including a click on the detailed info pane.'''
        self._test_json_html_render('demo_fib2.png')

    def test_json_html_render_with_io(self):
        '''Operate on a sample json file and render webpage using selenium, with extra input/output labels.'''
        self._test_json_html_render('demo_fib.png', '--io')

    def _test_json_html_render(self, expected_pngfile, *args):
        htmlfile = os.path.join(TMPDIR, 'ttviewer.html')
        # pre-clean
        if os.path.isfile(htmlfile):
            os.remove(htmlfile)
        # create html
        logfile = os.path.join(BASEDIR, 'tests', 'demo_fib.log')
        cmd_args = ['-n', logfile]
        if len(args):
            cmd_args += args
        self._run_cmd(TTVIEWER, *cmd_args)
        # render html, convert to png
        from selenium import webdriver
        from time import sleep
        options = webdriver.firefox.options.Options()
        options.headless = True
        options.add_argument('--width=1280')
        options.add_argument('--height=862') # TODO: why is resulting height only 777 pixels?!
        browser = webdriver.Firefox(options=options)
        browser.get('file://' + htmlfile)
        sleep(1)
        el = browser.find_element_by_xpath("//body")
        action = webdriver.common.action_chains.ActionChains(browser)
        action.move_to_element_with_offset(el, 730, 116)
        action.click()
        action.perform()
        sleep(0.1)
        actual_png = '/tmp/ttviewer/ttviewer.png'
        expected_png = os.path.join(BASEDIR, 'tests', expected_pngfile)
        browser.get_screenshot_as_file(actual_png)
        browser.quit()
        # compare png hashes
        expected_md5 = self._run_cmd('md5sum', expected_png).split()[0]
        actual_md5 = self._run_cmd('md5sum', actual_png).split()[0]
        self.assertEqual(expected_md5, actual_md5)

    # helper functions below

    def _run_cmd(self, command, *args):
        cmd = '{} {}'.format(command, ' '.join(args))
        return subprocess.check_output(cmd, shell=True).strip().decode('utf-8')




if __name__ == '__main__':
    unittest.main()

