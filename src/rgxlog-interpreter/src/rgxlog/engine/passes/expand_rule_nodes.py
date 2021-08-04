from collections import OrderedDict

from typing import Tuple, Set, Optional, Union, Dict, List

from rgxlog.engine.datatypes.ast_node_types import Relation, IERelation
from rgxlog.engine.execution import RgxlogEngineBase
from rgxlog.engine.passes.lark_passes import GenericPass
from rgxlog.engine.state.symbol_table import SymbolTableBase
from rgxlog.engine.state.term_graph import EvalState, ExecutionTermGraph, NetxTermGraph
from rgxlog.engine.utils.general_utils import get_input_free_var_names, get_output_free_var_names, \
    get_free_var_to_relations_dict


class BoundingGraph:
    """
    This class gets body relations of a rule and computes for each ie relation the relations that bound it.
    @note: In some cases ie relation is bounded by other ie relation.
            e.g. A(X) <- B(Y), C(Z) -> (X), D(Y) -> (Z); in this example C is bounded only by D.
    """

    def __init__(self, relations: Set[Relation], ie_relations: Set[IERelation]):
        """
        @param relations: set of the regular relations in the rule body
        @param ie_relations: set of the ie relations in the rule body
        """
        self.relations = relations
        self.ie_relations = ie_relations

        # holds the ie relation that are bounded
        self.bounded_ie_relations = set()

        # maps each ie relation to it's bounding relations
        self.bounding_graph = OrderedDict()

    def find_bounding_relations_of_ie_function(self, ie_relation: IERelation) -> \
            Optional[Set[Union[Relation, IERelation]]]:
        """
        Finds all the relation that are already bounded that bind the ie relation.
        @param ie_relation: the ie relation to bound.
        @return: set of the bounding relations.
        """

        bounded_vars = set()
        bounding_relations = set()
        ie_input_terms = get_input_free_var_names(ie_relation)

        # iterate over all the bounded relations
        for relation in (self.relations | self.bounded_ie_relations):
            rel_terms = get_output_free_var_names(relation)
            # check if the relation and the ie relation have some common free vars
            mutual_vars = rel_terms.intersection(ie_input_terms)
            if len(mutual_vars) > 0:
                bounding_relations.add(relation)
                bounded_vars = bounded_vars.union(mutual_vars)

        # check whether all ie relation's free vars are bounded
        if bounded_vars == ie_input_terms:
            return bounding_relations
        else:
            # the ie relation can't be bounded yet
            return

    def compute_graph(self) -> Dict[IERelation, Set[Union[Relation, IERelation]]]:
        """
        See class description.
        @return: a dictionary that maps each ie function to a set of it's bounding relations.
        """

        # The function will eventually stop since the rule is safe.
        while True:
            # find the unbounded ie relations
            unbounded_ie_relations = self.ie_relations.difference(self.bounded_ie_relations)
            if len(unbounded_ie_relations) == 0:
                # all the ie relation are bounded
                break

            for ie_relation in unbounded_ie_relations:
                bounding_relations = self.find_bounding_relations_of_ie_function(ie_relation)
                if bounding_relations is not None:
                    # we managed to bind the ie relation
                    self.bounding_graph[ie_relation] = bounding_relations
                    self.bounded_ie_relations.add(ie_relation)

        return self.bounding_graph


