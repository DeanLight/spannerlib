from rgxlog import magic_session

from tests.utils import run_query_assert_output


def test_magic_session_basic():
    session = magic_session
    expected_result_intro = """printing results for query 'uncle(X, Y)':
      X  |  Y
    -----+------
     bob | greg
    """

    pre_query = """new uncle(str, str)
                   uncle("bob", "greg")
                   """

    query = "?uncle(X,Y)"

    run_query_assert_output(session, query, expected_result_intro, pre_query)
