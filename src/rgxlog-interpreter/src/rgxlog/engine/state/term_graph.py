"""
This module contains the implementations of graphs (directed graphs).
"""

from enum import Enum

import networkx as nx
from abc import abstractmethod
from itertools import count
from typing import Set, List, Dict, Iterable

from rgxlog.engine.datatypes.ast_node_types import Relation, Rule

PRETTY_INDENT = " " * 4
ROOT_NODE_ID = "__rgxlog_root"


class EvalState(Enum):
    """
    will be used to determine if a term is computed or not.
    """

    NOT_COMPUTED = "not_computed"
    VISITED = "visited"
    COMPUTED = "computed"

    def __str__(self):
        return self.value


class GraphBase:
    """
    This is an interface for a simple graph.
    """

    @abstractmethod
    def add_node(self, node_id=None, **attr):
        """
        Adds a node to the graph.

        @param node_id: the id of the node (optional).
        @param attr: the attributes of the term.
        @return: a node id that refers to the node that was added.
        """
        pass

    @abstractmethod
    def get_root_id(self):
        """
        @return: the node id of the root of the graph.
        """
        pass

    @abstractmethod
    def remove_node(self, node_id) -> None:
        """
        Removes a ndoe from the graph.

        @param node_id: the id of the node that will be removed.
        """
        pass

    @abstractmethod
    def add_edge(self, father_id, son_id, **attr) -> None:
        """
        Adds the edge (father_id, son_id) to the graph.
        the edge signifies that the father node is dependent on the son node.

        @param father_id: the id of the father node.
        @param son_id: the id of the son node.
        @param attr: the attributes for the edge.
        """
        pass

    @abstractmethod
    def pre_order_dfs_from(self, node_id) -> Iterable:
        """
        @return: an iterable of the node ids generated from a depth-first-search pre-ordering starting at the root
        of the graph.
        """
        pass

    def pre_order_dfs(self) -> Iterable:
        """
        @return: an iterable of the node ids generated from a depth-first-search pre-ordering starting at the root
        of the graph.
        """
        return self.pre_order_dfs_from(self.get_root_id())

    @abstractmethod
    def post_order_dfs_from(self, node_id) -> Iterable:
        """
        @return: an iterable of the node ids generated from a depth-first-search post-ordering starting at the root
        of the graph.
        """
        pass

    def post_order_dfs(self) -> Iterable:
        """
        @return: an iterable of the node ids generated from a depth-first-search post-ordering starting at the root
        of the graph.
        """
        return self.post_order_dfs_from(self.get_root_id())

    @abstractmethod
    def get_children(self, node) -> Iterable:
        """
        In a term graph the children of a node are its dependencies
        this function returns the children of a node.

        @param node: a node id.
        @return: an iterable of the children of the node.
        """
        pass

    @abstractmethod
    def has_node(self, node_id: str) -> bool:
        """
        Checks if node is in the graph.

        @param node_id: the node to look for.
        @return: True if node is in the graph, False otherwise.
        """
        pass

    @abstractmethod
    def set_node_attribute(self, node_id, attr_name: str, attr_value) -> None:
        """
        Sets an attribute of a node.

        @param node_id: the id of the node.
        @param attr_name: the name of the attribute.
        @param attr_value: the value that will be set for the attribute.
        """
        pass

    @abstractmethod
    def get_node_attributes(self, node_id) -> Dict:
        """
        @param node_id: a node id.
        @return: a dict containing the attributes of the node.
        """
        pass

    @abstractmethod
    def _get_node_string(self, node_id) -> str:
        """
        A utility function for __str__.

        @param node_id: a node id.
        @return: a string representation of the node.
        """
        pass

    def _pretty_aux(self, node_id, level: int) -> List[str]:
        """
        A helper function for pretty().

        @param node_id: an id of a term in the term graph.
        @param level: the depth of the term in the tree (used for indentation).
        @return: a list of strings that represents the term and its children.
        """

        # get a representation of the node
        ret = [PRETTY_INDENT * level, self._get_node_string(node_id), '\n']

        if node_id in self._visited_nodes:
            return ret

        self._visited_nodes.add(node_id)

        # get a representation of the node's children
        for child_id in self.get_children(node_id):
            ret += self._pretty_aux(child_id, level + 1)

        return ret

    def pretty(self):
        """
        Prints a representation of the networkx tree.
        Works similarly to lark's pretty() function.

        example:
        for a computed query term of id 4 "?A(X)", this method will print
        (4) (computed) query: A(X)
        """

        self._visited_nodes = set()
        return ''.join(self._pretty_aux(self.get_root_id(), 0))

    def __str__(self):
        return self.pretty()

    def __getitem__(self, node_id):
        return self.get_node_attributes(node_id)