class AddRuleToTermGraph:
    """
    This class adds the execution graph of a rule to the global term graph.
    Implements the following pseudo code:

        def generate_inference_tree(self, head, body):
            bounding_graph = find_bounding_graph(body)
            build_root
            connect_all_bodies_to_root_with_join
            for each ie_function:
            make calc_node
            connect to join of all bounding bodies
    """

    def __init__(self, term_graph: ExecutionTermGraph, head_relation: Relation,
                 relations: Set[Relation], ie_relations: Set[IERelation]):
        """
        note: term_graph is passed like a pointer, so it modifies

        @param term_graph: the global term graph (contains all the execution trees of all the rules).
        @param head_relation: the relation head of the rule.
        @param relations: set of relations in rule body.
        @param ie_relations: set of ie_relations in rule body.
        """
        self.term_graph = term_graph

        # a set of regular relations and a set of ie relations in the rule body.
        self.head_relation = head_relation
        self.relations = relations
        self.ie_relations = ie_relations

        # maps each relation to it's node id in the term graph.
        self.relation_to_branch_id: Dict[Union[Relation, IERelation, int]] = dict()

        # computes the bounding graph (it's actually an ordered dict).
        self.bounding_graph = BoundingGraph(self.relations, self.ie_relations).compute_graph()

    def add_join_branch(self, head_id: int, relations: Set[Union[Relation, IERelation]],
                        future_ie_relations: Optional[Set[IERelation]] = None) -> Optional[int]:
        """
        Connects all the relations to a join node. Connects the join_node to head_id.

        @param head_id: the node to which join node will be connected.
        @param relations: a set of relations.
        @param future_ie_relations: a set of ie relations that will be added to branch in the future.
        @return: the id of the join node.
        """

        future_ies = set() if future_ie_relations is None else future_ie_relations
        total_relations = relations | future_ies

        # check if there is one relation (we don't need join)
        if len(total_relations) == 1:
            self.add_relation_branch(next(iter(total_relations)), head_id)
            return

        join_dict = get_free_var_to_relations_dict(total_relations)
        if join_dict:
            join_node_id = self.term_graph.add_term(type="join", value=join_dict)
            self.term_graph.add_edge(head_id, join_node_id)
            for relation in relations:
                self.add_relation_branch(relation, join_node_id)

            return join_node_id

    def add_relation_to(self, relation: Union[Relation, IERelation], father_node_id: int) -> None:
        """
        Adds relation to father id.

        @param relation: a relation
        @param father_node_id: the node to which the relation will be connected.
        """

        root_rel_id = self.term_graph.get_relation_id(relation)
        is_base_rel = root_rel_id == -1
        # TODO@niv: @tom, is there any difference between those two?
        rel_type = "base_rel" if is_base_rel else "get_rel"
        rel_id = self.term_graph.add_term(type=rel_type, value=relation)

        self.relation_to_branch_id[relation] = rel_id
        self.term_graph.add_edge(father_node_id, rel_id)
        if not is_base_rel:
            self.term_graph.add_edge(rel_id, root_rel_id)

    def add_relation_branch(self, relation: Union[Relation, IERelation], join_node_id: int) -> None:
        """
        Adds relation to the join node.
        Finds all the columns of the relation that needed to be filtered and Adds select branch if needed.

        @param relation: a relation.
        @param join_node_id: the join node to which the relation will be connected.
        """
        if relation in self.relation_to_branch_id:
            self.term_graph.add_edge(join_node_id, self.relation_to_branch_id[relation])
            return

        free_vars = get_output_free_var_names(relation)
        term_list = relation.get_term_list()

        if len(free_vars) != len(term_list) or len(term_list) != len(set(term_list)):
            select_info = relation.get_select_cols_values_and_types()
            select_node_id = self.term_graph.add_term(type="select", value=select_info)
            self.term_graph.add_edge(join_node_id, select_node_id)
            self.add_relation_to(relation, select_node_id)
            self.relation_to_branch_id[relation] = select_node_id
        else:
            # no need to filter
            self.add_relation_to(relation, join_node_id)

    def add_calc_branch(self, join_node_id: int, ie_relation: IERelation) -> int:
        """
        Adds a calc branch of the ie relation.

        @param join_node_id: the join node to which the branch will be connected.
        @param ie_relation: an ie relation
        @return: the calc_node's id.
        """
        calc_node_id = self.term_graph.add_term(type="calc", value=ie_relation)

        # join all the ie relation's bounding relations. The bounding relations already exists in the graph!
        # (since we iterate on the ie relations in the same order they were bounded).
        bounding_relations = self.bounding_graph[ie_relation]
        self.add_join_branch(calc_node_id, bounding_relations)
        self.term_graph.add_edge(join_node_id, calc_node_id)
        return calc_node_id

    def generate_execution_graph(self) -> None:
        """
        Generates the execution tree of the rule and adds it to the term graph.
        @return:
        """
        # make root
        union_id = self.term_graph.add_relation(self.head_relation)
        project_id = self.term_graph.add_term(type="project", value=self.head_relation.term_list)
        self.term_graph.add_edge(union_id, project_id)

        # connect all regular relations to join node
        join_node_id = self.add_join_branch(project_id, self.relations, self.ie_relations)

        # iterate over ie relations in the same order they were bounded
        for ie_relation in self.bounding_graph:
            calc_node_id = self.add_calc_branch(join_node_id, ie_relation)
            self.relation_to_branch_id[ie_relation] = calc_node_id


