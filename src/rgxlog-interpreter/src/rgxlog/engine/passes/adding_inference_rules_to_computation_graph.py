from typing import List

from rgxlog.engine.datatypes.ast_node_types import Rule
from rgxlog.engine.passes.lark_passes import GenericPass
from rgxlog.engine.state.term_graph import EvalState, ComputationTermGraphBase, GraphBase


# TODO@niv: @tom, can you add a docstring for the class, with a short explanation?
class AddRulesToComputationTermGraph(GenericPass):

    def __init__(self, debug: bool, **kwargs):
        self.parse_graph: GraphBase = kwargs["parse_graph"]
        self.term_graph: ComputationTermGraphBase = kwargs["term_graph"]
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

            # make sure that the rule wasn't expanded before
            if term_type == "rule" and term_attrs['state'] == EvalState.NOT_COMPUTED:
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
            self.term_graph.add_rule_to_computation_graph(rule)

    def run_pass(self, **kwargs):
        self._add_rules_to_computation_graph()
        if self.debug:
            print(f"term graph after {self.__class__.__name__}:\n{self.term_graph}")
