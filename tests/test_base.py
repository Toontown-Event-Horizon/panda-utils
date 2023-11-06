import sys
import unittest


class ImprovedTestSuite(unittest.TestSuite):
    def run(self, result, debug=False):
        max_length = 0
        for test in self:
            if isinstance(test, ImprovedTestSuite) and test._tests:
                first_test = test._tests[0]
                max_length = max(max_length, len(first_test.__class__.__name__))

        for index, test in enumerate(self):
            if isinstance(test, ImprovedTestSuite) and test._tests:
                first_test = test._tests[0]
                if index > 0:
                    sys.stdout.write("\n")
                test_name = first_test.__class__.__name__
                sys.stdout.write(test_name + " " * (1 + max_length - len(test_name)))
                sys.stdout.write(" ")
                sys.stdout.flush()
            if result.shouldStop:
                break
            test(result)
            if self._cleanup:
                self._removeTestAtIndex(index)
        return result


class ImprovedTestLoader(unittest.TestLoader):
    suiteClass = ImprovedTestSuite
