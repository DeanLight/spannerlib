"""
this modules contains implementations of 'RgxlogEngineBase' which is an abstraction for the rgxlog engine
and also implementations of 'ExecutionBase' which serves as an abstraction for an interface between a term graph
and an rgxlog engine.
"""

from abc import ABC, abstractmethod
from typing import (Tuple, Dict, List)

from rgxlog.engine.datatypes.ast_node_types import (DataTypes, Relation, AddFact, Query,
                                                    RelationDeclaration, IERelation)
from rgxlog.engine.engine import RgxlogEngineBase, SqliteEngine
from rgxlog.engine.state.symbol_table import SymbolTableBase
from rgxlog.engine.state.term_graph import EvalState, GraphBase, ComputationTermGraph

VALUE_ATTRIBUTE = 'value'
OUT_REL_ATTRIBUTE = "output_rel"

FREE_VAR_PREFIX = "COL"


class ExecutionBase(ABC):
    """
    Abstraction for a class that gets a term graph and executes it
    """

    # TODO@niv: i don't understand why we need this class, since `GenericExecution` is already generic.
    def __init__(self, parse_graph: GraphBase, term_graph: ComputationTermGraph,
                 symbol_table: SymbolTableBase, rgxlog_engine: RgxlogEngineBase):
        """
        @param parse_graph: a term graph to execute.
        @param symbol_table: a symbol table.
        @param rgxlog_engine: a rgxlog engine that will be used to execute the term graph.
        """

        super().__init__()
        self.parse_graph = parse_graph
        self.term_graph = term_graph
        self.symbol_table = symbol_table
        self.rgxlog_engine = rgxlog_engine

    @abstractmethod
    def execute(self) -> Tuple[Query, List]:
        """
        Executes the term graph.
        """
        pass


