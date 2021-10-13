"""
This module contains the implementations of graphs (directed graphs).

The graphs we use when executing commands are called `term_graph`, `parse_graph`, and `dependency_graph`. the parse
graph is an abstract syntax tree. it contains nodes which represent commands, like `add_fact`, 'rule', 'query',
etc. In order to compute rule nodes, or compute query nodes, we use the term graph.

The term graph is holding the connection between all the relations and rules in the program, for more description read
TermGraph's docstring.

The dependency graph stores dependencies between relations in the program, it is used by the term graph to recognize
mutually recursive relations. for more information read DependencyGraph's docstring.
"""
from collections import OrderedDict
from enum import Enum

import networkx as nx
from abc import ABC, abstractmethod, ABCMeta
from itertools import count
from typing import Set, List, Dict, Iterable, Union, Optional, OrderedDict as OrderedDictType, no_type_check, Any, Sequence

from rgxlog.engine.datatypes.ast_node_types import Relation, Rule, IERelation
from rgxlog.engine.utils.general_utils import get_input_free_var_names, get_output_free_var_names, \
    get_free_var_to_relations_dict

PRETTY_INDENT = " " * 4
ROOT_NODE_ID = "__rgxlog_root"
ROOT_TYPE = "root"
TYPE = "type"
STATE = "state"
VALUE = "value"


class EvalState(Enum):
    """
    will be used to determine if a term is computed or not.
    """

    NOT_COMPUTED = "not_computed"
    VISITED = "visited"
    COMPUTED = "computed"

    def __str__(self) -> str:
        return self.value


class TermNodeType(Enum):
    """
    will be used to represent type of term graph nodes.
    """

    SELECT = "select"
    JOIN = "join"
    PROJECT = "project"
    UNION = "union"
    CALC = "calc"
    RULE_REL = "rule_rel"
    GET_REL = "get_rel"

    def __str__(self) -> str:
        return self.value


