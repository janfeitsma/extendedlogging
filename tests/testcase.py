# system imports
import sys
import os
import re
import unittest



class TestCase(unittest.TestCase):

    def _compare(self, filename, expected, regex=False):
        actual = open(filename, 'r').read()
        compare_function = [self.assertEqual, self.assertMultiLineRegexMatch][regex]
        compare_function(expected, actual)

    def _compare_stdout(self, expected):
        actual = sys.stdout.getvalue()
        self.assertEqual(actual, expected)

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



