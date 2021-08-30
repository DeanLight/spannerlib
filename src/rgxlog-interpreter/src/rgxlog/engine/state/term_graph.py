"""
this module contains the implementations of term graphs
"""

from enum import Enum

import networkx as nx
from abc import abstractmethod
from itertools import count
from typing import Set, List, Dict, Iterable

from rgxlog.engine.datatypes.ast_node_types import Relation, Rule

PRETTY_INDENT = ' ' * 4


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

    @abstractmethod
    def add_node(self, **attr) -> None:
        """
        Adds a term to the term graph.

        @param attr: the attributes of the term.
        @return: a term id that refers to the term that was added.
        """
        pass

    @abstractmethod
    def get_root_id(self) -> int:
        """
        @return: the term id of the root of the term graph.
        """
        pass

    @abstractmethod
    def remove_node(self, term_id: int) -> None:
        """
        Removes a term from the term graph.

        @param term_id: the id of the term that will be removed.
        """
        pass

    @abstractmethod
    def add_edge(self, father_id: int, son_id: int, **attr) -> None:
        """
        Adds the edge (father_id, son_id) to the term graph.
        the edge signifies that the father term is dependent on the son term.

        @param father_id: the id of the father term.
        @param son_id: the id of the son term.
        @param attr: the attributes for the edge.
        """
        pass

    @abstractmethod
    def pre_order_dfs_from(self, node_id: int) -> Iterable[int]:
        """
        @return: an iterable of the term ids generated from a depth-first-search pre-ordering starting at the root
        of the term graph.
        """
        pass

    def pre_order_dfs(self) -> Iterable[int]:
        """
        @return: an iterable of the term ids generated from a depth-first-search pre-ordering starting at the root
        of the term graph.
        """
        return self.pre_order_dfs_from(self.get_root_id())

    @abstractmethod
    def post_order_dfs_from(self, node_id: int) -> Iterable[int]:
        """
        @return: an iterable of the term ids generated from a depth-first-search post-ordering starting at the root
        of the term graph.
        """
        pass

    def post_order_dfs(self) -> Iterable[int]:
        """
        @return: an iterable of the term ids generated from a depth-first-search post-ordering starting at the root
        of the term graph.
        """
        return self.post_order_dfs_from(self.get_root_id())

    @abstractmethod
    def get_children(self, term_id) -> Iterable[int]:
        """
        In a term graph the children of a term are its dependencies
        this function returns the children of a term.

        @param term_id: a term id.
        @return: an iterable of the children of the term.
        """
        pass

    @abstractmethod
    def set_node_attribute(self, term_id: int, attr_name: str, attr_value) -> None:
        """
        Sets an attribute of a term.

        @param term_id: the id of the term.
        @param attr_name: the name of the attribute.
        @param attr_value: the value that will be set for the attribute.
        """
        pass

    @abstractmethod
    def get_node_attributes(self, term_id: int) -> Dict:
        """
        @param term_id: a term id.
        @return: a dict containing the attributes of the term.
        """
        pass

    def __getitem__(self, term_id: int):
        return self.get_node_attributes(term_id)

    def __str__(self):
        pass


