from abc import ABC, abstractmethod
from lark import Tree as LarkTree
import networkx as nx
from rgxlog.engine.custom_trees import NetxTree
from collections import deque


class Converter(ABC):
    """
    Abstract class for converters
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    @abstractmethod
    def convert(graph):
        pass


class LarkTreeToNetxTree(Converter):
    """
    Converts a lark tree to a Networkx tree
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    def convert(lark_tree: LarkTree) -> NetxTree:
        new_netx_node = 0
        netx_tree = NetxTree()
        netx_node_to_lark_node = dict()
        q = deque()
        q.append(new_netx_node)
        netx_node_to_lark_node[new_netx_node] = lark_tree
        netx_tree.add_node(new_netx_node, data=lark_tree.data)
        netx_tree.set_root(new_netx_node)
        new_netx_node += 1
        while q:
            cur_netx_node = q.popleft()
            cur_lark_node = netx_node_to_lark_node[cur_netx_node]
            for child_lark_node in cur_lark_node.children:
                if isinstance(child_lark_node, LarkTree):
                    q.append(new_netx_node)
                    netx_node_to_lark_node[new_netx_node] = child_lark_node
                    netx_tree.add_node(new_netx_node, data=child_lark_node.data)
                else:
                    netx_tree.add_node(new_netx_node, value=child_lark_node)
                netx_tree.add_edge(cur_netx_node, new_netx_node)
                new_netx_node += 1
        return netx_tree


class NetxTreeToLarkTreeConverter(Converter):
    """
    Converts a Networkx tree to a Lark tree
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    def convert(netx_tree: NetxTree) -> LarkTree:
        netx_root = netx_tree.get_root()
        netx_data_attr = nx.get_node_attributes(netx_tree, "data")
        netx_value_attr = nx.get_node_attributes(netx_tree, "value")
        lark_tree = LarkTree(netx_data_attr[netx_root], [])
        netx_node_to_lark_node = dict()
        q = deque()
        q.append(netx_root)
        netx_node_to_lark_node[netx_root] = lark_tree
        while q:
            cur_netx_node = q.popleft()
            cur_lark_node = netx_node_to_lark_node[cur_netx_node]
            for child_netx_node in list(netx_tree.successors(cur_netx_node)):
                if child_netx_node in netx_data_attr:
                    child_lark_node = LarkTree(netx_data_attr[child_netx_node], [])
                    cur_lark_node.children.append(child_lark_node)
                    netx_node_to_lark_node[child_netx_node] = child_lark_node
                    q.append(child_netx_node)
                else:
                    assert child_netx_node in netx_value_attr
                    cur_lark_node.children.append(netx_value_attr[child_netx_node])
        return lark_tree
