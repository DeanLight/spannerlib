"""
This file contains implementation of passes that optimize the term graph structure.
Note that this passes depend on the structure of the term graph!
"""
from typing import Dict, Any, Set, Union, List

from rgxlog.engine.datatypes.ast_node_types import IERelation, Relation
from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.passes.lark_passes import GenericPass
from rgxlog.engine.state.graphs import TermGraphBase


class PruneUnnecessaryProjectNodes(GenericPass):
    """
    This class prunes project nodes that gets a relation with one column (therefore, the project is redundant).

    For example, the rule A(X) <- B(X) will yield the following term graph:

        rule_rel node (of A)
            union node
                project node (on X)
                   get_rel node (get B)

        since we project a relation with one column, after this pass the term graph will be:

        rule_rel node (of A)
            union node
                get_rel node (get B)

    """

    def __init__(self, **kwargs):
        self.term_graph: TermGraphBase = kwargs["term_graph"]

    def run_pass(self, **kwargs):
        class_name = self.__class__.__name__
        print(f"Term graph before {class_name}:\n{self.term_graph}")
        self.prune_project_nodes()
        print(f"Term graph after {class_name}:\n{self.term_graph}")

    def prune_project_nodes(self) -> None:
        """
        Prunes the redundant project nodes.
        """

        union_to_project_children = self.get_all_union_and_project_nodes()
        for union_id, project_ids in union_to_project_children.items():
            for project_id in project_ids:
                arity = self.find_arity_of_node(project_id)

                if arity == 1:
                    # in this case the input relations of the project node has arity of one so we prune to node
                    # the node has exactly one child so we connect the child to project's node father (it's a union node)

                    project_child = next(iter(self.term_graph.get_children(project_id)))
                    self.term_graph.add_edge(union_id, project_child)
                    self.term_graph.remove_node(project_id)

    def find_arity_of_node(self, node_id) -> int:
        """
        @param node_id: id of the node.
        @note: we expect id of project/join node.
        @return: the arity of the relation that the node gets during the execution.
        """

        node_ids = list(self.term_graph.get_children(node_id))
        free_vars: Set[str] = set()

        def is_relation_has_one_free_var(relation_: Union[Relation, IERelation]) -> bool:
            """
            Check whether relation is only one free variable.

            @param relation_: a relation or an ie_relaiton.
            """

            return len(relation_.get_term_list()) == 1

        while len(node_ids) != 0:
            node_id = node_ids.pop(0)
            node_attrs = self.term_graph[node_id]
            node_type = node_attrs["type"]

            if node_type in ("get_rel", "rule_rel", "calc"):
                relation = node_attrs["value"]
                # if relation has more than one free var we can' prune to project
                if not is_relation_has_one_free_var(relation):
                    return 0

                free_vars |= set(relation.get_term_list())

            elif node_type == "join":
                # the input of project node is the same as the input of the join node
                return self.find_arity_of_node(node_id)

            elif node_type == "select":
                relation_child_id = next(iter(self.term_graph.get_children(node_id)))
                relation = self.term_graph[relation_child_id]["value"]
                if not is_relation_has_one_free_var(relation):
                    return 0

                relation_free_vars = [var for var, var_type in zip(relation.get_term_list(), relation.get_type_list()) if var_type is DataTypes.free_var_name]
                free_vars |= set(relation_free_vars)

        return len(free_vars)

    def get_all_union_and_project_nodes(self) -> Dict[Any, List]:
        """
        Finds all the union node and their project children nodes in the term graph.

        @return: a mapping between union nodes ids to their project children nodes id.
        """

        union_to_project_children = {}
        nodes_ids = self.term_graph.post_order_dfs()

        for node_id in nodes_ids:
            node_attrs = self.term_graph[node_id]
            node_type = node_attrs["type"]

            if node_type == "union":
                children = self.term_graph.get_children(node_id)
                project_children = [node for node in children if self.term_graph[node]["type"] == "project"]
                union_to_project_children[node_id] = project_children

        return union_to_project_children
