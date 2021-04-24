from rgxlog import magic_client
from rgxlog.engine.session import query_to_string
from tests.utils import compare_strings


def test_magic_client_basic():
    session = magic_client
    EXPECTED_RESULT_INTRO = """printing results for query 'uncle(X, Y)':
      X  |  Y
    -----+------
     bob | greg
    """

    session.run_query("new uncle(str, str)")
    session.run_query('uncle("bob", "greg")')
    query_result = session.run_query("?uncle(X,Y)", print_results=False)
    query_result_string = query_to_string(query_result)
    assert compare_strings(EXPECTED_RESULT_INTRO, query_result_string), "fail"