class NetxGraph(GraphBase):
    """
    implementation of a term graph using a networkx graph
    the official documentation for networkx can be found here: https://networkx.org/documentation/stable/index.html
    a basic tutorial for networkx https://networkx.org/documentation/stable//reference/introduction.html
    """

    def __init__(self):

        # define the graph with 'DiGraph' to make sure the order of a reported node's children is the same
        # as the order they were added to the graph.
        self._graph = nx.DiGraph()

        # when a new node is added to the graph, it needs to have an id that was not used before
        # this field will serve as a counter that will provide a new term id
        self._term_id_counter = count()

        # create the root of the term graph. it will be used as a source for dfs/bfs
        self._root_id = self.add_node(type="root")

    def add_node(self, **attr) -> int:
        # assert the term has a type
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

    def get_root_id(self) -> int:
        return self._root_id

    def remove_node(self, term_id: int) -> None:
        self._graph.remove_node(term_id)

    def add_edge(self, father_id: int, son_id: int, **attr) -> None:

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

    def pre_order_dfs_from(self, node_id: int) -> List[int]:
        return nx.dfs_preorder_nodes(self._graph, node_id)

    def post_order_dfs_from(self, node_id: int) -> List[int]:
        return nx.dfs_postorder_nodes(self._graph, node_id)

    def get_children(self, term_id: int) -> List[int]:
        return list(self._graph.successors(term_id))

    def set_node_attribute(self, term_id: int, attr_name: str, attr_value) -> None:
        self._graph.nodes[term_id][attr_name] = attr_value

    def get_node_attributes(self, term_id: int) -> Dict:
        return self._graph.nodes[term_id].copy()

    def _get_term_string(self, term_id: int) -> str:
        """
        A utility function for pretty().

        @param term_id: a term id
        @return: a string representation of the term
        """

        term_attrs = self.get_node_attributes(term_id)

        # get a string of the term's value (if it exists)
        if 'value' in term_attrs:
            term_value_string = f": {term_attrs['value']}"
        else:
            term_value_string = ''

        # create a string representation of the term and return it
        term_string = f"({term_id}) ({term_attrs['state']}) {term_attrs['type']}{term_value_string}"
        return term_string

    def _pretty_aux(self, term_id: int, level: int) -> List[str]:
        """
        A helper function for pretty().

        @param term_id: an id of a term in the term graph.
        @param level: the depth of the term in the tree (used for indentation).
        @return: a list of strings that represents the term and its children.
        """

        # get a representation of the term
        ret = [PRETTY_INDENT * level, self._get_term_string(term_id), '\n']

        if term_id in self._visited_nodes:
            return ret

        self._visited_nodes.add(term_id)

        # get a representation of the term's children
        for child_id in self.get_children(term_id):
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
        return ''.join(self._pretty_aux(self._root_id, 0))

    def __str__(self):
        return self.pretty()


class DependencyGraph(NetxGraph):
    """
    a class that represents the dependencies between rules.
    """

    def __init__(self):
        super().__init__()
        self.relation_to_id = dict()
        self.id_to_relation = dict()

    def _add_relation(self, relation: Relation) -> int:
        """
        Adds relation to dependency graph.

        @param relation: the relation to add (should be rule relation).
        @return: the id of the relation node.
        """
        relation_name = relation.relation_name
        if relation_name in self.relation_to_id:
            return self.relation_to_id[relation_name]

        rel_id = self.add_node(type="rel", value=relation_name)
        self.add_edge(self._root_id, rel_id)
        self.relation_to_id[relation_name] = rel_id
        self.id_to_relation[rel_id] = relation_name
        return rel_id

    def is_dependent(self, head_rel: Relation, body_rel: Relation) -> bool:
        """
        Finds out whether the head relation is dependent in body relation.

        @param head_rel: the head relation.
        @param body_rel: a body relation.
        @return: True if they are dependent, False otherwise.
        """

        common_free_vars = set(head_rel.term_list).intersection(body_rel.term_list)
        return body_rel.relation_name in self.relation_to_id and len(common_free_vars) > 0

    def add_dependencies(self, head_relation: Relation, body_relations: Set[Relation]) -> None:
        """
        Adds all the dependencies of the rule to the graph.

        @param head_relation: the head relation of the rule.
        @param body_relations: a set of rule's body relations.
        """

        head_id = self._add_relation(head_relation)

        for relation in body_relations:
            # add edge only if there is at least one free var in relation
            relation_name = relation.relation_name
            if self.is_dependent(head_relation, relation):
                rel_id = self.relation_to_id[relation_name]
                edge = (head_id, rel_id)
                num_of_edges = 1 + self._graph.get_edge_data(*edge, default={"amount": 0})["amount"]
                self.add_edge(*edge, amount=num_of_edges)

    def remove_relation(self, relation_name: str) -> None:
        """
        Removes the relation node from the dependency graph.

        @param relation_name: the name of the relation to remove.
        """

        self._graph.remove_node(self.relation_to_id[relation_name])

    def remove_rule(self, rule: Rule) -> None:
        """
        Removes the dependencies of the rule from the graph.

        @param rule: the rule to remove.
        """

        head_relation = rule.head_relation
        head_id = self.relation_to_id[head_relation.relation_name]

        body_relations, _ = rule.get_relations_by_type()
        for relation in body_relations:
            if self.is_dependent(head_relation, relation):
                rel_id = self.relation_to_id[relation.relation_name]
                edge = (head_id, rel_id)
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
        rel_id = self.relation_to_id[relation_name]
        scc = nx.strongly_connected_components(self._graph)

        for component in scc:
            if rel_id in component:
                names_component = set(map(lambda x: self.id_to_relation[x], component))
                return names_component

    def __str__(self):
        return self.__class__.__name__ + " is:\n" + super().__str__()

