import sys
import os
import unittest

# get system under test
import extendedlogging


class TestAutoLogging(unittest.TestCase):
    TMP_OUTPUT_FILE = '/tmp/test_autologging.txt'

    def _setupLogger(self, level=extendedlogging.TRACE):
        # reset configuration overrides
        extendedlogging.ARRAY_SIZE_LIMIT = None
        extendedlogging.STRING_SIZE_LIMIT = None
        # reset any previous open handlers
        root = extendedlogging.logging.root
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        logfile = TestAutoLogging.TMP_OUTPUT_FILE
        if os.path.isfile(logfile):
            os.remove(logfile)
        extendedlogging.extendedConfig(format='%(levelname)s: %(funcName)s: %(message)s',
            filename=logfile,
            filemode='w',
            level=level)

    def _readLogFile(self):
        return file(TestAutoLogging.TMP_OUTPUT_FILE).read()

    def test_logging_info(self):
        '''Log using standard INFO level.'''
        # setup
        self._setupLogger()
        # run
        extendedlogging.info('hi')
        # verify
        expected_log_content = """INFO: test_logging_info: hi\n"""
        self.assertEqual(self._readLogFile(), expected_log_content)

    def test_trace_function_decorator(self):
        '''Apply tracing decorator to a little function.'''
        # setup
        self._setupLogger()
        @extendedlogging.traced
        def f():
            pass
        # run
        f()
        # verify
        expected_log_content = """TRACE: f: CALL *() **{}\nTRACE: f: RETURN None\n"""
        self.assertEqual(self._readLogFile(), expected_log_content)

    def test_trace_class_decorator(self):
        '''Apply tracing decorator to a little class.'''
        # setup
        self._setupLogger()
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
        expected_log_content = """TRACE: __init__: CALL *('some_argument',) **{}
TRACE: f: CALL *() **{}
TRACE: f: RETURN None
TRACE: __init__: RETURN None
TRACE: g: CALL *() **{}
TRACE: g: RETURN 3
"""
        self.assertEqual(self._readLogFile(), expected_log_content)

    def test_newline_folding(self):
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

    def test_huge_string_as_is(self):
        '''By default, a huge string is logged as is.'''
        # setup
        self._setupLogger()
        huge_string = str(range(100))
        # run
        extendedlogging.log(extendedlogging.TRACE, huge_string)
        # verify
        expected_log_content = "TRACE: test_huge_string_as_is: " + str(range(100)) + "\n"
        self.assertEqual(self._readLogFile(), expected_log_content)

    def test_huge_string_condensed(self):
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




if __name__ == '__main__':
    unittest.main()    
        