class NetxGraph(GraphBase):
    """
    Implementation of a graph using a networkx graph.
    The official documentation for networkx can be found here: https://networkx.org/documentation/stable/index.html.
    A basic tutorial for networkx https://networkx.org/documentation/stable//reference/introduction.html.
    """

    def __init__(self):

        # define the graph with 'DiGraph' to make sure the order of a reported node's children is the same
        # as the order they were added to the graph.
        self._graph = nx.DiGraph()

        # when a new node is added to the graph, it needs to have an id that was not used before
        # this field will serve as a counter that will provide a new term id
        self._node_id_counter = count()

        # create the root of the graph. it will be used as a source for dfs/bfs
        self._root_id = self.add_node(node_id=ROOT_NODE_ID, type="root")

        # used for keep track of the printed nodes (in pretty function)
        self._visited_nodes = None

    def add_node(self, node_id=None, **attr):
        # get the id for the new node (if id wasn't passed)
        node_id = next(self._node_id_counter) if node_id is None else node_id

        # add the new node to the graph and return its id
        self._graph.add_node(node_for_adding=node_id, **attr)
        return node_id

    def get_root_id(self):
        return self._root_id

    def remove_node(self, node_id) -> None:
        self._graph.remove_node(node_id)

    def add_edge(self, father_id, son_id, **attr) -> None:

        # assert that both nodes are in the term graph
        if father_id not in self._graph.nodes:
            raise ValueError(f'father term of id {father_id} is not in the term graph')
        if son_id not in self._graph.nodes:
            raise ValueError(f'son term of id {son_id} is not in the term graph')

        # add an edge that represents the dependency of the father node on the son node
        self._graph.add_edge(father_id, son_id, **attr)

    def pre_order_dfs_from(self, node_id) -> Iterable:
        return nx.dfs_preorder_nodes(self._graph, node_id)

    def post_order_dfs_from(self, node_id) -> Iterable:
        return nx.dfs_postorder_nodes(self._graph, node_id)

    def get_children(self, node_id):
        return list(self._graph.successors(node_id))

    def set_node_attribute(self, node_id, attr_name: str, attr_value) -> None:
        self._graph.nodes[node_id][attr_name] = attr_value

    def get_node_attributes(self, node_id) -> Dict:
        return self._graph.nodes[node_id].copy()

    def _get_node_string(self, node_id) -> str:
        node_attrs = self.get_node_attributes(node_id)

        # get a string of the node's value (if it exists)
        if 'value' in node_attrs:
            term_value_string = f": {node_attrs['value']}"
        else:
            term_value_string = ''

        # create a string representation of the node and return it
        term_string = f"({node_id}) {term_value_string}"
        return term_string

    def has_node(self, node_id) -> bool:
        return self._graph.has_node(node_id)


class NetxStateGraph(NetxGraph):
    """
    This is a wrapper to NetxGraph that stores a state and type for each node in the graph.
    (This class will be the base class of the computation term graph and the parse graph while NetxGrpah
    will be the base of dependency graph).
    """

    def add_node(self, node_id=None, **attr):
        # assert the node has a type
        if 'type' not in attr:
            raise Exception("cannot add a term without a type")

        # if the node does not have a 'state' attribute, give it a default 'not computed' state
        if 'state' not in attr:
            attr['state'] = EvalState.NOT_COMPUTED

        return super(NetxStateGraph, self).add_node(node_id, **attr)

    def add_edge(self, father_id, son_id, **attr) -> None:
        super(NetxStateGraph, self).add_edge(father_id, son_id, **attr)

        # if the son node is not computed, mark all of its ancestor as not computed as well
        son_term_state = self._graph.nodes[son_id]['state']
        if son_term_state is EvalState.NOT_COMPUTED:
            # get all of the ancestors by reversing the graph and using a dfs algorithm from the son term
            ancestors_graph = nx.dfs_tree(self._graph.reverse(), source=son_id)
            ancestors_ids = list(ancestors_graph.nodes)
            # mark all of the ancestors as not computed
            for ancestor_id in ancestors_ids:
                self._graph.nodes[ancestor_id]['state'] = EvalState.NOT_COMPUTED

    def _get_node_string(self, node_id) -> str:
        node_attrs = self.get_node_attributes(node_id)

        # get a string of the node's value (if it exists)
        if 'value' in node_attrs:
            term_value_string = f": {node_attrs['value']}"
        else:
            term_value_string = ''

        # create a string representation of the node and return it
        term_string = f"({node_id}) ({node_attrs['state']}) {node_attrs['type']}{term_value_string}"
        return term_string


