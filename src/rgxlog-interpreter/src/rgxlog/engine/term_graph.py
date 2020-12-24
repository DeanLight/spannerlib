from abc import abstractmethod
import networkx as nx
from enum import Enum


class EvalState(Enum):
    """
    will be used to determine if a term is computed or not
    """
    NOT_COMPUTED = 0
    COMPUTED = 1


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
        # this field will be used to save that id. each time a term is added to the graph, this field
        # will be incremented, providing us with a new unused id
        self._next_term_id = 0

        # create the root of the term graph. it will be used as a source for dfs/bfs
        self._root_id = self._next_term_id
        self.add_term(type="root")

    def add_term(self, **attr):

        # assert the the term has a type
        if 'type' not in attr:
            raise Exception("cannot add a term without a type")

        # if the term does not have a 'state' attribute, give it a default 'not computed' state
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

        # assert that both terms are in the term graph
        if dependent_term_id not in self._graph.nodes:
            raise Exception(f'dependent term of id {dependent_term_id} is not in the term graph')
        if dependency_term_id not in self._graph.nodes:
            raise Exception(f'dependency term of id {dependency_term_id} is not in the term graph')

        # add an edge that represents the dependency
        self._graph.add_edge(dependent_term_id, dependency_term_id, **attr)

        # if the dependency term is not computed, mark all of its ancestor as not computed as well
        dependency_term_state = self._graph.nodes[dependency_term_id]['state']
        if dependency_term_state is EvalState.NOT_COMPUTED:
            # get all of the ancestors by reversing the graph and using a dfs algorithm from the dependency term
            dependent_ancestors_graph = nx.dfs_tree(self._graph.reverse(), source=dependency_term_id)
            dependent_ancestors_ids = list(dependent_ancestors_graph.nodes)
            # mark all of the ancestors as not computed
            for node_id in dependent_ancestors_ids:
                self._graph.nodes[node_id]['state'] = EvalState.NOT_COMPUTED

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

    def __get_term_string(self, term_id):
        """
        an utility function for pretty()
        Args:
            term_id: a term id

        Returns: a string representation of the term
        """

        # get a string of the term state
        term_state = self.get_term_state(term_id)
        if term_state is EvalState.COMPUTED:
            term_state_string = "computed"
        else:
            term_state_string = "not computed"

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

    def __pretty_aux(self, term_id, level):
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
            return [indent_str * level, self.__get_term_string(term_id), '\n']

        # the term node has children, get its representation along with its children's representations
        ret = [indent_str * level, self.__get_term_string(term_id), '\n']
        for child_id in children_ids:
            ret += self.__pretty_aux(child_id, level + 1)

        return ret

    def pretty(self):
        """
        prints a representation of the networkx tree.
        Works similarly to lark's pretty() function.

        example:
        for a computed query term of id 4 "?A(X)", this method will print
        (4) (computed) query: A(X)
        """
        return ''.join(self.__pretty_aux(self._root_id, 0))

    def __str__(self):
        return self.pretty()
