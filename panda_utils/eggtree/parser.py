import logging
import warnings

import lark_cython
from lark import Lark, Transformer, v_args, Tree

from panda_utils.eggtree.nodes import EggString, EggLeaf, EggBranch, EggTree

__all__ = ["egg_tokenize"]


logger = logging.getLogger("panda_utils.eggtree.parser")


"""
The main types of egg nodes are the following:
String nodes:
<Comment> {  <- EggLeaf (!)
    Some comment here  <- str
}
<Matrix4> {  <- EggLeaf (!)
    1 0 0 0
    0 1 0 0
    0 0 1 0
    0 0 0 1  <- str
}
<Scalar> alpha { dual }  <- EggLeaf (dual: str)

This is a *breaking behavior* from the old parser which had Comment and Matrix4 as EggBranches instead.

Recursive nodes:
<Group> {                 <- EggBranch
    <Vertex> { 1 0 0 0 }  <- EggLeaf
}
<VertexRef> { 20 21 22 23 <Ref> { Cube }}  <- EggBranch (!)
<Texture> some_texture {     <- EggBranch
    name.png                 <- EggString
    <Scalar> alpha { dual }  <- EggLeaf
}
<Group> name {            <- EggBranch
    <VertexPool> Cube {}  <- EggBranch
}
This is a *breaking behavior* from the old parser because <Ref>s will be returned as children.
While we're at here we can abolish EggTrees inside EggBranches. All of this only goes into version 2.0, anyway.
"""
EGG_SYNTAX = r"""
// Whitespace is not important
%import common.WS
%ignore WS

COMMENT: "//" /[^\n]*/
%ignore COMMENT
ML_COMMENT: "/*" /[^*]*/ "*/"
%ignore ML_COMMENT

%import common.ESCAPED_STRING -> QUOTED_STRING
%import common.HEXDIGIT
%import common.SIGNED_NUMBER
NUMBER: /\b(-?(([0-9]+(\.[0-9]*)?)|([0-9]*\.[0-9]+))(e-?[0-9]+)?|[0-9a-fA-F]+|nan|-?(\.#)?inf)\b/

NODE_CHAR: /[a-zA-Z0-9_*$.-]+/
UNQUOTED_STRING: /[^" \t\n\r{}<>]+/

coords: NUMBER+

leaf_contents: QUOTED_STRING
             | coords
             | UNQUOTED_STRING

node_type: NODE_CHAR
maybe_node_name: NODE_CHAR | QUOTED_STRING

node: "<" node_type ">" maybe_node_name "{" node_contents "}"
    | "<" node_type ">" "{" node_contents "}"
node_or_text: node | leaf_contents
node_contents: node_or_text*
tree: node+
"""


@v_args(inline=True)
class TextToEgg(Transformer):
    def tree(self, *t):
        return EggTree(*t)

    def node_type(self, t: lark_cython.Token):
        return t.value

    def maybe_node_name(self, t: lark_cython.Token):
        return t.value.strip('"')

    coord = node_type
    coord_boundary = node_type

    def node(self, *t):
        node_type = t[0]
        node_name = t[1] if len(t) == 3 else ""
        node_value = t[-1]
        if len(node_value.children) == 1:
            if isinstance(node_value.children[0], str):
                return EggLeaf(node_type, node_name, node_value.children[0])
            if isinstance(node_value.children[0], EggString):
                return EggLeaf(node_type, node_name, node_value.children[0].value)
        return EggBranch(
            str(node_type),
            str(node_name),
            [EggString(child) if isinstance(child, str) else child for child in node_value.children],
        )

    def leaf_contents(self, t):
        if isinstance(t, Tree):
            return EggString(" ".join([k.value for k in t.children]))
        return t.value

    def node_or_text(self, t):
        return t


parser = Lark(EGG_SYNTAX, start="tree", parser="lalr", transformer=TextToEgg(), _plugins=lark_cython.plugins)


def egg_tokenize(contents: str) -> EggTree:
    if isinstance(contents, list):
        warnings.warn(
            "egg_tokenize accepts string values now (output of read()) instead of lists (output of readlines()). "
            "Using a list will be unavailable in Panda Utils v3.",
            FutureWarning,
        )
        contents = "\n".join(contents)
    return parser.parse(contents)  # type: ignore
