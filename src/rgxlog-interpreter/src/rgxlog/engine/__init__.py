# TODO: move stuff to diff files and folders later
from abc import ABC, abstractmethod

import networkx as nx


class SymbolTableBase(ABC):
    @abstractmethod
    def add_variable(self, name, data):
        pass

    @abstractmethod
    def remove_variable(self, name):
        pass

    @abstractmethod
    def get_all_variables(self):
        pass

    def __repr__(self):
        print(self.get_all_variables())

    def __str__(self):
        print('Variable\tData')
        for name, data in self.get_all_variables():
            print(f'{name}\t{data}')


class SymbolTable(SymbolTableBase):
    def __init__(self):
        self._var_to_node = {}

    def add_variable(self, name, data):
        self._var_to_node[name] = data

    def remove_variable(self, name):
        del self._var_to_node[name]

    def get_all_variables(self):
        return ((var, data) for var, data in self._var_to_node.items())


class MemoryHeapBase(ABC):
    @abstractmethod
    def collect_garbage(self):
        pass


# TODO: the term graph is itself a heap, what use is there to have a separate
# TODO: structure for it? better just force it to implement heap methods imo
# TODO: i assume some optimizations would not occur on a single node but rather,
# TODO: they would happen on the entire term graph (global optimizations)
# TODO: what interface would be comfy for this purpose?
class TermGraphBase(MemoryHeapBase):
    @abstractmethod
    def add_term(self, name, data):
        pass

    @abstractmethod
    def remove_term(self, name):
        pass

    @abstractmethod
    def get_node_state(self, name):
        # for now, computed / not computed / dirty (?)
        pass

    @abstractmethod
    def get_term_data(self, name):
        # will be called to get an AST and send it to the execution engine
        # or get the result of a node's computation
        pass

    @abstractmethod
    def transform_node_data(self, name, transformer):
        pass

    @abstractmethod
    def transform_graph(self):
        pass


class TermGraph(TermGraphBase):
    def __init__(self):
        self._g = nx.Graph()

    def add_term(self, name, attr: dict):  # attr[state / data]
        # TODO: attr should have data but not state, we set state to not comp
        self._g.add_node(node_for_adding=name, attr=attr)

    def remove_term(self, name):
        self._g.remove_node(name)

    def get_node_state(self, name):
        return self._g.nodes[name]['state']

    def get_term_data(self, name):
        return self._g.nodes[name]['data']

    def transform_node_data(self, name, transformer):
        assert callable(transformer)
        return transformer(self._g.nodes[name]['data'])

    def collect_garbage(self):
        super(self).collect_garbage()

    def transform_graph(self):
        super(self).transform_graph()


class SessionBase(ABC):
    def __init__(self):
        self._st = SymbolTable()
        self._tg = TermGraph()

    @abstractmethod
    def read_state(self):
        pass

    @abstractmethod
    def update_state(self):  # TODO: probably split to several smaller functions
        pass

    def __repr__(self):
        print(repr(self._st))
        print(repr(self._tg))

    def __str__(self):
        print('Symbol Table:')
        print(str(self._st))
        print('Term Graph:')
        print(str(self._tg))


class Session(SessionBase):
    pass


class ExecutionBase:
    pass


class Execution(ExecutionBase):
    pass