class ComputationTermGraph(NetxGraph):
    """
    a wrapper to NextTermGraph that adds support to relations and their corresponding nodes.
    """

    def __init__(self):
        super().__init__()
        self._relation_to_id = dict()
        self._rule_to_nodes = dict()
        self._dependency_graph = DependencyGraph()

    def add_rule(self, rule: Rule, nodes: Set[int]) -> None:
        """
        Adds rule to term graph dict.

        @param rule: the rule to add.
        @param nodes: all the nodes in the graph that are unique to the rule
                      (and thus should be removed if the rule is removed).
        """

        self._rule_to_nodes[str(rule)] = (rule, nodes)

    def _is_node_in_use(self, node_id: int) -> bool:
        """
        Checks if id node has parents or it's the root node.

        @param node_id: id of a node.
        @return: true if the node is has parents (if node is root the we also return true).
        """
        if node_id == self.get_root_id():
            return True

        # all the nodes are connected to global root
        return len(list(self._graph.predecessors(node_id))) > 1

    def _get_all_rules_with_head(self, relation_name: str) -> List[str]:
        """
        Find all the rule with rule head.

        @raise Exception: if relation name doesn't exist in the graph.
        @param relation_name: name of the relation.
        @return: a list of rules with rule head.
        """

        rules = [rule for rule in self._rule_to_nodes if rule.startswith(relation_name)]

        if len(rules) == 0:
            # if we are here than we didn't find the given relation
            raise Exception(f"There are no relation with head '{relation_name}' in the term graph.")

        return rules

    def remove_rules_with_head(self, rule_head: str) -> None:
        """
        Removes all rules with given rule head from the term graph.

        @param rule_head: a relation name
        """

        rules = self._get_all_rules_with_head(rule_head)
        rel_node, union_node = self._relation_to_id[rule_head]
        if self._is_node_in_use(rel_node):
            raise Exception(f"The rule head'{rule_head}' can't be deleted since it's used in another existing rule.")

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
            raise Exception(f"The rule '{rule}' was never registered "
                            f"(you can run 'print_all_rules' to see all the registered rules)")

        actual_rule, nodes = self._rule_to_nodes[rule]
        rule_name = actual_rule.head_relation.relation_name
        rel_node, union_node = self._relation_to_id[rule_name]

        is_last_rule_path = len(self.get_children(union_node)) == 1
        is_rule_used = self._is_node_in_use(rel_node)

        # check if something is connected to the root and the root is going to be deleted (this shouldn't happen)
        if is_last_rule_path and is_rule_used:
            raise Exception(f"The rule '{rule}' can't be deleted since '{rule_name}' is used in another existing rule.")

        self._graph.remove_nodes_from(nodes)
        del self._rule_to_nodes[rule]

        self._dependency_graph.remove_rule(actual_rule)

        if is_last_rule_path:
            self._graph.remove_nodes_from((rel_node, union_node))
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
        if relation_name in self._relation_to_id:
            return self.get_relation_id(relation_name, False)

        rel_id = self.add_node(type="rule_rel", value=relation)
        self.add_edge(self._root_id, rel_id)
        union_id = self.add_node(type="union")
        self.add_edge(rel_id, union_id)
        self._relation_to_id[relation_name] = (rel_id, union_id)

        return self.get_relation_id(relation_name, False)

    def get_relation_id(self, relation: str, actual_node: bool = True) -> int:
        """
        @param relation: the relation to look for.
        @param actual_node: if true we return the relation node. otherwise we return it's union child node id.
        """
        ids = self._relation_to_id.get(relation, -1)
        if ids == -1:
            return -1
        return ids[0] if actual_node else ids[1]

    def add_dependencies(self, head_relation: Relation, body_relations: Set[Relation]) -> None:
        """@see documentation of add_dependencies in DependencyGraph"""
        self._dependency_graph.add_dependencies(head_relation, body_relations)

    def get_mutually_recursive_relations(self, relation_name: str) -> Set[str]:
        """@see documentation of get_mutually_recursive_relations in DependencyGraph"""
        return self._dependency_graph.get_mutually_recursive_relations(relation_name)

    def __str__(self):
        return super().__str__() + "\n" + str(self._dependency_graph)


