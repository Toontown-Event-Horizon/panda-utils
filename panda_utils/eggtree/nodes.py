import abc
import dataclasses
import functools
import warnings
from typing import List, TypeVar, Union


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

    @staticmethod
    def convert_string_to_egg(value):
        value = value.strip()
        if " " in value:
            return f'"{value}"'
        return value


AnyNode = TypeVar("AnyNode", bound=EggNode)


@dataclasses.dataclass(eq=False)
class EggString(EggNode):
    value: str

    def __repr__(self):
        return self.value

    def findall(self, node_type):
        return []

    def remove_nodes(self, nodeset):
        pass

    def get_child(self, index):
        return None


@dataclasses.dataclass(eq=False)
class EggLeaf(EggNode):
    node_type: str
    node_name: Union[str, None]
    node_value: str

    def __repr__(self):
        if self.node_name:
            return f"<{self.node_type}> {self.convert_string_to_egg(self.node_name)} {{ {self.node_value.strip()} }}"
        return f"<{self.node_type}> {{ {self.node_value.strip()} }}"

    def findall(self, node_type):
        if self.node_type == node_type:
            return [self]
        return []

    def remove_nodes(self, nodeset):
        pass

    def get_child(self, index):
        return None


@dataclasses.dataclass(eq=False)
class EggBranch(EggNode):
    node_type: str
    node_name: Union[str, None]
    children: List[AnyNode]

    def __post_init__(self):
        if isinstance(self.children, EggTree):
            warnings.warn(
                "EggTree is no longer needed to create an EggBranch. This option will be removed in Panda Utils v3.",
                FutureWarning,
            )
            self.children = self.children.children

    def __repr__(self):
        if self.node_name:
            preamble = f"<{self.node_type}> {self.convert_string_to_egg(self.node_name)} {{"
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
        self.children = [x for x in self.children if x not in nodeset]
        for child in self.children:
            child.remove_nodes(nodeset)

    def get_child(self, index):
        return self.children[index]

    def add_child(self, child):
        self.children += child


@dataclasses.dataclass(init=False)
class EggTree:
    children: List[AnyNode]

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
