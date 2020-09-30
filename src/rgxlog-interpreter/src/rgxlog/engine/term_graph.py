from abc import abstractmethod

import networkx as nx


# TODO add nx to package deps


# TODO: i assume some optimizations would not occur on a single node but rather,
# TODO: they would happen on the entire term graph (global optimizations)
# TODO: what interface would be comfy for this purpose?
class TermGraphBase:
    @abstractmethod
    def add_term(self, name, data):
        pass

    @abstractmethod
    def remove_term(self, name):
        pass

    @abstractmethod
    def get_term_list(self):
        pass

    @abstractmethod
    def get_term_state(self, name):
        # for now, computed / not computed / dirty (?)
        pass

    @abstractmethod
    def get_term_data(self, name):
        # will be called to get an AST and send it to the execution engine
        # or get the result of a node's computation
        pass

    @abstractmethod
    def transform_term_data(self, name, transformer):
        pass

    @abstractmethod
    def transform_graph(self, transformer):
        pass

    # TODO
    def __repr__(self):
        pass

    # TODO
    def __str__(self):
        pass


class TermGraph(TermGraphBase):  # , MemoryHeap):
    def __init__(self):
        self._g = nx.Graph()

    def add_term(self, name, attr: dict):  # attr[state / data]
        # TODO: attr should have data but not state, we set state to not comp
        # TODO: check if already defined
        self._g.add_node(node_for_adding=name, attr=attr)

    def remove_term(self, name):
        self._g.remove_node(name)

    def get_term_list(self):
        # TODO
        pass

    def get_term_state(self, name):
        return self._g.nodes[name]['state']

    def get_term_data(self, name):
        return self._g.nodes[name]['data']

    def transform_term_data(self, name, transformer):
        return transformer(self._g.nodes[name])

    def transform_graph(self, transformer):
        return transformer(self._g)
