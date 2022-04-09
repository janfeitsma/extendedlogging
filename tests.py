import sys
import os
import shutil
import re
import unittest

# get system under test
import extendedlogging

# constants
TMP_FOLDER = '/tmp/test_extendedlogging'
LOG_FILE = os.path.join(TMP_FOLDER, 'logfile.txt')




class TestExtendedLogging(unittest.TestCase):

    def test_logging_info_default(self):
        '''Default configuration shall be to log INFO events, only to console (not file), no timestamps.'''
        # run
        extendedlogging.info('hi') # show
        extendedlogging.debug('debug message') # hide, debug level is lower than default info level
        extendedlogging.warning('almost done') # show, warning level is higher
        # verify
        expected_content = """INFO   :test_logging_info_default:hi
WARNING:test_logging_info_default:almost done
"""
        self._compare_stdout(expected_content)
        self.assertFalse(os.path.isfile(LOG_FILE))

    def test_trace_function_decorator_timestamp(self):
        '''Apply tracing decorator to a little function. It shall only appear in logfile, not console, default with timestamps.'''
        # setup
        self._configure(tracing=True)
        # run
        @extendedlogging.traced
        def f():
            pass
        f()
        # verify
        t = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}' # timestamp with millisecond resolution
        empty = '{}'
        expected_content = f"""{t}:TRACE:tests.py,\d+:root.f:CALL \*\(\) \*\*{empty}
{t}:TRACE:tests.py,\d+:root.f:RETURN None
"""
        self._compare_logfile(expected_content, regex=True)
        self._compare_stdout("")

    def test_mixed_stdout_file(self):
        '''It is possible to mix both logging styles: basic messages to stdout, more detail (tracing) is logged to file.'''
        # setup
        self._configure(tracing=True)
        # run
        @extendedlogging.traced
        def f():
            extendedlogging.info('hi')
            extendedlogging.debug('debug message')
            extendedlogging.warning('almost done')
        f()
        # verify
        expected_stdout = """INFO   :f:hi
WARNING:f:almost done
"""
        self._compare_stdout(expected_stdout)
        self._compare_logfile_linecount(5)

    def test_trace_class_decorator(self):
        '''The magical beauty of the tracing decorator is that it can be applied to a class.'''
        # setup
        self._configure(tracing=True, file_format='%(levelname)s:%(funcName)s: %(message)s')
        # run
        @extendedlogging.traced
        class myclass():
            def __init__(self, *args, **kwargs):
                self.f()
            def f(self):
                pass
            def g(self):
                return 3
        # run
        c = myclass('some_argument')
        c.g()
        # verify
        expected_content = """TRACE:__init__: CALL *('some_argument',) **{}
TRACE:f: CALL *() **{}
TRACE:f: RETURN None
TRACE:__init__: RETURN None
TRACE:g: CALL *() **{}
TRACE:g: RETURN 3
"""
        self._compare_logfile(expected_content)

    def _test_newline_folding(self):
        '''Newlines should be folded into a single line.'''
        # setup
        self._setupLogger()
        string_with_newlines = """This is line 1.
        This is line 2,
        finally we have line 3."""
        # run
        extendedlogging.info(string_with_newlines)
        # verify
        expected_log_content = "INFO: test_newline_folding: This is line 1.\\n        This is line 2,\\n        finally we have line 3.\n"
        self.assertEqual(self._readLogFile(), expected_log_content)

    def _test_huge_string_as_is(self):
        '''By default, a huge string is logged as is.'''
        # setup
        self._setupLogger()
        huge_string = str(range(100))
        # run
        extendedlogging.log(extendedlogging.TRACE, huge_string)
        # verify
        expected_log_content = "TRACE: test_huge_string_as_is: " + str(range(100)) + "\n"
        self.assertEqual(self._readLogFile(), expected_log_content)

    def _test_huge_string_condensed(self):
        '''If so configured, a huge string should be cut.'''
        # setup
        self._setupLogger()
        extendedlogging.STRING_SIZE_LIMIT = 50
        huge_string = str(range(100))
        # run
        extendedlogging.log(extendedlogging.TRACE, huge_string)
        # verify
        expected_log_content = "TRACE: test_huge_string_condensed: [0, 1, 2, 3, 4,<375 characters truncated>\n"
        self.assertEqual(self._readLogFile(), expected_log_content)

    def _not_implemented_test_huge_array_as_is(self):
        '''By default, a huge array is logged as is.'''
        # setup
        self._setupLogger()
        huge_array = range(100)
        # run
        @extendedlogging.traced
        def f(arg1, arg2):
            pass
        f(huge_array, tuple(reversed(huge_array)))
        # verify
        expected_log_content = "TRACE: f: CALL *(" + str(range(100)) + ", " + str(tuple(reversed(huge_array))) + ") **{}\nTRACE: f: RETURN None\n"
        self.assertEqual(self._readLogFile(), expected_log_content)

    def _not_implemented_test_huge_array_condensed(self):
        '''If so configured, a huge array should be displayed with the interior removed, as numpy would do.'''
        # setup
        self._setupLogger()
        extendedlogging.ARRAY_SIZE_LIMIT = 10
        huge_array = range(10000)
        # run
        @extendedlogging.traced
        def f(arg1, arg2):
            pass
        f(huge_array, tuple(reversed(huge_array)))
        # verify
        expected_log_content = "TRACE: test_huge_array_condensed: [0, 1, 2, 3, 4,<375 characters truncated>\n"
        self.assertEqual(self._readLogFile(), expected_log_content)

    # helper functions below

    def setUp(self):
        extendedlogging.remove_all_handlers()
        # wipe temp folder
        folder = TMP_FOLDER
        self.folder = folder
        if os.path.isdir(self.folder):
            shutil.rmtree(self.folder)
        os.mkdir(self.folder)
        # configure logger
        self._configure()

    def _configure(self, **kwargs):
        extendedlogging.configure(filename=LOG_FILE, **kwargs)

    def tearDown(self):
        extendedlogging.remove_all_handlers()

    def _compare(self, filename, expected, regex=False):
        actual = open(filename, 'r').read()
        compare_function = [self.assertEqual, self.assertMultiLineRegexMatch][regex]
        compare_function(expected, actual)

    def _compare_stdout(self, expected):
        actual = sys.stdout.getvalue()
        self.assertEqual(actual, expected)

    def _compare_logfile(self, expected, *args, **kwargs):
        # close the log file
        extendedlogging.remove_all_handlers()
        self._compare(LOG_FILE, expected, *args, **kwargs)

    def _compare_logfile_linecount(self, expected_linecount):
        # close the log file
        extendedlogging.remove_all_handlers()
        actual_linecount = len(open(LOG_FILE, 'r').readlines())
        self.assertEqual(actual_linecount, expected_linecount)

    def assertRegexValid(self, s, msg=None):
        """Assert that provided pattern string is a valid regular expression."""
        try:
            p = re.compile(s)
        except re.error as e:
            standardMsg = 'Invalid pattern \'{}\': {}'.format(s, e)
            self.fail(self._formatMessage(msg, standardMsg))

    def assertMultiLineRegexMatch(self, first, second, msg=None):
        """Assert that two multi-line strings are equal, where the first one contains regular expressions to match against."""
        # this basically combines two methods from unittest: assertMultiLineEqual and assertRegex
        self.assertIsInstance(first, str, 'First argument is not a string')
        self.assertIsInstance(second, str, 'Second argument is not a string')
        firstlines = first.splitlines(keepends=False)
        secondlines = second.splitlines(keepends=False)
        if len(firstlines) != len(secondlines):
            standardMsg = 'Line count mismatch: %d != %d' % (len(firstlines), len(secondlines))
            self.fail(self._formatMessage(msg, standardMsg))
        for it in range(len(firstlines)):
            self.assertRegexValid(firstlines[it], msg='at line %d' % it)
            self.assertRegex(secondlines[it], firstlines[it], msg='at line %d' % it)




if __name__ == '__main__':
    # buffering is required for stdout checks
    unittest.main(module='tests', buffer=True, exit=False)

