from tests.utils import run_test


def test_magic_session_basic():
    query = """
        new uncle(str, str)
        uncle("bob", "greg")
        ?uncle(X,Y)
        """

    expected_result_intro = """printing results for query 'uncle(X, Y)':
              X  |  Y
            -----+------
             bob | greg
            """

    run_test(query, expected_result_intro)
