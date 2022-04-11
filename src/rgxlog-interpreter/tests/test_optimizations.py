from rgxlog.engine.passes.optimizations_passes import PruneUnnecessaryProjectNodes, RemoveUselessRelationsFromRule
from rgxlog.engine.utils.general_utils import QUERY_RESULT_PREFIX

from tests.utils import run_test, get_session_with_optimizations


def test_prune_project_nodes() -> None:
    commands = """
               new B(int)
               new C(int)
               B(1)
               B(2)
               B(4)
               C(0)

               A(X) <- B(X), C(0)
               ?A(X)
            """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X)':
       X
    -----
       1
       2
       4
    """

    session = get_session_with_optimizations(term_graph_optimization_passes=(PruneUnnecessaryProjectNodes,))
    run_test(commands, expected_result, session=session)


def test_remove_useless_relation() -> None:
    commands = """
               new B(int)
               new C(int)
               B(1)
               B(2)
               B(4)
               C(0)

               A(X) <- B(X), C(Y)
               ?A(X)
            """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X)':
           X
        -----
           1
           2
           4
        """

    session = get_session_with_optimizations(parse_graph_optimization_passes=(RemoveUselessRelationsFromRule,))
    run_test(commands, expected_result, session=session)
