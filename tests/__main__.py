import unittest

from tests.eggtree import *  # noqa: F401
from tests.pipeline import *  # noqa: F401
from tests.test_base import ImprovedTestLoader

unittest.main(testLoader=ImprovedTestLoader())