class DependencyGraph(NetxGraph):
    """
    A class that represents the dependencies between rule relation.
    We use this class to find out which relations are mutually recursive.

    Example:
        Let's look on the following RGXLog program-

        new A(int)
        B(X) <- A(X)
        C(X) <- A(X)
        B(X) <- C(X)  # B is dependent on C
        C(X) <- B(X)  # C is dependent on D
        D(X) <- C(X)  # D is dependent on C

        In this case the dependency graph will be:
        Nodes = {A, B, C, D} (all the rule relations)
        Edges = {(B, C), (B, C), (D, C)}

    @note: In order to find mutually recursive rule relation we just need to compute the strongly connected components
           of the graph (all the relations in a certain component are mutually recursive).
    """

    def __init__(self):
        super().__init__()

    def _add_relation(self, relation: Relation) -> None:
        """
        Adds relation to dependency graph.

        @param relation: the relation to add (should be rule relation).
        @return: the id of the relation node.
        """

        if self.has_node(relation.relation_name):
            return

        self.add_node(node_id=relation.relation_name)
        self.add_edge(self._root_id, relation.relation_name)

    def is_dependent(self, head_rel: Relation, body_rel: Relation) -> bool:
        """
        Finds out whether the head relation is dependent in body relation.

        @param head_rel: the head relation.
        @param body_rel: a body relation.
        @return: True if they are dependent, False otherwise.
        """

        common_free_vars = set(head_rel.term_list).intersection(body_rel.term_list)
        return self.has_node(body_rel.relation_name) and len(common_free_vars) > 0

    def add_dependencies(self, head_relation: Relation, body_relations: Set[Relation]) -> None:
        """
        Adds all the dependencies of the rule to the graph.

        @param head_relation: the head relation of the rule.
        @param body_relations: a set of rule's body relations.
        """

        self._add_relation(head_relation)

        for body_relation in body_relations:
            # add edge only if there is at least one free var in relation
            if self.is_dependent(head_relation, body_relation):
                edge = (head_relation.relation_name, body_relation.relation_name)
                num_of_edges = 1 + self._graph.get_edge_data(*edge, default={"amount": 0})["amount"]
                self.add_edge(*edge, amount=num_of_edges)

    def remove_relation(self, relation_name: str) -> None:
        """
        Removes the relation node from the dependency graph.

        @param relation_name: the name of the relation to remove.
        """

        self._graph.remove_node(relation_name)

    def remove_rule(self, rule: Rule) -> None:
        """
        Removes the dependencies of the rule from the graph.

        @param rule: the rule to remove.
        """

        head_relation = rule.head_relation

        body_relations, _ = rule.get_relations_by_type()
        for relation in body_relations:
            if self.is_dependent(head_relation, relation):
                edge = (head_relation.relation_name, relation.relation_name)
                num_of_edges = self._graph.get_edge_data(*edge)["amount"]
                if num_of_edges == 1:
                    self._graph.remove_edge(*edge)
                else:
                    self.add_edge(*edge, amount=num_of_edges - 1)

    def get_mutually_recursive_relations(self, relation_name: str) -> Set[str]:
        """
        Finds all relations that are mutually recursive with the input relation.

        @param relation_name: the name of the relation.
        @return: a set of relations names (including the input relation).
        """

        scc = nx.strongly_connected_components(self._graph)

        for component in scc:
            if relation_name in component:
                names_component = set(component)
                return names_component

    def _get_node_string(self, node_id: str) -> str:
        # for nicer printing format
        return node_id

    def __str__(self):
        return self.__class__.__name__ + " is:\n" + super().__str__()