class ExpandRuleNodes(GenericPass):
    """
    This pass transforms each rule node into an execution tree and adds it to the term graph.
    """

    def __init__(self, parse_graph: NetxTermGraph, symbol_table: SymbolTableBase,
                 rgxlog_engine: RgxlogEngineBase, term_graph: ExecutionTermGraph, debug: int):
        self.parse_graph = parse_graph
        self.symbol_table = symbol_table
        self.engine = rgxlog_engine
        self.term_graph = term_graph
        self.debug = debug

    def _get_rule_node_ids(self) -> List[int]:
        """
        Finds all rule subtrees.

        @return: a list of id's of the subtrees roots.
        """
        term_ids = self.parse_graph.post_order_dfs()
        rule_node_ids: List[int] = list()

        for term_id in term_ids:
            term_attrs = self.parse_graph.get_term_attributes(term_id)

            # the term is not computed, get its type and compute it accordingly
            term_type = term_attrs['type']

            if term_type == "rule":
                _, body_id = self.get_rule_head_and_body_ids(term_id)
                body = self.parse_graph[body_id]
                state = body['state']
                if state == EvalState.NOT_COMPUTED:
                    rule_node_ids.append(term_id)
                    self.parse_graph.set_term_attribute(body_id, 'state', EvalState.VISITED)

        return rule_node_ids

    def get_rule_head_and_body_ids(self, rule_id: int):
        rule_children = self.parse_graph.get_children(rule_id)
        assert len(rule_children) == 2, "a rule that was not expanded must have exactly 2 children"
        return rule_children

    def get_relations(self, rule_id: int) -> Tuple[Relation, Set[Relation], Set[IERelation]]:
        """
        Extracts the head relation, the regular relations and the ie relations from the parse tree.

        @param rule_id: the root of to subtree from which we extract the information.
        @return: head relation, regular relations and ie relations inside the rule.
        """

        rule_head_id, rule_body_id = self.get_rule_head_and_body_ids(rule_id)
        rule_head = self.parse_graph[rule_head_id]
        head_relation: Relation = rule_head['value']

        body_relation_id_list = self.parse_graph.get_children(rule_body_id)
        all_relations_in_rule = [self.parse_graph[term_id] for term_id in body_relation_id_list]

        relations, ie_relations = set(), set()
        for relation_attrs in all_relations_in_rule:
            relation_object: Union[Relation, IERelation] = relation_attrs['value']
            relation_type: str = relation_attrs['type']

            if relation_type == "relation":
                relations.add(relation_object)
            else:
                ie_relations.add(relation_object)

        return head_relation, relations, ie_relations

    def expand(self) -> None:
        """
        Generates and adds all the execution trees to the term graph.
        """

        rule_node_ids = self._get_rule_node_ids()
        for rule_node_id in rule_node_ids:
            # modifies the term graph
            head_relation, relations, ie_relations = self.get_relations(rule_node_id)
            AddRuleToTermGraph(self.term_graph, head_relation, relations, ie_relations).generate_execution_graph()

    def run_pass(self, **kwargs):
        self.expand()
        if self.debug:
            print(f"term graph after {self.__class__.__name__}:\n{self.term_graph}")