class GraphBase(ABC):
    """
    This is an interface for a simple graph.
    """

    NodeIdType = Union[int, str]

    def __init__(self) -> None:
        self._visited_nodes: Set = set()

    @abstractmethod
    def add_node(self, node_id: Optional[NodeIdType] = None, **attr: Dict) -> NodeIdType:
        """
        Adds a node to the graph.

        @param node_id: the id of the node (optional).
        @param attr: the attributes of the term.
        @return: a node id that refers to the node that was added.
        """
        pass

    @abstractmethod
    def get_root_id(self) -> NodeIdType:
        """
        @return: the node id of the root of the graph.
        """
        pass

    @abstractmethod
    def remove_node(self, node_id: NodeIdType) -> None:
        """
        Removes a ndoe from the graph.

        @param node_id: the id of the node that will be removed.
        """
        pass

    @abstractmethod
    def add_edge(self, father_id: NodeIdType, son_id: NodeIdType, **attr: Dict) -> None:
        """
        Adds the edge (father_id, son_id) to the graph.
        the edge signifies that the father node is dependent on the son node.

        @param father_id: the id of the father node.
        @param son_id: the id of the son node.
        @param attr: the attributes for the edge.
        """
        pass

    @abstractmethod
    def pre_order_dfs_from(self, node_id: NodeIdType) -> Iterable[NodeIdType]:
        """
        @return: an iterable of the node ids generated from a depth-first-search pre-ordering starting at the root
        of the graph.
        """
        pass

    def pre_order_dfs(self) -> Iterable[NodeIdType]:
        """
        @return: an iterable of the node ids generated from a depth-first-search pre-ordering starting at the root
        of the graph.
        """
        return self.pre_order_dfs_from(self.get_root_id())

    @abstractmethod
    def post_order_dfs_from(self, node_id: NodeIdType) -> Iterable[NodeIdType]:
        """
        @return: an iterable of the node ids generated from a depth-first-search post-ordering starting at the root
        of the graph.
        """
        pass

    def post_order_dfs(self) -> Iterable[NodeIdType]:
        """
        @return: an iterable of the node ids generated from a depth-first-search post-ordering starting at the root
        of the graph.
        """
        return self.post_order_dfs_from(self.get_root_id())

    @abstractmethod
    def get_children(self, node_id: NodeIdType) -> Iterable[NodeIdType]:
        """
        In a term graph the children of a node are its dependencies
        this function returns the children of a node.

        @param node_id: a node id.
        @return: an iterable of the children of the node.
        """
        pass

    def get_child(self, node_id: NodeIdType) -> NodeIdType:
        """
        @param node_id: a node id.
        @return: the child of the node.
        """

        children = list(self.get_children(node_id))
        if len(children) == 1:
            return children[0]

        raise RuntimeError(f"Expected one child, but node has {len(children)} children.")

    @abstractmethod
    def get_parents(self, node_id: NodeIdType) -> Iterable[NodeIdType]:
        """
        @param node_id: a node id.
        @return: the parents (predecessors) of the node.
        """

    def get_parent(self, node_id: NodeIdType) -> NodeIdType:
        """
        @param node_id: a node id.
        @return: the parent of the node.
        """

        parents = list(self.get_parents(node_id))
        if len(parents) == 1:
            return parents[0]

        raise RuntimeError(f"Expected one parent, but node has {len(parents)} parents.")

    @abstractmethod
    def is_contains_node(self, node_id: NodeIdType) -> bool:
        """
        Checks if node is in the graph.

        @param node_id: the node to look for.
        @return: True if node is in the graph, False otherwise.
        """
        pass

    @abstractmethod
    def set_node_attribute(self, node_id: NodeIdType, attr_name: str, attr_value: Any) -> None:
        """
        Sets an attribute of a node.

        @param node_id: the id of the node.
        @param attr_name: the name of the attribute.
        @param attr_value: the value that will be set for the attribute.
        """
        pass

    @abstractmethod
    def get_node_attributes(self, node_id: NodeIdType) -> Dict[str, Any]:
        """
        @param node_id: a node id.
        @return: a dict containing the attributes of the node.
        """
        pass

    @abstractmethod
    def _get_node_string(self, node_id: NodeIdType) -> str:
        """
        A utility function for __str__.

        @param node_id: a node id.
        @return: a string representation of the node.
        """
        pass

    def get_all_nodes_with_attributes(self, sub_graph_root: Optional[NodeIdType] = None, **attributes: Any) -> Iterable[NodeIdType]:
        """
        @param attributes: all the attributes name and values to look for..
        @param sub_graph_root: the sub-graph root. if set to None then we search in the entire graph.
        @return: all nodes that contains all the attributes inside the sub-graph
        """

        root = self.get_root_id() if sub_graph_root is None else sub_graph_root
        node_ids = self.post_order_dfs_from(root)

        def is_node_contains_all_attributes(node_id: GraphBase.NodeIdType) -> bool:
            node_attrs = self.get_node_attributes(node_id)
            return all(item in node_attrs.items() for item in attributes.items())

        return list(filter(is_node_contains_all_attributes, node_ids))

    def _pretty_aux(self, node_id: NodeIdType, level: int) -> List[str]:
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

    def pretty(self) -> str:
        """
        Prints a representation of the networkx tree.
        Works similarly to lark's pretty() function.

        example:
        for a computed query term of id 4 "?A(X)", this method will print
        (4) (computed) query: A(X)
        """

        self._visited_nodes = set()
        return ''.join(self._pretty_aux(self.get_root_id(), 0))

    def __str__(self) -> str:
        return self.pretty()

    def __getitem__(self, node_id: NodeIdType) -> Dict:
        return self.get_node_attributes(node_id)


