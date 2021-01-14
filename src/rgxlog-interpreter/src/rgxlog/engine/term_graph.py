"""
this module contains the implementations of term graphs
"""

from abc import abstractmethod
import networkx as nx
from enum import Enum
from itertools import count


class EvalState(Enum):
    """
    will be used to determine if a term is computed or not
    """

    NOT_COMPUTED = "not_computed"
    COMPUTED = "computed"

    def __str__(self):
        return self.value


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
    def add_edge(self, father_id, son_id, **attr):
        """
        Adds the edge (father_id, son_id) to the term graph.
        the edge signifies that the father term is dependent on the son term
        Args:
            father_id: the id of the father term
            son_id: the id of the son term
            **attr: the attributes for the edge
        """
        pass

    @abstractmethod
    def pre_order_dfs(self):
        """
        Returns: an iterable of the term ids generated from a depth-first-search pre-ordering starting at the root
        of the term graph
        """
        pass

    @abstractmethod
    def post_order_dfs(self):
        """
        Returns: an iterable of the term ids generated from a depth-first-search post-ordering starting at the root
        of the term graph
        """
        pass

    @abstractmethod
    def get_children(self, term_id):
        """
        in a term graph the children of a term are its dependencies
        this function returns the children of a term

        Args:
            term_id: a term id

        Returns: an iterable of the children of the term.
        """
        pass

    @abstractmethod
    def set_term_attribute(self, term_id, attr_name, attr_value):
        """
        sets an attribute of a term

        Args:
            term_id: the id of the term
            attr_name: the name of the attribute
            attr_value: the value that will be set for the attribute
        """
        pass

    @abstractmethod
    def get_term_attributes(self, term_id) -> dict:
        """
        Args:
            term_id: a term id

        Returns: a dict containing the attributes of the term
        """
        pass

    def __str__(self):
        pass


class NetxTermGraph(TermGraphBase):
    """
    implementation of a term graph using a networkx graph
    the official documentation for networkx can be found here: https://networkx.org/documentation/stable/index.html
    a basic tutorial for networkx https://networkx.org/documentation/stable//reference/introduction.html
    """

    def __init__(self):

        # define the graph with 'OrderedDiGraph' to make sure the order of a reported node's children is the same
        # as the order they were added to the graph.
        self._graph = nx.OrderedDiGraph()

        # when a new node is added to the graph, it needs to have an id that was not used before
        # this field will serve as a counter that will provide a new term id
        self._term_id_counter = count()

        # create the root of the term graph. it will be used as a source for dfs/bfs
        self._root_id = self.add_term(type="root")

    def add_term(self, **attr):

        # assert the the term has a type
        if 'type' not in attr:
            raise Exception("cannot add a term without a type")

        # if the term does not have a 'state' attribute, give it a default 'not computed' state
        if 'state' not in attr:
            attr['state'] = EvalState.NOT_COMPUTED

        # get the id for the new term node
        term_id = next(self._term_id_counter)

        # add the new term to the graph and return its id
        self._graph.add_node(node_for_adding=term_id, **attr)
        return term_id

    def get_root_id(self):
        return self._root_id

    def remove_term(self, term_id):
        self._graph.remove_node(term_id)

    def add_edge(self, father_id, son_id, **attr):

        # assert that both terms are in the term graph
        if father_id not in self._graph.nodes:
            raise Exception(f'father term of id {father_id} is not in the term graph')
        if son_id not in self._graph.nodes:
            raise Exception(f'son term of id {son_id} is not in the term graph')

        # add an edge that represents the dependency of the father term on the son term
        self._graph.add_edge(father_id, son_id, **attr)

        # if the son term is not computed, mark all of its ancestor as not computed as well
        son_term_state = self._graph.nodes[son_id]['state']
        if son_term_state is EvalState.NOT_COMPUTED:
            # get all of the ancestors by reversing the graph and using a dfs algorithm from the son term
            ancestors_graph = nx.dfs_tree(self._graph.reverse(), source=son_id)
            ancestors_ids = list(ancestors_graph.nodes)
            # mark all of the ancestors as not computed
            for ancestor_id in ancestors_ids:
                self._graph.nodes[ancestor_id]['state'] = EvalState.NOT_COMPUTED

    def pre_order_dfs(self):
        return nx.dfs_preorder_nodes(self._graph, self._root_id)

    def post_order_dfs(self):
        return nx.dfs_postorder_nodes(self._graph, self._root_id)

    def get_children(self, term_id):
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

    def set_term_attribute(self, term_id, attr_name, attr_value):
        self._graph.nodes[term_id][attr_name] = attr_value

    def get_term_attributes(self, term_id) -> dict:
        return self._graph.nodes[term_id].copy()

    def _get_term_string(self, term_id):
        """
        an utility function for pretty()
        Args:
            term_id: a term id

        Returns: a string representation of the term
        """

        # get a string of the term state
        term_state_string = str(self.get_term_state(term_id))

        # get the term type string
        term_type_string = self.get_term_type(term_id)

        # get a string of the term's value (if it exists)
        if 'value' in self._graph.nodes[term_id]:
            term_value_string = f": {self._graph.nodes[term_id]['value']}"
        else:
            term_value_string = ''

        # create a string representation of the term and return it
        term_string = f'({term_id}) ({term_state_string}) {term_type_string}{term_value_string}'
        return term_string

    def _pretty_aux(self, term_id, level):
        """
        a helper function for pretty()

        Args:
            term_id: an id of a term in the term graph
            level: the depth of the term in the tree (used for indentation)

        Returns: a list of strings that represents the term and its children
        """
        indent_str = '  '
        children_ids = list(self._graph.successors(term_id))

        if len(children_ids) == 0:
            # the term node has no children, return its representation
            return [indent_str * level, self._get_term_string(term_id), '\n']

        # the term node has children, get its representation along with its children's representations
        ret = [indent_str * level, self._get_term_string(term_id), '\n']
        for child_id in children_ids:
            ret += self._pretty_aux(child_id, level + 1)

        return ret

    def pretty(self):
        """
        prints a representation of the networkx tree.
        Works similarly to lark's pretty() function.

        example:
        for a computed query term of id 4 "?A(X)", this method will print
        (4) (computed) query: A(X)
        """
        return ''.join(self._pretty_aux(self._root_id, 0))

    def __str__(self):
        return self.pretty()
