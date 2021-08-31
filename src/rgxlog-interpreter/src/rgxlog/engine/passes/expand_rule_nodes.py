from collections import OrderedDict

from typing import Set, Optional, Union, Dict, List, OrderedDict as OrderedDictType

from rgxlog.engine.datatypes.ast_node_types import Relation, IERelation, Rule
from rgxlog.engine.passes.lark_passes import GenericPass
from rgxlog.engine.state.symbol_table import SymbolTableBase
from rgxlog.engine.state.term_graph import EvalState, ComputationTermGraph, NetxGraph
from rgxlog.engine.utils.general_utils import (get_input_free_var_names, get_output_free_var_names,
                                               get_free_var_to_relations_dict)


class AddRulesToComputationTermGraph(GenericPass):
    """
    This pass transforms each rule node into an execution tree and adds it to the term graph.
    """

    def __init__(self, parse_graph: NetxGraph, symbol_table: SymbolTableBase,
                 term_graph: ComputationTermGraph, debug: bool):
        self.parse_graph = parse_graph
        self.symbol_table = symbol_table
        self.term_graph = term_graph
        self.debug = debug

    def _get_rule_nodes(self) -> List[Rule]:
        """
        Finds all rule subtrees.

        @return: a list of rules to expand.
        """

        term_ids = self.parse_graph.post_order_dfs()
        rule_nodes: List[Rule] = list()

        for term_id in term_ids:
            term_attrs = self.parse_graph.get_node_attributes(term_id)

            # the term is not computed, get its type and compute it accordingly
            term_type = term_attrs['type']

            if term_type == "rule":
                # make sure that the rule wasn't expanded before
                if term_attrs['state'] == EvalState.NOT_COMPUTED:
                    rule_nodes.append(term_attrs['value'])
                    self.parse_graph.set_node_attribute(term_id, 'state', EvalState.VISITED)

        return rule_nodes

    def _add_rules_to_computation_graph(self) -> None:
        """
        Generates and adds all the execution trees to the term graph.
        """

        rule_nodes = self._get_rule_nodes()
        for rule in rule_nodes:
            # modifies the term graph
            self.add_rule_to_computation_graph(rule)

    @staticmethod
    def _compute_bounding_graph(relations: Set[Relation], ie_relations: Set[IERelation]) -> \
            OrderedDictType[IERelation, Set[Union[Relation, IERelation]]]:
        """
        This class gets body relations of a rule and computes for each ie relation the relations that bound it.
        @note: In some cases ie relation is bounded by other ie relation.
                e.g. A(X) <- B(Y), C(Z) -> (X), D(Y) -> (Z); in this example C is bounded only by D.

        @param relations: set of the regular relations in the rule body.
        @param ie_relations: set of the ie relations in the rule body.
        @return: a dictionary that maps each ie function to a set of it's bounding relations.
        """

        # holds the ie relation that are bounded
        bounded_ie_relations = set()

        # maps each ie relation to it's bounding relations
        bounding_graph = OrderedDict()

        def find_bounding_relations_of_ie_function(ie_rel: IERelation) -> (
                Optional[Set[Union[Relation, IERelation]]]):
            """
            Finds all the relation that are already bounded that bind the ie relation.

            @param ie_rel: the ie relation to bound.
            @return: set of the bounding relations.
            """

            bounded_vars = set()
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
                return

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

    def add_rule_to_computation_graph(self, rule: Rule) -> None:
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
        """

        # maps each relation to it's node id in the term graph.
        relation_to_branch_id: Dict[Union[Relation, IERelation, int]] = dict()

        # stores the nodes that were added to to execution graph
        nodes = set()

        def add_node(node_id: int) -> None:
            """
            Saves all the nodes that were added due to the rule.

            @param node_id: a new node that was added.
            """
            nodes.add(node_id)

        def add_join_branch(head_id: int, joined_relations: Set[Union[Relation, IERelation]],
                            future_ie_relations: Optional[Set[IERelation]] = None) -> int:
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
            join_node_id_ = self.term_graph.add_node(type="join", value=join_dict)
            add_node(join_node_id_)

            self.term_graph.add_edge(head_id, join_node_id_)
            for relation in joined_relations:
                add_relation_branch(relation, join_node_id_)

            return join_node_id_

        def add_relation_to(relation: Union[Relation, IERelation], father_node_id: int) -> None:
            """
            Adds relation to father id.

            @param relation: a relation.
            @param father_node_id: the node to which the relation will be connected.
            """

            rel_id = self.term_graph.get_relation_id(relation.relation_name)
            is_base_rel = rel_id == -1

            get_rel_id = self.term_graph.add_node(type="get_rel", value=relation)
            add_node(get_rel_id)

            # cache the branch
            relation_to_branch_id[relation] = get_rel_id
            self.term_graph.add_edge(father_node_id, get_rel_id)

            # if relation is a rule relation we connect it to the root of the relation (rel_id)
            if not is_base_rel:
                self.term_graph.add_edge(get_rel_id, rel_id)

        def add_relation_branch(relation: Union[Relation, IERelation], join_node_id_: int) -> None:
            """
            Adds relation to the join node.
            Finds all the columns of the relation that needed to be filtered and Adds select branch if needed.

            @param relation: a relation.
            @param join_node_id_: the join node to which the relation will be connected.
            """

            # check if the branch already exists
            if relation in relation_to_branch_id:
                self.term_graph.add_edge(join_node_id_, relation_to_branch_id[relation])
                return

            free_vars = get_output_free_var_names(relation)
            term_list = relation.get_term_list()

            # check if there is a constant (A("4")), or there is a free var that appears multiple times (A(X, X))
            if len(free_vars) != len(term_list) or len(term_list) != len(set(term_list)):
                # create select node and connect relation branch to it
                select_info = relation.get_select_cols_values_and_types()
                select_node_id = self.term_graph.add_node(type="select", value=select_info)
                add_node(select_node_id)
                self.term_graph.add_edge(join_node_id_, select_node_id)
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
            calc_node_id_ = self.term_graph.add_node(type="calc", value=ie_relation_)
            add_node(calc_node_id_)

            # join all the ie relation's bounding relations. The bounding relations already exists in the graph!
            # (since we iterate on the ie relations in the same order they were bounded).
            bounding_relations = bounding_graph_[ie_relation_]
            add_join_branch(calc_node_id_, bounding_relations)
            self.term_graph.add_edge(join_node_id_, calc_node_id_)
            return calc_node_id_

        head_relation = rule.head_relation
        relations, ie_relations = rule.get_relations_by_type()
        # computes the bounding graph (it's actually an ordered dict).
        bounding_graph = AddRulesToComputationTermGraph._compute_bounding_graph(relations, ie_relations)

        # make root
        union_id = self.term_graph.add_relation(head_relation)
        project_id = self.term_graph.add_node(type="project", value=head_relation.term_list)
        self.term_graph.add_edge(union_id, project_id)
        add_node(project_id)

        # connect all regular relations to join node
        join_node_id = add_join_branch(project_id, relations, ie_relations)

        # iterate over ie relations in the same order they were bounded
        for ie_relation in bounding_graph:
            calc_node_id = add_calc_branch(join_node_id, ie_relation, bounding_graph)
            relation_to_branch_id[ie_relation] = calc_node_id

        self.term_graph.add_rule(rule, nodes)
        self.term_graph.add_dependencies(head_relation, relations)

    def run_pass(self, **kwargs):
        self._add_rules_to_computation_graph()
        if self.debug:
            print(f"term graph after {self.__class__.__name__}:\n{self.term_graph}")
