import logging
from typing import Any

from rgxlog.engine.datatypes.ast_node_types import Rule
from rgxlog.engine.passes.lark_passes import GenericPass
from rgxlog.engine.state.graphs import EvalState, TermGraphBase, GraphBase
from rgxlog.engine.utils.passes_utils import get_new_rule_nodes

logger = logging.getLogger(__name__)


class AddRulesToTermGraph(GenericPass):
    """
    This class traverses the parse graph and finds all the new rules.
    It adds these rules to the term graph (using term_graph's add rule method).
    """

    def __init__(self, parse_graph: GraphBase, term_graph: TermGraphBase, **kwargs: Any) -> None:
        self.parse_graph = parse_graph
        self.term_graph = term_graph

    def _add_rules_to_computation_graph(self) -> None:
        """
        Generates and adds all the execution trees to the term graph.
        """

        rule_nodes = get_new_rule_nodes(self.parse_graph)
        for rule_node_id in rule_nodes:
            # modifies the term graph
            rule: Rule = self.parse_graph[rule_node_id]["value"]
            self.parse_graph.set_node_attribute(rule_node_id, "state", EvalState.VISITED)
            self.term_graph.add_rule_to_term_graph(rule)

    def run_pass(self, **kwargs: Any) -> None:
        self._add_rules_to_computation_graph()
        logger.debug(f"term graph after {self.__class__.__name__}:\n{self.term_graph}")