class ComputationTermGraph(NetxStateGraph):
    """
    A wrapper to NetxStateGraph that adds support to relations.
    We suggest to go over AddRulesToComputationTermGraph's docstring (that explains about the structure of the
    computation term graph and some terminology) before going over this class.
    """

    def __init__(self):
        super().__init__()
        # for each rule stores it's relevant nodes
        self._rule_to_nodes = dict()
        self._dependency_graph = DependencyGraph()

    def add_rule(self, rule: Rule, nodes: Set[str]) -> None:
        """
        Adds rule to term graph dict.

        @param rule: the rule to add.
        @param nodes: all the nodes in the graph that are unique to the rule
                      (and thus should be removed if the rule is removed).
        """

        self._rule_to_nodes[str(rule)] = (rule, nodes)

    def _is_node_in_use(self, node_id: str) -> bool:
        """
        Checks if id node has parents or it's the root node.

        @param node_id: id of a node.
        @return: true if the node is has parents (if node is root the we also return true).
        """
        if node_id == self.get_root_id():
            return True

        # all the nodes are connected to global root
        predecessors_number = len(list(self._graph.predecessors(node_id)))
        return predecessors_number > 1

    def _get_all_rules_with_head(self, relation_name: str) -> List[str]:
        """
        Find all the rule with rule head.

        @raise ValueError: if relation name doesn't exist in the graph.
        @param relation_name: name of the relation.
        @return: a list of rules with rule head.
        """

        rules = [rule for rule in self._rule_to_nodes if rule.startswith(relation_name)]

        if len(rules) == 0:
            # if we are here than we didn't find the given relation
            raise ValueError(f"There are no relation with head '{relation_name}' in the term graph.")

        return rules

    def remove_rules_with_head(self, rule_head_name: str) -> None:
        """
        Removes all rules with given rule head from the term graph.

        @param rule_head_name: a relation name
        """

        rules = self._get_all_rules_with_head(rule_head_name)
        if self._is_node_in_use(rule_head_name):
            raise ValueError(f"The rule head'{rule_head_name}' can't be deleted since it's used in another existing "
                             f"rule.")

        for rule in rules:
            self.remove_rule(rule)

    def remove_rule(self, rule: str) -> bool:
        """
        Removes rule from term graph.

        @param rule: the rule to remove. unlike add_rule, here rule should be string as it is a user input.
        @raise Exception if the rule doesn't exist in the term graph
        @return: true if the head relation was deleted, false otherwise.
        """

        if rule not in self._rule_to_nodes:
            raise ValueError(f"The rule '{rule}' was never registered "
                             f"(you can run 'print_all_rules' to see all the registered rules)")

        actual_rule, nodes = self._rule_to_nodes[rule]
        rule_name = actual_rule.head_relation.relation_name
        union_node = self.get_relation_union_node(rule_name)

        is_last_rule_path = len(list(self.get_children(union_node))) == 1
        is_rule_used = self._is_node_in_use(rule_name)

        # check if something is connected to the root and the root is going to be deleted (this shouldn't happen)
        if is_last_rule_path and is_rule_used:
            raise RuntimeError(f"The rule '{rule}' can't be deleted since '{rule_name}' is used in another existing "
                               f"rule.")

        self._graph.remove_nodes_from(nodes)
        del self._rule_to_nodes[rule]

        self._dependency_graph.remove_rule(actual_rule)

        if is_last_rule_path:
            self._graph.remove_nodes_from((rule_name, union_node))
            self._dependency_graph.remove_relation(rule_name)
            return True

        return False

    def print_all_rules(self) -> None:
        """
        Prints all the registered rules.
        """
        print("Printing all the rules:")
        for i, rule in enumerate(self._rule_to_nodes):
            print(f"\t{i + 1}. {rule}")

    def add_relation(self, relation: Relation) -> int:
        """
        Adds the relation to the graph. if it's already inside nothing is done.

        @param relation: the relation to add.
        @note: we assume the relation is rule relation and not declared relation.
        @return: returns the relation node id if is_rule is false.
                 otherwise returns the relation child node id (union node).
        """
        relation_name = relation.relation_name
        if self.has_node(relation_name):
            return self.get_relation_union_node(relation_name)

        self.add_node(node_id=relation_name, type="rule_rel", value=relation)
        self.add_edge(self._root_id, relation_name)
        union_id: int = self.add_node(type="union")
        self.add_edge(relation_name, union_id)

        return union_id

    def get_relation_union_node(self, relation_name: str) -> int:
        """
        @param relation_name: name of a relation.
        @return: the union node of the given relation.
        """

        union_id,  = self.get_children(relation_name)  # relation has only one child (the union node).
        return union_id

    def add_dependencies(self, head_relation: Relation, body_relations: Set[Relation]) -> None:
        """@see documentation of add_dependencies in DependencyGraph"""
        self._dependency_graph.add_dependencies(head_relation, body_relations)

    def get_mutually_recursive_relations(self, relation_name: str) -> Set[str]:
        """@see documentation of get_mutually_recursive_relations in DependencyGraph"""
        return self._dependency_graph.get_mutually_recursive_relations(relation_name)

    def __str__(self):
        return super().__str__() + "\n" + str(self._dependency_graph)
