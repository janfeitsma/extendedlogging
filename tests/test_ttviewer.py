# system imports
import os
import subprocess
import unittest

# own imports
import testcase
import ttvlib.ttviewer as ttviewer
import extendedlogging

# constants
TMPDIR = ttviewer.DEFAULT_TMPDIR
BROWSER = ttviewer.DEFAULT_BROWSER
LOGFILE = extendedlogging.DEFAULT_LOG_FILE
BASEDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
TTVIEWER = os.path.join(BASEDIR, 'ttviewer')
PATH_TO_DEMOS = os.path.join(BASEDIR, 'demos')


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
        demo_script = os.path.join(PATH_TO_DEMOS, 'demo.py')
        self._run_cmd('python', demo_script)
        # create html
        args = ['-n', LOGFILE]
        if quiet:
            args.append('-q')
        actual_output = self._run_cmd(TTVIEWER, *args)
        # checks
        expected_output = """Converting /tmp/extendedlogging.log \(.*B\) to /tmp/ttviewer/extendedlogging.log.json using parser: LoggingParser ... done \(.*B, n=9\)
Converting /tmp/ttviewer/extendedlogging.log.json \(.*B\) to /tmp/ttviewer/ttviewer.html using tool: trace2html ... done \(...s, 4.0MB\)"""
        if quiet:
            expected_output = ''
        self.assertTrue(os.path.isfile(htmlfile))
        self.assertMultiLineRegexMatch(expected_output, actual_output)

    def test_json_html_render(self):
        '''Operate on a sample json file and render webpage using selenium, including a click on the detailed info pane.'''
        logfile = os.path.join(BASEDIR, 'tests', 'demo_fib.log')
        self._run_cmd(TTVIEWER, '-n', logfile)
        self._test_json_html_render('demo_fib2.png', click=(730,116))

    def test_json_html_render_with_io(self):
        '''Operate on a sample json file and render webpage using selenium, with extra input/output labels.'''
        logfile = os.path.join(BASEDIR, 'tests', 'demo_fib.log')
        self._run_cmd(TTVIEWER, '-n', logfile, '--io')
        self._test_json_html_render('demo_fib.png', click=(730,116))

    def test_catapult_render(self):
        '''Use the demo data from catapult, well hidden in their website.'''
        # download the data file if not yet present in tests (file is a bit large to store in git)
        # https://www.chromium.org/developers/how-tos/trace-event-profiling-tool/using-frameviewer/
        logfile = os.path.join(BASEDIR, 'tests', 'demo_catapult.json')
        if not os.path.isfile(logfile):
            self._run_cmd('wget', '-q', '-O', logfile, 'https://www.chromium.org/developers/how-tos/trace-event-profiling-tool/using-frameviewer/nytimes_scroll_trace')
        self._run_cmd(TTVIEWER, '-n', logfile)
        self._test_json_html_render('demo_catapult.png', sleeptime=5)

    def test_events_html_render(self):
        '''Try to render events ... hard to spot, need some trickery, or migrate to Perfetto?'''
        logfile = os.path.join(BASEDIR, 'tests', 'demo_events.log')
        self._run_cmd(TTVIEWER, '-n', logfile)
        self._test_json_html_render('demo_events.png')

    def test_multiprocessing_html_render(self):
        '''Multiple threads/processes are rendered in their own lanes.'''
        logfile = os.path.join(BASEDIR, 'tests', 'demo_multiprocessing.log')
        self._run_cmd(TTVIEWER, '-n', logfile)
        self._test_json_html_render('demo_multiprocessing.png')

    def test_autoclose_openloop_html_render(self):
        '''Without the autoclose functionality, the loop layer would not be rendered because final tick errors out and the log is incomplete.'''
        logfile = os.path.join(BASEDIR, 'tests', 'demo_openloop.log')
        self._run_cmd(TTVIEWER, '-n', logfile)
        self._test_json_html_render('demo_openloop.png')


    # helper functions below

    def setUp(self):
        htmlfile = os.path.join(TMPDIR, 'ttviewer.html')
        # pre-clean
        if os.path.isfile(htmlfile):
            os.remove(htmlfile)

    def _test_json_html_render(self, expected_pngfile, sleeptime=1, click=None):
        htmlfile = os.path.join(TMPDIR, 'ttviewer.html')
        # render html, convert to png
        from selenium import webdriver
        from time import sleep
        options = webdriver.firefox.options.Options()
        options.headless = True
        options.add_argument('--width=1280')
        options.add_argument('--height=862') # TODO: why is resulting height only 777 pixels?!
        service = webdriver.firefox.service.Service(log_path=os.path.devnull) # get rid of geckodriver.log
        browser = webdriver.Firefox(options=options, service=service)
        browser.get('file://' + htmlfile)
        sleep(sleeptime) # nasty
        if click:
            el = browser.find_element(by=webdriver.common.by.By.XPATH, value="//body")
            action = webdriver.common.action_chains.ActionChains(browser)
            action.move_to_element_with_offset(el, *click)
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
        self.assertEqual(expected_md5, actual_md5, 'difference between actual and expected: {} {}'.format(actual_png, expected_png))

    def _run_cmd(self, command, *args):
        cmd = '{} {}'.format(command, ' '.join(args))
        return subprocess.check_output(cmd, shell=True).strip().decode('utf-8')




if __name__ == '__main__':
    unittest.main()

