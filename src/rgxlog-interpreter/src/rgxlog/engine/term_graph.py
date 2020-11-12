from abc import abstractmethod
import networkx as nx
from enum import Enum


class EvalState(Enum):
    NOT_COMPUTED = 0
    COMPUTED = 1
    DIRTY = 2


class TermGraphBase:

    @abstractmethod
    def add_term(self, data):
        pass

    @abstractmethod
    def get_root(self):
        pass

    @abstractmethod
    def remove_term(self, name):
        pass

    @abstractmethod
    def add_dependency(self, name1, name2, data):
        pass

    @abstractmethod
    def get_term_list_pre_order(self):
        pass

    @abstractmethod
    def get_term_list_post_order(self):
        pass

    @abstractmethod
    def get_node_children(self, name):
        pass

    @abstractmethod
    def get_term_state(self, name):
        pass

    @abstractmethod
    def get_term_value(self, name):
        pass

    @abstractmethod
    def get_term_type(self, name):
        pass

    @abstractmethod
    def set_term_state(self, name, value):
        pass

    @abstractmethod
    def set_term_value(self, name, value):
        pass

    @abstractmethod
    def set_term_type(self, name, value):
        pass

    @abstractmethod
    def transform_term_data(self, name, transformer):
        pass

    @abstractmethod
    def transform_graph(self, transformer):
        pass

    def __str__(self):
        pass


class NetxTermGraph(TermGraphBase):  # , MemoryHeap):
    """implementation of a term graph using a networkx tree"""
    def __init__(self):
        # OrderedDiGraph makes sure the order of a reported node's children is the same as the order they were
        # added to the graph.
        self._g = nx.OrderedDiGraph()
        self._root = 0
        # the root of the whole term graph. will be used as a source for bfs/dfs
        self._g.add_node(node_for_adding=self._root, type="main_root")
        self._new_node_id = 1

    def add_term(self, **attr):  # attr[state / data]
        if 'state' not in attr:
            attr['state'] = EvalState.NOT_COMPUTED
        self._g.add_node(node_for_adding=self._new_node_id, **attr)
        self._new_node_id += 1
        return self._new_node_id - 1

    def get_root(self):
        return self._root

    def remove_term(self, name):
        self._g.remove_node(name)

    def add_dependency(self, name1, name2, **attr):
        assert name1 in self._g.nodes
        assert name2 in self._g.nodes
        self._g.add_edge(name1, name2, **attr)

    def get_term_list_pre_order(self):
        return nx.dfs_preorder_nodes(self._g, self._root)

    def get_term_list_post_order(self):
        return nx.dfs_postorder_nodes(self._g, self._root)

    def get_node_children(self, name):
        return self._g.successors(name)

    def get_term_state(self, name):
        return self._g.nodes[name]['state']

    def get_term_value(self, name):
        return self._g.nodes[name]['value']

    def get_term_type(self, name):
        return self._g.nodes[name]['type']

    def set_term_state(self, name, value):
        self._g.nodes[name]['state'] = value

    def set_term_value(self, name, value):
        self._g.nodes[name]['value'] = value

    def set_term_type(self, name, value):
        self._g.nodes[name]['type'] = value

    def transform_term_data(self, name, transformer):
        return transformer(self._g.nodes[name])

    def transform_graph(self, transformer):
        return transformer.transform(self._g, self._root)

    def _get_node_string(self, node):
        assert node in self._g.nodes
        assert 'type' in self._g.nodes[node]
        ret = '(' + str(node) + ') '
        if 'state' in self._g.nodes[node]:
            state = self._g.nodes[node]['state']
            if state == EvalState.COMPUTED:
                ret += '(computed) '
            elif state == EvalState.NOT_COMPUTED:
                ret += '(not computed) '
            elif state == EvalState.DIRTY:
                ret += '(dirty) '
            else:
                assert 0
        ret += self._g.nodes[node]['type']
        if 'value' in self._g.nodes[node]:
            ret += ': ' + str(self._g.nodes[node]['value'])
        return ret

    def _pretty(self, node, level, indent_str):
        children = list(self._g.successors(node))
        if len(children) == 0:
            return [indent_str * level, self._get_node_string(node), '\n']

        ret = [indent_str * level, self._get_node_string(node), '\n']
        for child_node in children:
            ret += self._pretty(child_node, level + 1, indent_str)

        return ret

    def pretty(self, indent_str='  '):
        """
        prints a representation of the networkx tree.
        Works similarly to lark's pretty() function.
        """
        return ''.join(self._pretty(self._root, 0, indent_str))

    def __str__(self):
        return self.pretty()
