from rgxlog import magic_session

from tests.utils import run_query_assert_output, run_test


def test_magic_session_basic():
    expected_result_intro = """printing results for query 'uncle(X, Y)':
              X  |  Y
            -----+------
             bob | greg
            """

    query = """
        new uncle(str, str)
        uncle("bob", "greg")
        ?uncle(X,Y)
        """

    run_test(query, expected_result_intro)
