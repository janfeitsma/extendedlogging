# system imports
import sys
import os
import re
import unittest



class TestCase(unittest.TestCase):

    def _compare(self, filename, expected, regex=False, sort=False):
        actual = open(filename, 'r').read()
        compare_function = None
        if sort:
            if regex:
                raise NotImplementedError('combining sort and regex option')
            else:
                compare_function = self.assertMultiLineSortedEqual
        else:
            if regex:
                compare_function = self.assertMultiLineRegexMatch
            else:
                compare_function = self.assertMultiLineEqual
        compare_function(expected, actual)

    def _compare_stdout(self, expected):
        actual = sys.stdout.getvalue()
        self.assertEqual(actual, expected)

    def _splitlines(self, s):
        if sys.version_info[0] < 3: # python2 backwards compatibility
            return s.splitlines()
        # python3
        return s.splitlines(keepends=False)

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
        firstlines = self._splitlines(first)
        secondlines = self._splitlines(second)
        if len(firstlines) != len(secondlines):
            standardMsg = 'Line count mismatch: %d != %d' % (len(firstlines), len(secondlines))
            self.fail(self._formatMessage(msg, standardMsg))
        for it in range(len(firstlines)):
            self.assertRegexValid(firstlines[it], msg='at line %d' % it)
            if sys.version_info[0] < 3: # python2 backwards compatibility
                asserter = self.assertRegexpMatches
            else:
                asserter = self.assertRegex
            asserter(secondlines[it], firstlines[it], msg='at line %d' % it)

    def assertMultiLineSortedEqual(self, first, second, msg=None):
        """Assert that two multi-line strings are equal after sorting."""
        self.assertIsInstance(first, str, 'First argument is not a string')
        self.assertIsInstance(second, str, 'Second argument is not a string')
        firstlines = sorted(self._splitlines(first))
        secondlines = sorted(self._splitlines(second))
        if len(firstlines) != len(secondlines):
            standardMsg = 'Line count mismatch: %d != %d' % (len(firstlines), len(secondlines))
            self.fail(self._formatMessage(msg, standardMsg))
        for it in range(len(firstlines)):
            self.assertEqual(firstlines[it], secondlines[it], msg='at (sorted) line %d' % it)