class NetxGraph(GraphBase):
    """
    Implementation of a graph using a networkx graph.
    The official documentation for networkx can be found here: https://networkx.org/documentation/stable/index.html.
    A basic tutorial for networkx https://networkx.org/documentation/stable//reference/introduction.html.
    """

    def __init__(self) -> None:
        super().__init__()
        # define the graph with 'DiGraph' to make sure the order of a reported node's children is the same
        # as the order they were added to the graph.
        self._graph = nx.DiGraph()

        # when a new node is added to the graph, it needs to have an id that was not used before
        # this field will serve as a counter that will provide a new term id
        self._node_id_counter: count[int] = count()

        # create the root of the graph. it will be used as a source for dfs/bfs
        self._root_id = self.add_node(node_id=ROOT_NODE_ID, type=ROOT_TYPE)

        # used for keep track of the printed nodes (in pretty function)
        self._visited_nodes = set()

    def add_node(self, node_id: Optional[GraphBase.NodeIdType] = None, **attr: Any) -> GraphBase.NodeIdType:
        # get the id for the new node (if id wasn't passed)
        node_id = next(self._node_id_counter) if node_id is None else node_id

        # add the new node to the graph and return its id
        self._graph.add_node(node_for_adding=node_id, **attr)
        return node_id

    def get_root_id(self) -> GraphBase.NodeIdType:
        return self._root_id

    def remove_node(self, node_id: GraphBase.NodeIdType) -> None:
        self._graph.remove_node(node_id)

    def add_edge(self, father_id: GraphBase.NodeIdType, son_id: GraphBase.NodeIdType, **attr: Any) -> None:

        # assert that both nodes are in the term graph
        if father_id not in self._graph.nodes:
            raise ValueError(f'father node of id {father_id} is not in the graph')
        if son_id not in self._graph.nodes:
            raise ValueError(f'son node of id {son_id} is not in the graph')

        # add an edge that represents the dependency of the father node on the son node
        self._graph.add_edge(father_id, son_id, **attr)

    def pre_order_dfs_from(self, node_id: GraphBase.NodeIdType) -> Iterable[GraphBase.NodeIdType]:
        return nx.dfs_preorder_nodes(self._graph, node_id)

    def post_order_dfs_from(self, node_id: GraphBase.NodeIdType) -> Iterable[GraphBase.NodeIdType]:
        return nx.dfs_postorder_nodes(self._graph, node_id)

    def get_children(self, node_id: GraphBase.NodeIdType) -> Sequence[GraphBase.NodeIdType]:
        return list(self._graph.successors(node_id))

    def set_node_attribute(self, node_id: GraphBase.NodeIdType, attr_name: str, attr_value: Any) -> None:
        self._graph.nodes[node_id][attr_name] = attr_value

    def get_node_attributes(self, node_id: GraphBase.NodeIdType) -> Dict[str, Any]:
        return self._graph.nodes[node_id].copy()

    def _get_node_string(self, node_id: GraphBase.NodeIdType) -> str:
        node_attrs = self.get_node_attributes(node_id)

        # get a string of the node's value (if it exists)
        if VALUE in node_attrs:
            term_value_string = f": {node_attrs[VALUE]}"
        else:
            term_value_string = ''

        # create a string representation of the node and return it
        term_string = f"({node_id}) {term_value_string}"
        return term_string

    def is_contains_node(self, node_id: GraphBase.NodeIdType) -> bool:
        return self._graph.has_node(node_id)

    def get_parents(self, node_id: GraphBase.NodeIdType) -> Iterable[GraphBase.NodeIdType]:
        return self._graph.predecessors(node_id)


class NetxStateGraph(NetxGraph):
    """
    This is a wrapper to NetxGraph that stores a state and type for each node in the graph.
    (This class will be the base class of the term graph and the parse graph while NetxGraph
    will be the base of dependency graph).
    """

    def __init__(self) -> None:
        super().__init__()

    def add_node(self, node_id: Optional[GraphBase.NodeIdType] = None, **attr: Any) -> GraphBase.NodeIdType:
        # assert the node has a type
        if TYPE not in attr:
            raise Exception("cannot add a node without a type")

        # if the node does not have a 'state' attribute, give it a default 'not computed' state
        if STATE not in attr:
            attr[STATE] = EvalState.NOT_COMPUTED

        return super(NetxStateGraph, self).add_node(node_id, **attr)

    def add_edge(self, father_id: GraphBase.NodeIdType, son_id: GraphBase.NodeIdType, **attr: Any) -> None:
        super(NetxStateGraph, self).add_edge(father_id, son_id, **attr)

        # if the son node is not computed, mark all of its ancestor as not computed as well
        son_term_state = self._graph.nodes[son_id][STATE]
        if son_term_state is EvalState.NOT_COMPUTED:
            # get all of the ancestors by reversing the graph and using a dfs algorithm from the son term
            ancestors_graph = nx.dfs_tree(self._graph.reverse(), source=son_id)
            ancestors_ids = list(ancestors_graph.nodes)
            # mark all of the ancestors as not computed
            for ancestor_id in ancestors_ids:
                self._graph.nodes[ancestor_id][STATE] = EvalState.NOT_COMPUTED

    def _get_node_string(self, node_id: GraphBase.NodeIdType) -> str:
        node_attrs = self.get_node_attributes(node_id)

        # get a string of the node's value (if it exists)
        if VALUE in node_attrs:
            term_value_string = f": {node_attrs[VALUE]}"
        else:
            term_value_string = ''

        # create a string representation of the node and return it
        term_string = f"({node_id}) ({node_attrs[STATE]}) {node_attrs[TYPE]}{term_value_string}"
        return term_string