class GenericExecution(ExecutionBase):
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
    """

    def __init__(self, parse_graph: GraphBase, term_graph: ComputationTermGraph,
                 symbol_table: SymbolTableBase, rgxlog_engine: RgxlogEngineBase):
        super().__init__(parse_graph, term_graph, symbol_table, rgxlog_engine)

    def execute(self) -> Tuple[Query, List]:
        parse_graph = self.parse_graph
        rgxlog_engine = self.rgxlog_engine
        exec_result = None

        # get the parse_graph's node ids. note that the order of the ids does not actually matter as long as the statements
        # are ordered the same way as they were in the original program
        parse_node_ids = parse_graph.post_order_dfs()

        # execute each non computed statement in the parse graph
        for parse_id in parse_node_ids:
            parse_node_attrs = parse_graph[parse_id]

            if parse_node_attrs["state"] is EvalState.COMPUTED:
                continue

            # the parse node is not computed, get its type and compute it accordingly
            parse_node_type = parse_node_attrs["type"]

            if parse_node_type in ("root", "relation"):
                # pass and not continue, because we want to mark them as computed
                pass

            elif parse_node_type == "rule":
                rule = parse_node_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.declare_relation(rule.head_relation.as_relation_declaration())

            elif parse_node_type == "relation_declaration":
                relation_decl = parse_node_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.declare_relation(relation_decl)

            elif parse_node_type == "add_fact":
                fact = parse_node_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.add_fact(fact)

            elif parse_node_type == "remove_fact":
                fact = parse_node_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.remove_fact(fact)

            elif parse_node_type == "query":
                # we return the query as well as the result, because we print as part of the output
                query = parse_node_attrs[VALUE_ATTRIBUTE]
                self.compute_rule(query.relation_name)
                exec_result = (query, rgxlog_engine.query(query))

            else:
                raise ValueError("illegal node type in parse graph")

            # statement was executed, mark it as "computed"
            parse_graph.set_node_attribute(parse_id, "state", EvalState.COMPUTED)

        return exec_result

    def compute_node(self, node_id: int) -> None:
        """
        Computes the current node based on its type.

        @param node_id: the current node.
        """

        def compute_rule_rel_node(term_attrs_: Dict) -> None:
            """
            Computes a rule rel node.

            @param term_attrs_: the attributes of the rule rel node.
            """
            rule_rel = term_attrs_[VALUE_ATTRIBUTE]
            rule_name = rule_rel.relation_name
            rel_in: Relation = get_child_relation(rule_name)
            copy_rel = self.rgxlog_engine.operator_copy(rel_in, rule_name)
            self.term_graph.set_node_attribute(rule_name, OUT_REL_ATTRIBUTE, copy_rel)

        def compute_join_node(node_id_: int) -> None:
            """
            Computes a join node.

            @param node_id_: the node.
            """

            join_rel = self.rgxlog_engine.operator_join(get_children_relations(node_id_))
            self.term_graph.set_node_attribute(node_id_, OUT_REL_ATTRIBUTE, join_rel)

        def compute_project_node(node_id_: int, term_attrs_: Dict) -> None:
            """
            Computes a project node.

            @param node_id_: the node.
            @param term_attrs_: the attributes of the node.
            """

            output_rel: Relation = get_child_relation(node_id_)
            project_info = term_attrs_[VALUE_ATTRIBUTE]
            project_rel = self.rgxlog_engine.operator_project(output_rel, project_info)
            self.term_graph.set_node_attribute(node_id_, OUT_REL_ATTRIBUTE, project_rel)

        def compute_calc_node(node_id_: int, term_attrs_: Dict) -> None:
            """
            Computes a calc node.

            @param node_id_: the node.
            @param term_attrs_: the attributes of the node.
            """

            children = get_children_relations(node_id_)
            rel_in = children[0] if children else None
            # note: we use the same `VALUE_ATTRIBUTE` keyword for different things to be able to print it easily
            # when printing the tree
            ie_rel_in: IERelation = term_attrs_[VALUE_ATTRIBUTE]
            ie_func_data = self.symbol_table.get_ie_func_data(ie_rel_in.relation_name)
            ie_rel_out = self.rgxlog_engine.compute_ie_relation(ie_rel_in, ie_func_data, rel_in)
            self.term_graph.set_node_attribute(node_id_, OUT_REL_ATTRIBUTE, ie_rel_out)

        def compute_union_node(node_id_: int) -> None:
            """
            Computes a union node.

            @param node_id_: the node.
            """

            union_rel = self.rgxlog_engine.operator_union(get_children_relations(node_id_))
            self.term_graph.set_node_attribute(node_id_, OUT_REL_ATTRIBUTE, union_rel)

        def compute_select_node(node_id_: int, term_attrs_: Dict) -> None:
            """
            Computes a select node.

            @param node_id_: the node.
            @param term_attrs_: the attributes of the node.
            """

            output_rel = get_child_relation(node_id_)
            select_info = term_attrs_[VALUE_ATTRIBUTE]
            select_rel = self.rgxlog_engine.operator_select(output_rel, select_info)
            term_graph.set_node_attribute(node_id_, OUT_REL_ATTRIBUTE, select_rel)

        def is_node_computed(node_id_) -> bool:
            """
            Finds out whether the node is computed.

            @param node_id_: the node for which we check the status.
            @return: True if all the children of the node are computed or it has no children, False otherwise.
            """

            children = term_graph.get_children(node_id_)
            if not children:
                return True

            children_statuses_is_computed = [self.term_graph[child_id]["state"] is EvalState.COMPUTED
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

        term_graph = self.term_graph

        term_attrs = term_graph[node_id]
        if term_attrs["state"] is EvalState.COMPUTED:
            return

        term_type = term_attrs["type"]

        if term_type in "get_rel":
            term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, term_attrs["value"])

        elif term_type == "rule_rel":
            compute_rule_rel_node(term_attrs)

        elif term_type == "union":
            compute_union_node(node_id)

        elif term_type == "join":
            compute_join_node(node_id)

        elif term_type == "project":
            compute_project_node(node_id, term_attrs)

        elif term_type == "calc":
            compute_calc_node(node_id, term_attrs)

        elif term_type == "select":
            compute_select_node(node_id, term_attrs)

        else:
            raise ValueError(f"illegal term type in rule's execution graph. The bad type is {term_type}")

        # statement was executed, mark it as "computed" or "visited"
        compute_status = EvalState.COMPUTED if is_node_computed(node_id) else EvalState.VISITED
        term_graph.set_node_attribute(node_id, 'state', compute_status)

    def compute_rule(self, relation_name: str, to_reset: bool = True, only_one_iteration: bool = False) -> bool:
        """
        Computes the rule (including the mutual recursive rules).

        @param relation_name: the name of the relation to compute.
        @param to_reset: if set to True we reset the nodes after the computation.
        @param only_one_iteration: if set to True we evaluate one iteration, Otherwise we do fixed-point.
        """
        term_graph = self.term_graph
        rgxlog_engine = self.rgxlog_engine

        # check if the relation is base relation
        if not term_graph.has_node(relation_name):
            return True

        # stores all the nodes that were visited during the dfs
        visited_nodes = set()
        mutually_recursive = term_graph.get_mutually_recursive_relations(relation_name)

        # declare methods used in rule computation
        def compute_iteration() -> bool:
            """
            Computes one iteration. if reaches a mutually recursive relation it uses the relation current state
            (rather than computing it).

            @return: whether the rule we computed converged (no new tuples).
            """

            initial_len = rgxlog_engine.get_table_len(relation_name)
            compute_dfs(relation_name)

            return rgxlog_engine.get_table_len(relation_name) == initial_len

        def compute_dfs(node_id) -> None:
            """
            Runs postorder dfs over the term graph and evaluates the tree.

            @param node_id: the current node.
            """
            if is_stop_dfs(node_id):
                return

            visited_nodes.add(node_id)
            children = self.term_graph.get_children(node_id)
            for child in children:
                compute_dfs(child)

            self.compute_node(node_id)

        def is_stop_dfs(node_id) -> bool:
            """
            Catches the cases of rule rel.

            @param node_id: the current node.
            @return: True if we can continue the DFS, False otherwise.
            """

            if node_id in visited_nodes:
                return True

            term_attrs = self.term_graph[node_id]
            if term_attrs["state"] is EvalState.COMPUTED:
                return True

            # if type is not rule_rel it's fine to continue the dfs
            if term_attrs["type"] != "rule_rel":
                return False

            rule_rel = term_attrs[VALUE_ATTRIBUTE]
            if rule_rel.relation_name not in mutually_recursive:
                # computes the independent rule and stop
                self.compute_rule(rule_rel.relation_name, to_reset=False)
                return True

            # if rule rel is the rule we're currently computing - continue the dfs
            if rule_rel.relation_name == relation_name:
                return False

            # in case of dependent rule we use the current state of that rule
            term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, rule_rel)
            return True

        def set_visited_nodes(state_: EvalState) -> None:
            """
            Marks all the nodes that were visited during the computation as not computed.

            @param state_: the state of the visited nodes.
            """

            for term_id in self.term_graph.post_order_dfs_from(relation_name):
                self.term_graph.set_node_attribute(term_id, "state", state_)

        if only_one_iteration:
            return compute_iteration()

        # clear all the mutually recursive tables.
        rgxlog_engine.clear_tables(mutually_recursive)

        fixed_point = False
        while not fixed_point:
            # computes one iteration for all of the mutually recursive rules
            stopped = [self.compute_rule(relation, only_one_iteration=True)
                       for relation in mutually_recursive]

            # we stop iterating when all the rules converged at the same step
            fixed_point = all(stopped)

        state = EvalState.NOT_COMPUTED if to_reset else EvalState.COMPUTED
        set_visited_nodes(state)


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
