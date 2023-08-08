# This should have used pyparsing but I am lazy
import abc
import functools
import re
from typing import List


class EggTree:
    def __init__(self, *children):
        self.children = list(children)

    def __iadd__(self, other):
        if isinstance(other, list):
            self.children.extend(other)
        else:
            self.children.append(other)
        return self

    def __iter__(self):
        return iter(self.children)

    def __repr__(self):
        return "\n".join(str(child) for child in self.children)

    def findall(self, node_type):
        ans = [x.findall(node_type) for x in self.children]
        return functools.reduce(lambda x, y: x + y, ans, []) if ans else []

    def remove_nodes(self, nodeset):
        if isinstance(nodeset, EggNode):
            nodeset = {nodeset}
        self.children = [x for x in self.children if x not in nodeset]
        for child in self.children:
            child.remove_nodes(nodeset)

    def __getitem__(self, item):
        return self.children[item]


class EggNode(abc.ABC):
    @abc.abstractmethod
    def findall(self, node_type):
        pass

    @abc.abstractmethod
    def remove_nodes(self, nodeset):
        pass

    @abc.abstractmethod
    def get_child(self, index):
        pass


class EggString(EggNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value

    def findall(self, node_type):
        return []

    def remove_nodes(self, nodeset):
        pass

    def get_child(self, index):
        return None


class EggLeaf(EggNode):
    def __init__(self, node_type, node_name, node_value):
        self.node_type = node_type
        self.node_name = (node_name or "").strip()
        self.node_value = node_value

    def __repr__(self):
        if self.node_name:
            return f"<{self.node_type}> {self.node_name.strip()} {{ {self.node_value.strip()} }}"
        return f"<{self.node_type}> {{ {self.node_value.strip()} }}"

    def findall(self, node_type):
        if self.node_type == node_type:
            return [self]
        return []

    def remove_nodes(self, nodeset):
        pass

    def get_child(self, index):
        return None


class EggBranch(EggNode):
    def __init__(self, node_type, node_name, children):
        self.node_type = node_type
        self.node_name = (node_name or "").strip()
        self.children = children

    def __repr__(self):
        if self.node_name:
            preamble = f"<{self.node_type}> {self.node_name} {{"
        else:
            preamble = f"<{self.node_type}> {{"

        child_list = [f"  {child}" for child in self.children]
        child_list = [x.replace("\n", "\n  ") for x in child_list]
        return preamble + "\n" + "\n".join(child_list) + "\n}"

    def findall(self, node_type):
        ans = []
        if self.node_type == node_type:
            ans.append(self)
        for child in self.children:
            ans += child.findall(node_type)
        return ans

    def remove_nodes(self, nodeset):
        self.children = EggTree(*[x for x in self.children if x not in nodeset])
        for child in self.children:
            child.remove_nodes(nodeset)

    def get_child(self, index):
        return self.children[index]

    def add_child(self, child):
        self.children += child


def sanitize_string(val):
    if val and val[0] in "\"'":
        return val[1:-1]
    return val


single_line_leaf_regex = re.compile(r"<([A-Za-z0-9_$*]+)> +([-a-z0-9A-Z_.]+ )?\{ ?(.+) ?}")
preline_regex = re.compile(r"<([A-Za-z0-9_$]+)> +([-a-z0-9A-Z_.<>\" ]+ )?\{([^\n]*)")


def subtree_tokenize(lines: List[str]):
    last_line = lines[-1].strip()
    if len(lines) == 1:
        if last_line.count("}") > 1 and not last_line.startswith("<VertexRef>"):
            parts = [x + "}" for x in last_line.split("}")[:-1]]
            nodes = []
            for part in parts:
                nodes += subtree_tokenize([part])
            return nodes

        match = single_line_leaf_regex.match(last_line)
        if not match:
            raise ValueError(f"subtree_tokenize: Invalid single-line subtree: {lines[0]}")

        final = match.group(3)
        if "}" not in final or match.group(1) == "VertexRef":
            return [EggLeaf(match.group(1), match.group(2), final)]
        return [EggBranch(match.group(1), match.group(2), EggTree(*subtree_tokenize([final])))]

    lines = lines[:-1] + list(last_line)
    if lines[-1] != "}":
        raise ValueError(f"subtree_tokenize: Invalid tree finish: {lines[-1]}")
    preamble = preline_regex.match(lines[0])
    if not preamble:
        raise ValueError(f"subtree_tokenize: Invalid preamble: {lines[0]}")
    append = preamble.group(3)
    if append:
        lines.insert(1, append)
    tree = egg_tokenize([line.strip() for line in lines[1:-1]])
    return [EggBranch(preamble.group(1), preamble.group(2), tree)]


def egg_tokenize(lines: List[str]) -> EggTree:
    tree = EggTree()

    current_indent = 0
    subtree = []
    for line in lines:
        line = line.strip()
        if line.startswith("<") or current_indent:
            current_indent += line.count("{") - line.count("}")
            subtree.append(line)
            if current_indent == 0:
                tree += subtree_tokenize(subtree)
                subtree = []
        else:
            tree += EggString(line)

    if current_indent > 0 or subtree:
        raise ValueError(f"egg_tokenize: Invalid tree finish - indent {current_indent}, subtree {subtree})")
    return tree
