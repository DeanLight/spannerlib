"""
This file contains implementation of passes that optimize the term graph structure.
Note that this passes depend on the structure of the term graph!
"""
from typing import Dict, Any, Set, Union, List, Tuple

from rgxlog.engine.datatypes.ast_node_types import IERelation, Relation, Rule
from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.passes.lark_passes import GenericPass
from rgxlog.engine.state.graphs import TermGraphBase, GraphBase, TermNodeType, TYPE, VALUE
from rgxlog.engine.utils.general_utils import get_output_free_var_names, get_input_free_var_names, fixed_point
from rgxlog.engine.utils.passes_utils import get_new_rule_nodes


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

    def __init__(self, **kwargs: Any) -> None:
        self.term_graph: TermGraphBase = kwargs["term_graph"]

    def run_pass(self, **kwargs: Any) -> None:
        self.prune_project_nodes()

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
                    # the node has exactly one child so we connect the child to project's node parent (it's a union node)

                    project_child = next(iter(self.term_graph.get_children(project_id)))
                    self.term_graph.add_edge(union_id, project_child)
                    self.term_graph.remove_node(project_id)

    def find_arity_of_node(self, node_id: Union[int, str]) -> int:
        """
        @param node_id: id of the node.
        @note: we expect id of project/join node.
        @return: the arity of the relation that the node gets during the execution.
        """

        # this methods suppose to work for both project nodes and join nodes.
        # project nodes always have one child while join nodes always have more than one child.
        # for that reason, we traverse all the children of the node.
        node_ids = self.term_graph.get_children(node_id)
        free_vars: Set[str] = set()

        def is_relation_has_one_free_var(relation_: Union[Relation, IERelation]) -> bool:
            """
            Check whether relation is only one free variable.
            @param relation_: a relation or an ie_relation.
            """

            return len(relation_.get_term_list()) == 1

        for node_id in node_ids:
            node_attrs = self.term_graph[node_id]
            node_type = node_attrs[TYPE]

            if node_type in (TermNodeType.GET_REL, TermNodeType.RULE_REL, TermNodeType.GET_REL.CALC):
                relation = node_attrs[VALUE]
                # if relation has more than one free var we can't prune the project
                if not is_relation_has_one_free_var(relation):
                    return 0

                free_vars |= set(relation.get_term_list())

            elif node_type is TermNodeType.JOIN:
                # the input of project node is the same as the input of the join node
                return self.find_arity_of_node(node_id)

            elif node_type is TermNodeType.SELECT:
                relation_child_id = next(iter(self.term_graph.get_children(node_id)))
                relation = self.term_graph[relation_child_id][VALUE]
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
            node_type = node_attrs[TYPE]

            if node_type is TermNodeType.UNION:
                children = self.term_graph.get_children(node_id)
                project_children = [node for node in children if self.term_graph[node][TYPE] is TermNodeType.PROJECT]
                union_to_project_children[node_id] = project_children

        return union_to_project_children


class RemoveUselessRelationsFromRule(GenericPass):
    """
    This pass removes duplicated relations from a rule.
    For example, the rule A(X) <- B(X), C(Y) contains a redundant relation (C(Y)).
    After this pass the rule will be A(X) <- B(X).

    @note: in the rule A(X) <- B(X, Y), C(Y); C(Y) is not redundant!
    """

    def __init__(self, **kwargs: Any):
        self.parse_graph: GraphBase = kwargs["parse_graph"]

    @staticmethod
    def remove_useless_relations(rule: Rule) -> None:
        """
        Finds redundant relations and removes them from the rule.
        @param rule: a rule.
        """
        relevant_free_vars = set(rule.head_relation.get_term_list())

        # relation without free vars are always relevant
        initial_useless_relations_and_types = [(rel, rel_type) for rel, rel_type in zip(rule.body_relation_list, rule.body_relation_type_list)
                                               if len(get_output_free_var_names(rel)) != 0]

        def step_function(current_useless_relations_and_types: List[Tuple[Union[Relation, IERelation], str]]) -> List[Tuple[Union[Relation, IERelation], str]]:
            """
            Used by fixed pont algorithm.

            @param current_useless_relations_and_types: current useless relations and their types
            @return: useless relations after considering the new relevant free vars.
            """

            next_useless_relations_and_types = []
            for relation, rel_type in current_useless_relations_and_types:
                term_list = get_output_free_var_names(relation)
                if len(relevant_free_vars.intersection(term_list)) == 0:
                    next_useless_relations_and_types.append((relation, rel_type))
                else:
                    relevant_free_vars.update(term_list)
                    relevant_free_vars.update(get_input_free_var_names(relation))

            return next_useless_relations_and_types

        useless_relations_and_types = fixed_point(start=initial_useless_relations_and_types, step=step_function, distance=lambda x, y: int(len(x) != len(y)))

        relevant_relations_and_types = set(zip(rule.body_relation_list, rule.body_relation_type_list)).difference(useless_relations_and_types)
        new_body_relation_list, new_body_relation_type_list = zip(*relevant_relations_and_types)
        rule.body_relation_list = list(new_body_relation_list)
        rule.body_relation_type_list = list(new_body_relation_type_list)

    def run_pass(self, **kwargs: Any) -> None:
        rules = get_new_rule_nodes(self.parse_graph)
        for rule_node_id in rules:
            rule: Rule = self.parse_graph[rule_node_id][VALUE]
            RemoveUselessRelationsFromRule.remove_useless_relations(rule)
