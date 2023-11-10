"""
Old parser was in this file, but we're using the new parser instead.

This is used for partial compatibility purposes,
and we're giving out warnings until this file is phased out completely.
"""
import warnings

from panda_utils.eggtree.parser import egg_tokenize
from panda_utils.eggtree.nodes import EggString, EggBranch, EggLeaf, EggTree

__all__ = ["egg_tokenize", "EggString", "EggBranch", "EggLeaf", "EggTree", "sanitize_string"]

warnings.warn("panda_utils.eggtree.eggparse is phased out and will be removed in Panda Utils v3", FutureWarning)


def sanitize_string(val):
    warnings.warn("panda_utils.eggtree.eggparse.sanitize_string will be removed in Panda Utils v3", FutureWarning)
    if val and val[0] in "\"'":
        return val[1:-1]
    return val
