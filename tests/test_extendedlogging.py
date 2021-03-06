# system imports
import sys
import os
import shutil
import time
import unittest
import threading

# own imports
import testcase
import extendedlogging

# constants
TMP_FOLDER = '/tmp/test_extendedlogging'
LOG_FILE = os.path.join(TMP_FOLDER, 'logfile.log')
PATH_TO_DEMOS = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'demos')




class TestExtendedLogging(testcase.TestCase):

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

    def _template_trace_function_decorator_timestamp(self, check_digits=6, **kwargs):
        # setup
        self._configure(tracing=True, **kwargs)
        # run
        @extendedlogging.traced
        def f():
            pass
        f()
        # verify
        t = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{' + str(check_digits) + '}' # timestamp with millisecond or microsecond resolution
        empty = '{}'
        # python2 backwards compatibility: cannot use f-string, so do a poor-man explicit replace
        expected_content = """{t}:TRACE:test_extendedlogging.py,\d+:f:CALL \*\(\) \*\*{empty}
{t}:TRACE:test_extendedlogging.py,\d+:f:RETURN None
""".replace('{t}', t).replace('{empty}', empty)
        self._compare_logfile(expected_content, regex=True)
        self._compare_stdout("")

    def test_trace_function_decorator_timestamp(self):
        '''Apply tracing decorator to a little function. It shall only appear in logfile, not console, default with timestamps (microsecond resolution).'''
        self._template_trace_function_decorator_timestamp(check_digits=6)

    def test_timestamp_custom_millisecond_resolution(self):
        '''Check that tracing timestamps can also be logged with traditional reduced millisecond resolution.'''
        self._template_trace_function_decorator_timestamp(check_digits=3, file_timestamp_resolution=3)

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

    def _template_newline_folding(self, expected_logfile_linecount, **kwargs):
        # setup
        self._configure(tracing=True, file_format='%(levelname)s:%(funcName)s: %(message)s', **kwargs)
        # run
        string_with_newlines = """This is line 1.
        This is line 2,
        finally we have line 3."""
        # run
        extendedlogging.info(string_with_newlines)
        # verify
        expected_stdout = "INFO   :_template_newline_folding:" + string_with_newlines + "\n"
        self._compare_stdout(expected_stdout) # 3 lines, as original
        self._compare_logfile_linecount(expected_logfile_linecount) # could be 3 lines folded into 1

    def test_newline_folding(self):
        '''By default, newlines should be folded into a single line in the tracing file.'''
        expected_logfile_linecount = 1
        self._template_newline_folding(expected_logfile_linecount) # fold_newlines=True

    def test_newline_folding_disabled(self):
        '''Optionally newlines are left unfolded in the tracing file.'''
        expected_logfile_linecount = 3
        self._template_newline_folding(expected_logfile_linecount, fold_newlines=False)

    def _template_trace_it(self, trace_args, **kwargs):
        # setup
        self._configure(tracing=True, **kwargs)
        # run
        @extendedlogging.traced
        def f(trace_args):
            pass
        f(trace_args)

    def test_huge_string_default_cut(self):
        '''By default, a huge string in tracing is cut off at some point.'''
        s = str(list(range(1000)))
        self.assertEqual(len(s), 4890)
        self._template_trace_it(s)
        self.assertEqual(self._get_logfile_max_linesize(), 1000)

    def test_huge_string_optional_longer_lines(self):
        '''Optionally, the tracing string cutoff limit can be increased.'''
        s = str(list(range(1000)))
        self.assertEqual(len(s), 4890)
        self._template_trace_it(s, string_size_limit=10000)
        max_linesize = self._get_logfile_max_linesize()
        self.assertGreater(max_linesize, 4000)
        self.assertLess(max_linesize, 5000)

    def test_huge_array_default_inner_truncation(self):
        '''By default, a huge array in tracing is truncated on the interior, like numpy repr().'''
        arg = list(range(100))
        max_linesize = self._template_trace_it(arg, file_format='%(levelname)s:%(funcName)s: %(message)s')
        # verify
        expected_content = """TRACE:f: CALL *([0, 1, 2, 3, 4, '...', 95, 96, 97, 98, 99],) **{}
TRACE:f: RETURN None
"""
        self._compare_logfile(expected_content)

    def test_huge_array_full(self):
        '''Optionally, huge array cutting can be disabled.'''
        arg = list(range(100))
        max_linesize = self._template_trace_it(arg, file_format='%(levelname)s:%(funcName)s: %(message)s', array_size_limit=100)
        # verify
        expected_content = """TRACE:f: CALL *([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99],) **{}
TRACE:f: RETURN None
"""
        self._compare_logfile(expected_content)

    def test_huge_array_end_truncation(self):
        '''Optionally, huge array cutting can be set to tail truncation instead of inner truncation.'''
        arg = list(range(100))
        max_linesize = self._template_trace_it(arg, file_format='%(levelname)s:%(funcName)s: %(message)s', array_tail_truncation=True)
        # verify
        expected_content = """TRACE:f: CALL *([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, '...'],) **{}
TRACE:f: RETURN None
"""
        self._compare_logfile(expected_content)

    def test_recursive_array_trunctation(self):
        '''Array truncation even works recursively, on lists and tuples.'''
        arg = (['s1',('a','b','c'),'drop','e1'], 'keep', 'drop', ('s2',['d',range(100),'f'],None,'e2'))
        max_linesize = self._template_trace_it(arg, file_format='%(levelname)s:%(funcName)s: %(message)s', array_size_limit=3)
        # verify
        expected_content = """TRACE:f: CALL *((['s1', ('a', 'b', 'c'), '...', 'e1'], 'keep', '...', ('s2', ['d', range(0, 100), 'f'], '...', 'e2')),) **{}
TRACE:f: RETURN None
"""
        if sys.version_info[0] < 3: # python2 backwards compatibility
            expected_content = expected_content.replace("range(0, 100)", "[0, 1, '...', 99]")
        self._compare_logfile(expected_content)

    def test_trace_error_handling_disabled(self):
        '''Tracing can be incomplete when an exception occurs.'''
        expected_content = self._expected_error_handling(closed=False)
        self._template_trace_error_handling(expected_content, error_handling=False)

    def _expected_error_handling(self, closed=False):
        result = """TRACE:recurse: CALL *(4,) **{}
TRACE:recurse: CALL *(3,) **{}
TRACE:recurse: CALL *(2,) **{}
TRACE:recurse: CALL *(1,) **{}
TRACE:recurse: RETURN None
TRACE:recurse: RETURN None
"""
        if closed:
            result += """ERROR:recurse: something went terribly wrong at n=3
TRACE:recurse: RETURN ERROR
TRACE:recurse: RETURN ERROR
"""
        return result

    def test_trace_error_handling_enabled(self):
        '''If so configured, exceptions shall be logged with ERROR events and tracing shall be closed.'''
        expected_content = self._expected_error_handling(closed=True)
        self._template_trace_error_handling(expected_content, error_handling=True)

    def _template_trace_error_handling(self, expected_content, **kwargs):
        # setup
        self._configure(tracing=True, file_format='%(levelname)s:%(funcName)s: %(message)s', **kwargs)
        # run
        class ExpectedException(Exception):
            pass
        @extendedlogging.traced
        class myclass():
            def recurse(self, n):
                if n > 1:
                    self.recurse(n-1)
                if n == 3:
                    raise ExpectedException('something went terribly wrong at n=' + str(n))
        # run
        c = myclass()
        try:
            c.recurse(4) # will raise expected exception
        except ExpectedException as e:
            pass
        # verify
        self._compare_logfile(expected_content)

    def test_multithreading(self):
        '''When multiple threads are active, then trace events are logged with their name.'''
        expected_content = """# format: %(levelname)s:%(threadName)s:%(funcName)s: %(message)s
TRACE:Thread-1:run: CALL *('thread1', 0.2) **{}
TRACE:Thread-2:run: CALL *('thread2', 0.2) **{}
TRACE:Thread-1:run: RETURN None
TRACE:Thread-2:run: RETURN None
"""
        # setup
        self._configure(tracing=True, file_format='%(levelname)s:%(funcName)s: %(message)s', thread_names=True)
        numthreads = 2
        @extendedlogging.traced
        def run(name, duration):
            time.sleep(duration)
        # run
        threads = []
        for it in range(numthreads):
            threads.append(threading.Thread(target=run, args=('thread'+str(it+1), 0.2)))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        # verify
        self._compare_logfile(expected_content, sort=True) # sort needed to avoid race condition on threads start/finish

    def test_cfg_consistency(self):
        '''The configuration from main must also apply to imported modules using extendedlogging.'''
        # setup
        expected_content = self._expected_error_handling(closed=True)
        # run
        suppress_stderr = '2>/dev/null 1>&2'
        cmd = 'python {}/demo_cfg_consistency_main.py {}'.format(PATH_TO_DEMOS, suppress_stderr)
        r = os.system(cmd)
        # verify
        self.assertTrue(r != 0) # expected exception, ignore
        self._compare(extendedlogging.DEFAULT_LOG_FILE, expected_content)

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

    def _compare_logfile(self, expected, *args, **kwargs):
        # close the log file
        extendedlogging.remove_all_handlers()
        self._compare(LOG_FILE, expected, *args, **kwargs)

    def _compare_logfile_linecount(self, expected_linecount):
        # close the log file
        extendedlogging.remove_all_handlers()
        actual_linecount = len(open(LOG_FILE, 'r').readlines())
        self.assertEqual(actual_linecount, expected_linecount)

    def _get_logfile_max_linesize(self, strip=True):
        # close the log file
        extendedlogging.remove_all_handlers()
        result = 0
        for line in open(LOG_FILE, 'r').readlines():
            if strip:
                line = line.strip()
            result = max(result, len(line))
        return result




if __name__ == '__main__':
    # buffering is required for stdout checks
    unittest.main(buffer=True, exit=False)

