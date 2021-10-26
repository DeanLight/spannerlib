"""
this module contains the implementation of the naive execution function
"""

from typing import (Tuple, Dict, List, Callable, Optional, Union)

from rgxlog.engine.datatypes.ast_node_types import (Relation, Query,
                                                    IERelation)
from rgxlog.engine.engine import RgxlogEngineBase
from rgxlog.engine.state.graphs import EvalState, GraphBase, TermGraphBase, ROOT_TYPE, TermNodeType, TYPE, STATE, VALUE
from rgxlog.engine.state.symbol_table import SymbolTableBase
from rgxlog.engine.utils.passes_utils import ParseNodeType

OUT_REL_ATTRIBUTE = "output_rel"

FREE_VAR_PREFIX = "COL"


def naive_execution(parse_graph: GraphBase, term_graph: TermGraphBase,
                    symbol_table: SymbolTableBase, rgxlog_engine: RgxlogEngineBase) -> Optional[Tuple[Query, List]]:
    """
    Executes a parse graph
    this execution is generic, meaning it does not require any specific kind of term graph, symbol table or
    rgxlog engine in order to work.
    this execution performs no special optimization and merely serves as an interface between the term graph
    and the rgxlog engine.

    the main idea behind this class is that it uses the `term_graph` to understand how relations are related to
    one another, and thanks to that information, it is able to execute the commands in the `parse_graph`.
    for example, let's say the parse graph looks like this:

    ```
    (root) -> (query relation a)
    ```

    and the term graph looks like this:

    (a)  --> union --> (b)
                   --> (c)

    the execution class will perform a union over `b` and `c`, and put it in a new relation, let's say `union_b_c`.
    then it will copy `union_b_c` into `a`, and finally it will query `a` and return the result.

    more precisely, the execution traverses the parse tree, when it reaches a query node it compute the relevant
    relation using the term graph (i.e. if the query is ?A(X) it will compute the relation A).
    read the docstring of compute_rule function to understand how the computation is done.

    @param parse_graph: a term graph to execute.
    @param term_graph: a term graph.
    @param symbol_table: a symbol table.
    @param rgxlog_engine: a rgxlog engine that will be used to execute the term graph.
    """

    # it's an inner function because it needs to access all naive_execution's params
    def compute_rule(relation_name: str, do_reset: bool = True) -> None:
        """
        Computes the rule (including the mutual recursive rules).
        This function traverses the term graph and dynamically generates the computation graph of the rule (note that we
        don't really create a computational graph object; it's more of a conceptual thing).
        During the traversal, when we reach a root of another rule relation, we build its computational graph as well.
        We do that in the following way:
            * if the relation is mutually recursive, we use its current value.
            * if the relation isn't mutually recursive, we compute it recursively (calling compute_rule on it).

        Finally, we compute together all the mutually recursive relations in the following way:
            we iterate over all the mutually recursive relations:
                each relation is computed using the current states of its mutually recursive relations
            we stop iterating only after there was no change in all the mutually recursive relations at the same
            iteration (we reach a fixed point).

        the following abstract example might help understand this process:
        let's say we have 2 mutually recursive relations, `a` and `b`, which depend on one another:
        ...
        a(X) <- b(X)
        ...
        b(X) <- a(X)
        ...

        at the beginning, the imaginary relations a_0 and b_0 are empty.
        during the first iteration, the imaginary relation a_1 is created, and it may contain some rows of data (based on the rules).
        then b_1 is created, and it is affected by a_1 (because of the rule `b(X) <- a(X)`), so it will have all of a_1's rows, maybe more.
        after `i` iterations, a_i and b_i are not changed, and therefore we reached a fixed point. now we stop iteration,
        and relations `a` and `b` are `COMPUTED`.

        @param relation_name: the name of the relation to compute.
        @param do_reset: if set to True, we reset the nodes after the computation.
        """

        # check if the relation is base relation
        if not term_graph.is_contains_node(relation_name):
            return

        # stores all the nodes that were visited during the dfs
        visited_nodes = set()
        mutually_recursive = term_graph.get_mutually_recursive_relations(relation_name)
        current_computed_relation = None

        def compute_postorder(node_id: GraphBase.NodeIdType) -> None:
            """
            Runs postorder dfs over the term graph and evaluates the tree.

            @param node_id: the current node.
            """
            term_attrs = term_graph[node_id]
            if node_id in visited_nodes or term_attrs[STATE] is EvalState.COMPUTED:
                return

            # if type is not rule_rel it's fine to continue the dfs
            if term_attrs[TYPE] is TermNodeType.RULE_REL:
                rule_rel = term_attrs[VALUE]
                if rule_rel.relation_name not in mutually_recursive:
                    # computes the independent rule and stop
                    compute_rule(rule_rel.relation_name, do_reset=False)
                    return

                # we here if the rule_rel is mutually recursive with the relation we are computing
                # if rule rel is the rule we're currently computing - continue the dfs
                if rule_rel.relation_name != current_computed_relation:
                    # in case of dependent rule we use the current state of that rule
                    term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, rule_rel)
                    return

            visited_nodes.add(node_id)
            children = term_graph.get_children(node_id)
            for child in children:
                compute_postorder(child)

            compute_node(node_id)
            return

        # clear all the mutually recursive tables.
        rgxlog_engine.clear_tables(mutually_recursive)

        fixed_point = False
        while not fixed_point:
            # computes one iteration for all of the mutually recursive rules
            fixed_point = True
            for relation in mutually_recursive:
                current_computed_relation = relation
                visited_nodes = set()
                initial_len = rgxlog_engine.get_table_len(current_computed_relation)
                compute_postorder(current_computed_relation)
                is_stopped = rgxlog_engine.get_table_len(current_computed_relation) == initial_len

                # we stop iterating when all the rules converged at the same step
                fixed_point = fixed_point and is_stopped

        state = EvalState.NOT_COMPUTED if do_reset else EvalState.COMPUTED
        for term_id in term_graph.post_order_dfs_from(relation_name):
            term_graph.set_node_attribute(term_id, STATE, state)

        return

    def compute_node(node_id: GraphBase.NodeIdType) -> None:
        """
        Computes the current node based on its type.

        @param node_id: the current node.
        """

        def is_node_computed() -> bool:
            """
            Finds out whether the node is computed.

            @return: True if all the children of the node are computed or it has no children, False otherwise.
            """

            children = term_graph.get_children(node_id)
            if not children:
                return True

            children_statuses_is_computed = [term_graph[child_id][STATE] is EvalState.COMPUTED
                                             for child_id in children]
            return all(children_statuses_is_computed)

        def get_children_relations() -> List[Relation]:
            """
            Gets the node's children output relations.

            @return: a list containing the children output relations.
            """
            relations_ids = term_graph.get_children(node_id)
            relations_nodes = [term_graph[rel_id] for rel_id in relations_ids]
            relations = [rel_node[OUT_REL_ATTRIBUTE] for rel_node in relations_nodes]
            return relations

        term_type_to_engine_op: Dict[TermNodeType, Callable] = {
            TermNodeType.RULE_REL: rgxlog_engine.operator_copy,
            TermNodeType.UNION: rgxlog_engine.operator_union,
            TermNodeType.JOIN: rgxlog_engine.operator_join,
            TermNodeType.PROJECT: rgxlog_engine.operator_project,
            TermNodeType.SELECT: rgxlog_engine.operator_select
        }

        term_attrs = term_graph[node_id]
        if term_attrs[STATE] is EvalState.COMPUTED:
            return

        term_type = term_attrs[TYPE]

        if term_type is TermNodeType.GET_REL:
            output_relation = term_attrs[VALUE]

        elif term_type is TermNodeType.CALC:
            children_relations = get_children_relations()
            rel_in = children_relations[0] if children_relations else None  # tmp bounding relation of the ie rel (join over all the bounding relations)
            ie_rel_in: IERelation = term_attrs[VALUE]  # the ie relation to compute
            ie_func_data = symbol_table.get_ie_func_data(ie_rel_in.relation_name)  # the ie function that correspond to the ie relation
            output_relation = rgxlog_engine.compute_ie_relation(ie_rel_in, ie_func_data, rel_in)

        else:
            operator = term_type_to_engine_op[term_type]
            input_relations = get_children_relations()
            output_relation = operator(input_relations, term_attrs.get(VALUE))

        term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, output_relation)

        # statement was executed, mark it as "computed" or "visited"
        compute_status = EvalState.COMPUTED if is_node_computed() else EvalState.VISITED
        term_graph.set_node_attribute(node_id, STATE, compute_status)

    node_type_to_action: Dict[Union[str, ParseNodeType], Callable] = {
        ParseNodeType.RULE: lambda rule_: rgxlog_engine.declare_relation_table(rule_.head_relation.as_relation_declaration()),
        ParseNodeType.RELATION_DECLARATION: rgxlog_engine.declare_relation_table,
        ParseNodeType.ADD_FACT: rgxlog_engine.add_fact,
        ParseNodeType.REMOVE_FACT: rgxlog_engine.remove_fact,
        ROOT_TYPE: lambda *args: None  # noop
    }

    # get the parse_graph's node ids. note that the order of the ids does not actually matter as long as the statements
    # are ordered the same way as they were in the original program
    parse_node_ids = parse_graph.post_order_dfs()
    query_result = None

    # execute each non computed statement in the parse graph
    for parse_id in parse_node_ids:
        parse_node_attrs = parse_graph[parse_id]

        if parse_node_attrs[STATE] is EvalState.COMPUTED:
            continue

        # mark node as "computed"
        parse_graph.set_node_attribute(parse_id, STATE, EvalState.COMPUTED)

        # the parse node is not computed, get its type and compute it accordingly
        parse_node_type = parse_node_attrs[TYPE]

        if parse_node_type == ParseNodeType.QUERY:
            # we return the query as well as the result, because we print as part of the output
            query: Query = parse_node_attrs[VALUE]
            compute_rule(query.relation_name)
            query_result = (query, rgxlog_engine.query(query))

        else:
            action = node_type_to_action[parse_node_type]
            action(parse_node_attrs.get(VALUE))

    return query_result
