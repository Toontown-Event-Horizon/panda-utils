import pathlib
import unittest

from panda_utils.eggtree import eggparse
from panda_utils.eggtree.eggparse import EggString, EggBranch, EggLeaf


class EggtreeTest(unittest.TestCase):
    def assertInvolution(self, data, tree):
        self.assertEqual("\n".join(data), repr(tree).strip())

    def test_recursion(self):
        data = [
            "<Group> a {",
            "  <Group> b {",
            "    <Scalar> alpha { dual }",
            "  }",
            "}",
        ]
        tree = eggparse.egg_tokenize(data)
        groups = tree.findall("Group")
        self.assertListEqual(groups, [tree.children[0], tree.children[0].children[0]])
        self.assertEqual(groups[0].node_name, "a")
        self.assertEqual(groups[1].node_name, "b")
        scalars = tree.findall("Scalar")
        self.assertListEqual(scalars, [tree.children[0].children[0].children[0]])
        self.assertEqual(scalars[0].node_name, "alpha")
        self.assertEqual(scalars[0].node_value, "dual")
        self.assertInvolution(data, tree)

    def test_spaces(self):
        data = [
            '<Group> "Named Group" {',
            "  <Scalar> alpha { dual }",
            "}",
        ]
        tree = eggparse.egg_tokenize(data)
        groups = tree.findall("Group")
        self.assertListEqual(groups, [tree.children[0]])
        self.assertEqual(groups[0].node_name, "Named Group")
        self.assertInvolution(data, tree)

        old_egg = str(tree)
        data[0] = '<Group> Named Group {'
        tree = eggparse.egg_tokenize(data)
        self.assertEqual(old_egg, str(tree), "quotes don't cause egg file to change")

    def test_recursive_lookup_and_multiple_nodes(self):
        data = [
            '<Group> a {',
            "  <Scalar> alpha { dual }",
            "}",
            '<Group> b {',
            "  <Scalar> alpha { blend }",
            "}",
        ]
        tree = eggparse.egg_tokenize(data)
        b_group = [node for node in tree.findall("Group") if node.node_name == "b"][0]
        scalars = b_group.findall("Scalar")
        self.assertEqual(len(scalars), 1)
        self.assertEqual(scalars[0].node_value, "blend")
        self.assertInvolution(data, tree)

    def test_removal(self):
        data = [
            '<Group> a {',
            "  <Scalar> alpha { dual }",
            "}",
            '<Group> b {',
            "  <Scalar> alpha { blend }",
            "}",
        ]
        tree = eggparse.egg_tokenize(data)

        other_data = data[0:1] + [""] + data[2:4] + [""] + data[5:6]
        other_tree = "\n".join(other_data)

        all_scalars = {node for node in tree.findall("Scalar")}
        tree.remove_nodes(all_scalars)
        self.assertEqual(str(tree), other_tree)

    def test_modification(self):
        data = [
            '<Group> a {',
            "  <Scalar> alpha { dual }",
            "}",
            '<Group> b {',
            "  <Scalar> alpha { blend }",
            "}",
        ]
        tree = eggparse.egg_tokenize(data)

        other_data = data[0:4] + ["  <Scalar> alpha { dual }"] + data[5:6]
        other_tree = "\n".join(other_data)

        all_scalars = [node for node in tree.findall("Scalar")]
        for scalar in all_scalars:
            scalar.node_value = "dual"
        self.assertEqual(str(tree), other_tree)

    def test_yabeecube(self):
        with open(pathlib.Path(__file__).parent / "yabee_cube.egg") as f:
            data = f.readlines()

        tree = eggparse.egg_tokenize(data)
        # This will not be an involution, because the tree is sanitized
        # But we can check that the tree is exported properly by making random checks
        # there are 24 vertices in the yabee cube due to merging not being a thing
        self.assertEqual(len(tree.findall("Vertex")), 24)
        self.assertEqual(len(tree.findall("UV")), 24)
        self.assertEqual(len(tree.findall("RGBA")), 24)
        # there are 6 sides in a cube
        self.assertEqual(len(tree.findall("Polygon")), 6)
        self.assertEqual(len(tree.findall("VertexRef")), 6)
        # There are <Ref> entries which are not nodes, because they're recursively nested inside VertexRef
        self.assertEqual(len(tree.findall("Ref")), 0)

        # now for vertices
        vertex0 = tree.findall("Vertex")[0]
        v0c = vertex0.children.children
        self.assertEqual(len(v0c), 3)
        # coordinates
        self.assertIsInstance(v0c[0], EggString)
        # rgba
        self.assertEqual(v0c[1].node_value, "1 1 1 1")
        self.assertIsInstance(v0c[1], EggLeaf)
        # uv
        self.assertEqual(v0c[2].node_name, "UVMap")
        self.assertIsInstance(v0c[2], EggBranch)

        reverted_tree = str(tree)
        self.assertIn("1.0 0.0 0.0 0.0", reverted_tree, "transforms are reverted correctly")
        self.assertNotIn('"1.0 0.0 0.0 0.0"', reverted_tree, "and without syntax errors related to quotes")
