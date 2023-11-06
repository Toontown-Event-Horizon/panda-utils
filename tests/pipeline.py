import pathlib
import unittest

from panda_utils.assetpipeline.commons import AssetContext
from panda_utils.assetpipeline.imports import ALL_ACTIONS
from panda_utils.eggtree import eggparse


class PipelineTest(unittest.TestCase):
    def make_context(self, tree) -> AssetContext:
        ctx = AssetContext(pathlib.Path(), "", "")
        ctx.eggs = {"test.egg": tree}
        return ctx

    def run_operator(self, ctx: AssetContext, name, *args, **kwargs):
        callback = ALL_ACTIONS[name]
        callback(ctx, *args, **kwargs)
        return ctx.eggs["test.egg"]

    def test_collide(self):
        eggfile = [
            "<Group> my_name {",
            "  <Group> my_name {",
            "  }",
            "}",
        ]
        tree = eggparse.egg_tokenize(eggfile)
        context = self.make_context(tree)
        tree = self.run_operator(context, "collide", group_name="my_name")
        collides = tree.findall("Collide")
        self.assertEqual(len(collides), 1)
        second_group = tree.findall("Group")[1]
        self.assertEqual(len(second_group.findall("Collide")), 0)
        collide = collides[0]
        self.assertEqual(collide.node_value, "Sphere keep descend")

    def test_collide_fnmatch(self):
        eggfile = [
            "<Group> group1 {",
            "}",
            "<Group> group2 {",
            "}",
            "<Group> group3 {",
            "}",
            "<Group> group3 {",
            "}",
            "<Group> outsider {",
            "}",
        ]
        tree = eggparse.egg_tokenize(eggfile)
        context = self.make_context(tree)
        tree = self.run_operator(context, "collide", group_name="group*")
        first, second, third, dupl_third, outsider = tree.findall("Group")
        self.assertEqual(len(first.findall("Collide")), 1)
        self.assertEqual(len(second.findall("Collide")), 1)
        self.assertEqual(len(third.findall("Collide")), 1)
        self.assertEqual(len(dupl_third.findall("Collide")), 0)
        self.assertEqual(len(outsider.findall("Collide")), 0)
