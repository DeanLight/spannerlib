"""
this modules contains implementations of an execution function
"""

from typing import (Tuple, Dict, List)

from rgxlog.engine.datatypes.ast_node_types import (DataTypes, Relation, AddFact, Query,
                                                    RelationDeclaration, IERelation)
from rgxlog.engine.engine import RgxlogEngineBase, SqliteEngine
from rgxlog.engine.state.symbol_table import SymbolTableBase
from rgxlog.engine.state.graphs import EvalState, GraphBase, TermGraph

VALUE_ATTRIBUTE = 'value'
OUT_REL_ATTRIBUTE = "output_rel"

FREE_VAR_PREFIX = "COL"


def naive_execution(parse_graph: GraphBase, term_graph: TermGraph,
                    symbol_table: SymbolTableBase, rgxlog_engine: RgxlogEngineBase) -> Tuple[Query, List]:
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
    def compute_rule(relation_name: str, to_reset: bool = True) -> None:
        """
        Computes the rule (including the mutual recursive rules).
        This function traverses the term graph and dynamically building the computation graph of th rule (note that we
        don't really build the computational graph it's more a conceptual thing).
        During the traversal when we reach a root of another rule relation we build it's computational graph as well.
        We do that in the following way:
            if the relation is mutually recursive we use it's current value.
            if the relation isn't mutually recursive we compute it recursively (calling compute_rule on it).

        Finally, we compute together all the mutually recursive relation in the following way:
            we iterate over all the mutually recursive relations:
                each relation is computed using the current states of it's mutually recursive relation
            we stop iterating only when there was no change in all the mutually recursive relation at the same
            iteration (we reach a fixed point).

        @param relation_name: the name of the relation to compute.
        @param to_reset: if set to True we reset the nodes after the computation.
        """

        # check if the relation is base relation
        if not term_graph.has_node(relation_name):
            return

        # stores all the nodes that were visited during the dfs
        visited_nodes = set()
        mutually_recursive = term_graph.get_mutually_recursive_relations(relation_name)
        current_computed_relation = None

        def compute_postorder(node_id) -> None:
            """
            Runs postorder dfs over the term graph and evaluates the tree.

            @param node_id: the current node.
            """
            term_attrs = term_graph[node_id]
            if node_id in visited_nodes or term_attrs["state"] is EvalState.COMPUTED:
                return

            # if type is not rule_rel it's fine to continue the dfs
            if term_attrs["type"] == "rule_rel":
                rule_rel = term_attrs[VALUE_ATTRIBUTE]
                if rule_rel.relation_name not in mutually_recursive:
                    # computes the independent rule and stop
                    compute_rule(rule_rel.relation_name, to_reset=False)
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

        state = EvalState.NOT_COMPUTED if to_reset else EvalState.COMPUTED
        for term_id in term_graph.post_order_dfs_from(relation_name):
            term_graph.set_node_attribute(term_id, "state", state)

    def compute_node(node_id: int) -> None:
        """
        Computes the current node based on its type.

        @param node_id: the current node.
        """

        def is_node_computed(node_id_) -> bool:
            """
            Finds out whether the node is computed.

            @param node_id_: the node for which we check the status.
            @return: True if all the children of the node are computed or it has no children, False otherwise.
            """

            children = term_graph.get_children(node_id_)
            if not children:
                return True

            children_statuses_is_computed = [term_graph[child_id]["state"] is EvalState.COMPUTED
                                             for child_id in children]
            return all(children_statuses_is_computed)

        def get_children_relations(node_id_) -> List[Relation]:
            """
            Gets the node's children output relations.

            @param node_id_: a node.
            @return: a list containing the children output relations.
            """
            relations_ids = term_graph.get_children(node_id_)
            relations_nodes = [term_graph[rel_id] for rel_id in relations_ids]
            relations = [rel_node[OUT_REL_ATTRIBUTE] for rel_node in relations_nodes]
            return relations

        def get_child_relation(node_id_) -> Relation:
            """
            Gets the node's child output relation.
            @note: this method is called when we know that the node has at most one child.

            @param node_id_: a node.
            @return: the output relation of the node's child.
            """
            children = get_children_relations(node_id_)
            assert len(children) <= 1, "this node should have exactly one child"
            return children[0]

        # maps between the term type to:
        #   1. the sql operator to call
        #   2. a flag that is True if the node type has only one child.
        #   3. a flag that is True if the 'value' attribute of the node should be passed to the operator
        term_type_to_meta_data = {
            "rule_rel": (rgxlog_engine.operator_copy, True, True),
            "union": (rgxlog_engine.operator_union, False, False),
            "join": (rgxlog_engine.operator_join, False, False),
            "project": (rgxlog_engine.operator_project, True, True),
            "select": (rgxlog_engine.operator_select, True, True)
        }

        term_attrs = term_graph[node_id]
        if term_attrs["state"] is EvalState.COMPUTED:
            return

        term_type = term_attrs["type"]

        if term_type == "get_rel":
            output_relation = term_attrs[VALUE_ATTRIBUTE]

        elif term_type == "calc":
            children = get_children_relations(node_id)
            rel_in = children[0] if children else None
            # note: we use the same `VALUE_ATTRIBUTE` keyword for different things to be able to print it easily
            # when printing the tree
            ie_rel_in: IERelation = term_attrs[VALUE_ATTRIBUTE]
            ie_func_data = symbol_table.get_ie_func_data(ie_rel_in.relation_name)
            output_relation = rgxlog_engine.compute_ie_relation(ie_rel_in, ie_func_data, rel_in)

        else:
            operator, has_one_child, pass_value_attr = term_type_to_meta_data[term_type]
            input_relation = get_child_relation(node_id) if has_one_child else get_children_relations(node_id)
            operator_args = [input_relation]
            if pass_value_attr:
                operator_args.append(term_attrs[VALUE_ATTRIBUTE])

            output_relation = operator(*operator_args)

        term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, output_relation)

        # statement was executed, mark it as "computed" or "visited"
        compute_status = EvalState.COMPUTED if is_node_computed(node_id) else EvalState.VISITED
        term_graph.set_node_attribute(node_id, 'state', compute_status)

    exec_result = None
    node_type_to_action = {
        "rule": lambda rule_: rgxlog_engine.declare_relation(rule_.head_relation.as_relation_declaration()),
        "relation_declaration": rgxlog_engine.declare_relation,
        "add_fact": rgxlog_engine.add_fact,
        "remove_fact": rgxlog_engine.remove_fact,
    }

    # get the parse_graph's node ids. note that the order of the ids does not actually matter as long as the statements
    # are ordered the same way as they were in the original program
    parse_node_ids = parse_graph.post_order_dfs()

    # execute each non computed statement in the parse graph
    for parse_id in parse_node_ids:
        parse_node_attrs = parse_graph[parse_id]

        if parse_node_attrs["state"] is EvalState.COMPUTED:
            continue

        # mark node as "computed"
        parse_graph.set_node_attribute(parse_id, "state", EvalState.COMPUTED)

        # the parse node is not computed, get its type and compute it accordingly
        parse_node_type = parse_node_attrs["type"]

        if parse_node_type in ("root", "relation"):
            continue

        elif parse_node_type == "query":
            # we return the query as well as the result, because we print as part of the output
            query = parse_node_attrs[VALUE_ATTRIBUTE]
            compute_rule(query.relation_name)
            exec_result = (query, rgxlog_engine.query(query))

        else:
            action = node_type_to_action[parse_node_type]
            action(parse_node_attrs[VALUE_ATTRIBUTE])

    return exec_result


if __name__ == "__main__":
    my_engine = SqliteEngine()
    print("hello world")

    # add relation
    my_relation = RelationDeclaration("yoyo", [DataTypes.integer, DataTypes.string])
    my_engine.declare_relation(my_relation)

    # add fact
    my_fact = AddFact("yoyo", [8, "hihi"], [DataTypes.integer, DataTypes.string])
    my_engine.add_fact(my_fact)

    my_query = Query("yoyo", ["X", "Y"], [DataTypes.free_var_name, DataTypes.free_var_name])
    print(my_engine.query(my_query))

    print(my_engine.get_table_len("yoyo"))
