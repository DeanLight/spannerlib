from abc import abstractmethod
import networkx as nx
from enum import Enum


class EvalState(Enum):
    NOT_COMPUTED = 0
    COMPUTED = 1
    DIRTY = 2


class TermGraphBase:

    @abstractmethod
    def add_term(self, **attr):
        """
        add a term to the term graph
        Args:
            **attr: the attributes of the term

        Returns: a term id that refers to the term that was added
        """
        pass

    @abstractmethod
    def get_root_id(self):
        """
        Returns: the term id of the root of the term graph
        """
        pass

    @abstractmethod
    def remove_term(self, term_id):
        """
        removes a term from the term graph
        Args:
            term_id: the id of the term that will be removed
        """
        pass

    @abstractmethod
    def add_dependency_edge(self, dependent_term_id, dependency_term_id, **attr):
        """
        Adds the edge (dependent_term_id, dependency_term_id) to the term graph.
        the edge signifies that the father term is dependent on the son term
        Args:
            dependent_term_id: the dependent term
            dependency_term_id: a term id
            **attr: the attributes for the edge
        """
        pass

    @abstractmethod
    def get_dfs_pre_ordered_term_id_list(self):
        """
        Returns: a list of the term ids generated from a depth-first-search pre-ordering starting at the root
        of the term graph
        """
        pass

    @abstractmethod
    def get_dfs_post_ordered_term_id_list(self):
        """
        Returns: a list of the term ids generated from a depth-first-search post-ordering starting at the root
        of the term graph
        """
        pass

    @abstractmethod
    def get_term_first_order_dependencies(self, term_id):
        """
        Args:
            term_id: a term id

        Returns: a list of the first order dependencies (the "children") of the term
        """
        pass

    @abstractmethod
    def get_term_state(self, term_id):
        """
        Args:
            term_id: a term id

        Returns: the state attribute of the term
        """
        pass

    @abstractmethod
    def get_term_value(self, term_id):
        """
        Args:
            term_id: a term id

        Returns: the value attribute of the term
        """
        pass

    @abstractmethod
    def get_term_type(self, term_id):
        """
        Args:
            term_id: a term id

        Returns: the type attribute of the term
        """
        pass

    @abstractmethod
    def set_term_state(self, term_id, state):
        """
        sets the state attribute of the term
        Args:
            term_id: the term id
            state: the state attribute to be set
        """
        pass

    @abstractmethod
    def set_term_value(self, term_id, value):
        """
        sets the value attribute of the term
        Args:
            term_id: the term id
            value: the value attribute to be set
        """
        pass

    @abstractmethod
    def set_term_type(self, term_id, term_type):
        """
        sets the type attribute of the term
        Args:
            term_id: the term id
            term_type: the type attribute to be set
        """
        pass

    @abstractmethod
    def transform_term_data(self, term_id, transformer):
        pass

    @abstractmethod
    def transform_graph(self, transformer):
        pass

    def __str__(self):
        pass


class NetxTermGraph(TermGraphBase):
    """
    implementation of a term graph using a networkx tree
    """

    def __init__(self):

        # define the graph with 'OrderedDiGraph' to make sure the order of a reported node's children is the same
        # as the order they were added to the graph.
        self._graph = nx.OrderedDiGraph()

        # when a new node is added to the graph, it needs to have an id that was not used before
        # this field will be used to save that id. each time a term is added to the graph, this field
        # will be incremented, providing us with a new unused id
        self._next_term_id = 0

        # create the root of the term graph. it will be used as a source for dfs/bfs
        self._root_id = self._next_term_id
        self.add_term(type="root")

    def add_term(self, **attr):  # attr[state / data]
        # TODO limit to state, value/data, type?
        if 'state' not in attr:
            attr['state'] = EvalState.NOT_COMPUTED

        # get the id for the new term node
        term_id = self._next_term_id
        self._next_term_id += 1

        # add the new term to the graph and return its id
        self._graph.add_node(node_for_adding=term_id, **attr)
        return term_id

    def get_root_id(self):
        return self._root_id

    def remove_term(self, term_id):
        self._graph.remove_node(term_id)

    def add_dependency_edge(self, dependent_term_id, dependency_term_id, **attr):
        # TODO make the ancestor of a non computed term non computed
        self._graph.add_edge(dependent_term_id, dependency_term_id, **attr)

    def get_dfs_pre_ordered_term_id_list(self):
        return nx.dfs_preorder_nodes(self._graph, self._root_id)

    def get_dfs_post_ordered_term_id_list(self):
        return nx.dfs_postorder_nodes(self._graph, self._root_id)

    def get_term_first_order_dependencies(self, term_id):
        return self._graph.successors(term_id)

    def get_term_state(self, term_id):
        return self._graph.nodes[term_id]['state']

    def get_term_value(self, term_id):
        return self._graph.nodes[term_id]['value']

    def get_term_type(self, term_id):
        return self._graph.nodes[term_id]['type']

    def set_term_state(self, term_id, state):
        self._graph.nodes[term_id]['state'] = state

    def set_term_value(self, term_id, value):
        self._graph.nodes[term_id]['value'] = value

    def set_term_type(self, term_id, term_type):
        self._graph.nodes[term_id]['type'] = term_type

    def transform_term_data(self, term_id, transformer):
        return transformer(self._graph.nodes[term_id])

    def transform_graph(self, transformer):
        return transformer.execute(self._graph, self._root_id)

    def _get_node_string(self, node):
        assert node in self._graph.nodes
        assert 'type' in self._graph.nodes[node]
        ret = '(' + str(node) + ') '
        if 'state' in self._graph.nodes[node]:
            state = self._graph.nodes[node]['state']
            if state == EvalState.COMPUTED:
                ret += '(computed) '
            elif state == EvalState.NOT_COMPUTED:
                ret += '(not computed) '
            elif state == EvalState.DIRTY:
                ret += '(dirty) '
            else:
                assert 0
        ret += self._graph.nodes[node]['type']
        if 'value' in self._graph.nodes[node]:
            ret += ': ' + str(self._graph.nodes[node]['value'])
        return ret

    def _pretty(self, node, level, indent_str):
        children = list(self._graph.successors(node))
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
        return ''.join(self._pretty(self._root_id, 0, indent_str))

    def __str__(self):
        return self.pretty()