class DependencyGraph(NetxGraph):
    """
    A class that represents the dependencies between rule relation.
    We use this class to find out which relations are mutually recursive.
    Each rule relation in the program is represented by a node in this graph - the id of this node is the relation name.

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

    def __init__(self) -> None:
        super().__init__()

    def _add_relation(self, relation: Relation) -> None:
        """
        Adds relation to dependency graph.

        @param relation: the relation to add (should be rule relation).
        @return: the id of the relation node.
        """

        if self.is_contains_node(relation.relation_name):
            return

        self.add_node(node_id=relation.relation_name)
        self.add_edge(self._root_id, relation.relation_name)

    def is_dependent(self, head_rel: Relation, body_rel: Relation) -> bool:
        """
        Finds out whether the head relation is dependent in body relation, i.e. there is an edge from head_rel node to
        body_rel node).

        Example:
            A(X, Y) <- B(X, Y), C(X, Y)
            B(X, Y) < A(X, Y)

            is_dependent(A, B), is_dependent(A, C) and is_dependent(B, A) will return True.
            On the other hand, is_dependent(C, A) will return False.

        @param head_rel: the head relation.
        @param body_rel: a body relation.
        @return: True if they are dependent, False otherwise.
        """

        if head_rel.relation_name == body_rel.relation_name:
            return False

        common_free_vars = set(head_rel.term_list).intersection(body_rel.term_list)
        return self.is_contains_node(body_rel.relation_name) and len(common_free_vars) > 0

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
        names_component, = filter(lambda component: relation_name in component, scc)
        return set(names_component)

    def _get_node_string(self, node_id: GraphBase.NodeIdType) -> str:
        # for nicer printing format
        return str(node_id)

    def is_relation_in_use(self, relation_name: str) -> bool:
        """
        Checks if the relation is used by other existing rules.

        @param relation_name: name of the relation.
        @return: true if the node is has parents (if node is root the we also return true).
        """
        # all the nodes are connected to global root
        predecessors_number = len(list(self._graph.predecessors(relation_name)))
        return predecessors_number > 1

    def __str__(self) -> str:
        return self.__class__.__name__ + " is:\n" + super().__str__()


class TermGraphBase(NetxStateGraph, metaclass=ABCMeta):
    """
    A wrapper to NetxStateGraph that adds utility functions which are independent
    of the structure of the term graph.
    """

    def __init__(self) -> None:
        super().__init__()
        # for each rule stores it's relevant nodes
        self._rule_to_nodes: Dict = dict()
        self._dependency_graph = DependencyGraph()

    @abstractmethod
    def add_rule_to_term_graph(self, rule: Rule) -> None:
        """
        Adds the rule to the term graph.
        This function is responsible for the structure of the term graph.

        @param rule: the rule to add.
        """
        pass

    @abstractmethod
    def remove_rule(self, rule: str) -> bool:
        """
        Removes rule from the term graph.
        This function depends on the structure of the term graph.

        @param rule: the rule to remove.
        @note: the rule is in string format and must be exactly equal the the original rule (i.e.,  if you want to
               delete the rule A(X) <-B(X), you mast pass A(X) <- B(X) and not A(Y) <- B(Y))
        @return: Whether the deletion of the rule succeeded.
        """
        pass

    def add_rule_node(self, rule: Rule, nodes: Set[str]) -> None:
        """
        Adds rule to term graph dict.

        @param rule: the rule to add.
        @param nodes: all the nodes in the graph that are unique to the rule
                      (and thus should be removed if the rule is removed).
        """

        self._rule_to_nodes[str(rule)] = (rule, nodes)

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
        if self._dependency_graph.is_relation_in_use(rule_head_name):
            raise ValueError(f"The rule head '{rule_head_name}' can't be deleted since it's used in another existing "
                             f"rule.")

        for rule in rules:
            self.remove_rule(rule)

    def print_all_rules(self, head: Optional[str]) -> None:
        """
        Prints all the registered rules.
        """

        if head is None:
            print("Printing all the rules:")
        else:
            print(f"Printing all the rules with head {head}:")

        i = 0
        for rule, _ in self._rule_to_nodes.values():
            if head is None or rule.head_relation.relation_name == head:
                print(f"\t{i + 1}. {rule}")
                i += 1

    def get_mutually_recursive_relations(self, relation_name: str) -> Set[str]:
        """@see documentation of get_mutually_recursive_relations in DependencyGraph"""
        return self._dependency_graph.get_mutually_recursive_relations(relation_name)

    def __str__(self) -> str:
        return super().__str__() + "\n" + str(self._dependency_graph)


class TermGraph(TermGraphBase):
    """
       This class transforms each rule node into an execution graph and adds it to the term graph.

       The purpose of the term graph is to store relationships about the following entities:
           1. The rule head.
           2. The body rule relations.
           3. The body base relations and ie relations.
           4. All the computation paths of the rule head.

       Lets look on the following RGXLog program:
           new A(int, int)
           new B(int, int)
           C(X, Y) <- A(X, Y)
           D(X, Y) <- C(X, Y)
           D(X, Y) <- A(X, 1), B(X, Y), ID(X) -> (Y)  # ID is some ie function

       We will explain the meaning of the 4 entities w.r.t the rules of D:
           1. The rule head is: D(X, Y)
           2. The body relations are: C(X, Y) in the first rule (there are None in the second rule).
           3. The base relations are: A(X, 1) and B(X, Y) in the second rule (there are None in the first rule).
           4. The computation paths of the rule are the paths of first rule and second rule.

       The structure of the term graph:

           * Each rule relation has a node in the term graph, we call this node 'rule_rel node'.
             Every rule_rel node is connected to a global root.

           * The rule_rel node is connected to a node we call 'union_node'.

           * The union_node is connected to all the relation's computation paths.

           * Each computation path starts with a node we call 'project_node' that projects the columns of the relation it
             gets (the project_node is connected to the union_node).

           * Under the project_node, there is a node we call 'join_node' that joins all the body relations of the rule.
             There are specials cases when this node isn't used:
               - there is only one relation in the rule's body.
               - all the body relation don't have free variables.

           * Each ie relation in the body of the rule is connected to the join node by a node we call 'calc_node'.
             This node is connected to another join node that connects all the ie relation's bounding relations.

           * Each rule relation in the body relation is connected to the join node by a node we call 'get_rel node'.
             The get_rel node is connected to the corresponding rule root.

           * Each base relation is connected to the join node.

           * In case the is relation with same free var (e.g. A(X, X)) or relation with some constant value (e.g. A(1, x))
             we use a node we call 'select_node' that deals with filtering tuples form the relation. The select node is
             connected to the join node and the get_rel node is connected to the select node.

       For the RGXLog program above, the term graph will be:
           global root

               rule_rel node (of C)
                   union node
                       project node
                           get_rel node (get A)  @note: there isn't join node since there is only one body relation.

               rule_rel node (of D)
                   union node
                       project node
                           get_rel node (get C)  @note: there isn't join node since there is only one body relation.
                               rule_rel node (of C)

                       project node
                           join node (join A, B and ID)
                               get_rel node (get B)
                               select_node (select from A)
                                   get_rel node (get A)
                               calc node (of ID)
                                   join node (join A and B)
                                       get_rel node (get B)         @note: this get_rel node is the same one from above.
                                       select_node (select from A)  @note: this select node is the same one from above.
                                           get_rel node (get A)
       """

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def _compute_bounding_graph(relations: Set[Relation], ie_relations: Set[IERelation]) -> \
            OrderedDictType[IERelation, Set[Union[Relation, IERelation]]]:
        """
        This function gets body relations of a rule and computes for each ie relation the relations that bound it.
        @note: In some cases ie relation is bounded by other ie relation.
                e.g. A(X) <- B(Y), C(Z) -> (X), D(Y) -> (Z); in this example C is bounded only by D.

        @param relations: set of the regular relations in the rule body.
        @param ie_relations: set of the ie relations in the rule body.
        @return: a dictionary that maps each ie function to a set of it's bounding relations.
        """

        # holds the ie relation that are bounded
        bounded_ie_relations: Set[IERelation] = set()

        # maps each ie relation to it's bounding relations
        bounding_graph = OrderedDict()

        def find_bounding_relations_of_ie_function(ie_rel: IERelation) -> (
                Optional[Set[Union[Relation, IERelation]]]):
            """
            Finds all the relation that are already bounded that bind the ie relation.

            @param ie_rel: the ie relation to bound.
            @return: set of the bounding relations.
            """

            bounded_vars: Set[str] = set()
            bounding_relations_ = set()  # the trailing underscore is used to avoid shadowing the outer scope
            ie_input_terms = get_input_free_var_names(ie_rel)

            # iterate over all the bounded relations
            for relation in (relations | bounded_ie_relations):
                rel_terms = get_output_free_var_names(relation)
                # check if the relation and the ie relation have some common free vars
                mutual_vars = rel_terms.intersection(ie_input_terms)
                if len(mutual_vars) > 0:
                    bounding_relations_.add(relation)
                    bounded_vars = bounded_vars.union(mutual_vars)

            # check whether all ie relation's free vars are bounded
            if bounded_vars == ie_input_terms:
                return bounding_relations_
            else:
                # the ie relation can't be bounded yet
                return None

        # The function will eventually stop since the rule is safe.
        while True:
            # find the unbounded ie relations
            unbounded_ie_relations = ie_relations.difference(bounded_ie_relations)
            if len(unbounded_ie_relations) == 0:
                # all the ie relation are bounded
                break

            for ie_relation in unbounded_ie_relations:
                bounding_relations = find_bounding_relations_of_ie_function(ie_relation)
                if bounding_relations is not None:
                    # we managed to bind the ie relation
                    bounding_graph[ie_relation] = bounding_relations
                    bounded_ie_relations.add(ie_relation)

        return bounding_graph

    def add_relation(self, relation: Relation) -> GraphBase.NodeIdType:
        """
        Adds the relation to the graph. if it's already inside nothing is done.

        @param relation: the relation to add.
        @note: we assume the relation is rule relation and not declared relation.
        @return: returns the relation node id if is_rule is false.
                 otherwise returns the relation child node id (union node).
        """

        relation_name = relation.relation_name
        if self.is_contains_node(relation_name):
            return self.get_relation_union_node(relation_name)

        self.add_node(node_id=relation_name, type=TermNodeType.RULE_REL, value=relation)
        self.add_edge(self.get_root_id(), relation_name)
        union_id: GraphBase.NodeIdType = self.add_node(type=TermNodeType.UNION)
        self.add_edge(relation_name, union_id)

        return union_id

    def get_relation_union_node(self, relation_name: str) -> GraphBase.NodeIdType:
        """
        @param relation_name: name of a relation.
        @return: the union node of the given relation.
        """

        union_id, = self.get_children(relation_name)  # relation has only one child (the union node).
        return union_id

    @no_type_check
    def add_rule_to_term_graph(self, rule: Rule) -> None:
        """
        Generates the execution tree of the rule and adds it to the term graph.
        Implements the following pseudo code:

        def generate_computation_graph(self, head, body):
            bounding_graph = find_bounding_graph(body)
            build_root
            connect_all_bodies_to_root_with_join
            for each ie_function:
            make calc_node
            connect to join of all bounding bodies

        @param rule: the rule to add.
        """

        # maps each relation to it's node id in the term graph.
        relation_to_branch_id: Dict[Union[Relation, IERelation], int] = {}

        # stores the nodes that were added to to execution graph
        nodes = set()

        def add_node(node_id) -> None:
            """
            Saves all the nodes that were added due to the rule.

            @param node_id: a new node that was added.
            """
            nodes.add(node_id)

        def add_join_branch(head_id, joined_relations: Set[Union[Relation, IERelation]],
                            future_ie_relations: Optional[Set[IERelation]] = None):
            """
            Connects all the relations to a join node. Connects the join_node to head_id.

            @param head_id: the node to which join node will be connected.
            @param joined_relations: a set of relations.
            @param future_ie_relations: a set of ie relations that will be added to branch in the future.
            @return: the id of the join node.
            """

            future_ies = set() if future_ie_relations is None else future_ie_relations
            total_relations = joined_relations | future_ies

            # check if there is one relation (we don't need join)
            if len(total_relations) == 1 and len(joined_relations) == 1:
                add_relation_branch(next(iter(total_relations)), head_id)
                return head_id

            join_dict = get_free_var_to_relations_dict(total_relations)
            if not join_dict:
                return head_id

            # add join node
            join_node_id_ = self.add_node(type=TermNodeType.JOIN, value=join_dict)
            add_node(join_node_id_)

            self.add_edge(head_id, join_node_id_)
            for relation in joined_relations:
                add_relation_branch(relation, join_node_id_)

            return join_node_id_

        def add_relation_to(relation: Union[Relation, IERelation], father_node_id: int) -> None:
            """
            Adds relation to father id.

            @param relation: a relation.
            @param father_node_id: the node to which the relation will be connected.
            """

            get_rel_id = self.add_node(type=TermNodeType.GET_REL, value=relation)
            add_node(get_rel_id)

            # cache the branch
            relation_to_branch_id[relation] = get_rel_id
            self.add_edge(father_node_id, get_rel_id)

            # if relation is a rule relation we connect it to the root of the relation (rel_id)
            if self.is_contains_node(relation.relation_name):
                self.add_edge(get_rel_id, relation.relation_name)

        @no_type_check
        def add_relation_branch(relation: Union[Relation, IERelation], join_node_id_: int) -> None:
            """
            Adds relation to the join node.
            Finds all the columns of the relation that needed to be filtered and Adds select branch if needed.

            @param relation: a relation.
            @param join_node_id_: the join node to which the relation will be connected.
            """

            # check if the branch already exists (if relations is ie relation the branch already exists)
            if relation in relation_to_branch_id:
                self.add_edge(join_node_id_, relation_to_branch_id[relation])
                return

            free_vars = get_output_free_var_names(relation)
            term_list = relation.get_term_list()

            # check if there is a constant (A("4")), or there is a free var that appears multiple times (A(X, X))
            if len(free_vars) != len(term_list) or len(term_list) != len(set(term_list)):
                # create select node and connect relation branch to it
                select_info = relation.get_select_cols_values_and_types()
                select_node_id = self.add_node(type=TermNodeType.SELECT, value=select_info)
                add_node(select_node_id)
                self.add_edge(join_node_id_, select_node_id)
                add_relation_to(relation, select_node_id)
                relation_to_branch_id[relation] = select_node_id
            else:
                # no need to add select node
                add_relation_to(relation, join_node_id_)

        def add_calc_branch(join_node_id_: int, ie_relation_: IERelation, bounding_graph_: OrderedDict) -> int:
            """
            Adds a calc branch of the ie relation.

            @param join_node_id_: the join node to which the branch will be connected.
            @param ie_relation_: an ie relation.
            @param bounding_graph_: the bounding graph of the ie relations.
            @return: the calc_node's id.
            """
            calc_node_id_ = self.add_node(type=TermNodeType.CALC, value=ie_relation_)
            add_node(calc_node_id_)

            # join all the ie relation's bounding relations. The bounding relations already exists in the graph!
            # (since we iterate on the ie relations in the same order they were bounded).
            bounding_relations = bounding_graph_[ie_relation_]
            add_join_branch(calc_node_id_, bounding_relations)
            self.add_edge(join_node_id_, calc_node_id_)
            return calc_node_id_

        head_relation = rule.head_relation
        relations, ie_relations = rule.get_relations_by_type()
        # computes the bounding graph (it's actually an ordered dict).
        bounding_graph = TermGraph._compute_bounding_graph(relations, ie_relations)

        # make root
        union_id = self.add_relation(head_relation)
        project_id = self.add_node(type=TermNodeType.PROJECT, value=head_relation.term_list)
        self.add_edge(union_id, project_id)
        add_node(project_id)

        # connect all regular relations to join node
        join_node_id = add_join_branch(project_id, relations, ie_relations)

        # iterate over ie relations in the same order they were bounded
        for ie_relation in bounding_graph:
            calc_node_id = add_calc_branch(join_node_id, ie_relation, bounding_graph)
            relation_to_branch_id[ie_relation] = calc_node_id

        self.add_rule_node(rule, nodes)
        self._dependency_graph.add_dependencies(head_relation, relations)

    def remove_rule(self, rule: str) -> bool:
        """
        Removes a rule from term graph.

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
        is_rule_used = self._dependency_graph.is_relation_in_use(rule_name)

        # check if something is connected to the rel_root and the root is going to be deleted (this shouldn't happen)
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
