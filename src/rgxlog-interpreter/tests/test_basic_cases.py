from rgxlog.engine.utils.general_utils import QUERY_RESULT_PREFIX
from tests.utils import run_test


def test_copy_table_rule():
    commands = """
            new B(int, int)
            B(1, 1)
            B(1, 2)
            B(2, 3)
            A(X, Y) <- B(X, Y)
            ?A(X, Y)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   3
    """

    run_test(commands, expected_result)


def test_join_two_tables():
    commands = """
        new B(int, int)
        new C(int, int)
        B(1, 1)
        B(1, 2)
        B(2, 3)
        C(2, 2)
        C(1, 1)
        D(X, Y, Z) <- B(X, Y), C(Y, Z)
        ?D(X, Y, Z)
    """

    expected_result = f"""{QUERY_RESULT_PREFIX}'D(X, Y, Z)':
       X |   Y |   Z
    -----+-----+-----
       1 |   2 |   2
       1 |   1 |   1
    """

    run_test(commands, expected_result)


def test_relation_with_same_free_var():
    commands = """
        new B(int, int)
        B(1, 1)
        B(1, 2)
        B(2, 2)
        A(X) <- B(X, X)
        ?A(X)
    """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X)':
       X
    -----
       1
       2
    """

    run_test(commands, expected_result)


def test_union_rule_with_same_vars():
    commands = """
        new B(int, int)
        new C(int, int)
        B(1, 1)
        B(1, 2)
        B(2, 3)
        C(2, 2)
        C(1, 1)

        A(X, Y) <- B(X, Y)
        A(X, Y) <- C(X, Y)
        ?A(X, Y)
    """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   2
       2 |   3
    """

    run_test(commands, expected_result)


def test_union_rule_with_different_vars():
    commands = """
        new B(int, int)
        new C(int, int)
        B(1, 1)
        B(1, 2)
        B(2, 3)
        C(2, 2)
        C(1, 1)

        A(X, Y) <- B(X, Y)
        A(Z, W) <- C(Z, W)
        ?A(X, Y)
    """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   2
       2 |   3
    """

    run_test(commands, expected_result)


def test_project():
    commands = """
            new B(int, int)
            B(1, 1)
            B(1, 2)

            A(X) <- B(X, Y)
            ?A(X)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X)':
       X
    -----
       1 
    """

    run_test(commands, expected_result)


def test_add_fact_after_rule():
    commands = """
            new B(int, int)
            B(1, 1)
            A(X, Y) <- B(X, Y)
            B(1, 2)
            ?A(Z, W)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(Z, W)':
       Z |   W
    -----+-----
       1 |   1
       1 |   2
    """

    run_test(commands, expected_result)


def test_datatypes():
    commands = """
            new B(int, str, span)
            B(1, "2", [1, 2))
            ?B(X, Y, Z)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'B(X, Y, Z)':
       X |   Y |   Z
    -----+-----+--------
       1 |   2 | [1, 2)
    """

    run_test(commands, expected_result)


def test_join_same_relation():
    commands = """
            new Parent(str, str)
            Parent("God", "Abraham")
            Parent("Abraham", "Isaac")
            Parent("Isaac", "Benny")


            GrandParent(G, C) <- Parent(G, M), Parent(M, C)
            ?GrandParent(X, "Isaac")
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'GrandParent(X, "Isaac")':
      X
    -----
     God
    """

    run_test(commands, expected_result)


def test_rule_with_constant():
    commands = """
              new B(int, int)
              new C(int, int)
              B(1, 1)
              B(1, 2)
              B(2, 3)
              C(2, 2)
              C(1, 1)

              A(X) <- B(1, X)
              ?A(X)
           """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X)':
       X
    -----
       1
       2
    """

    run_test(commands, expected_result)


def test_rule_with_true_value():
    commands = """
               new B(int, int)
               new C(int, int)
               B(1, 1)
               B(1, 2)
               B(2, 3)
               C(2, 2)
               C(1, 1)

               A(X, Y) <- B(X, Y), C(1, 1)
               ?A(X, Y)
            """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   3
    """

    run_test(commands, expected_result)


def test_rule_with_false_value():
    commands = """
               new B(int, int)
               new C(int, int)
               B(1, 1)
               B(1, 2)
               B(2, 3)
               C(2, 2)
               C(1, 1)

               A(X, Y) <- B(X, Y), C(0, 0)
               ?A(X, Y)
            """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X, Y)':
    []
    """

    run_test(commands, expected_result)


def test_query_with_same_var():
    commands = """
              new B(int, int)
              B(1, 1)
              B(1, 2)
              B(2, 3)

              A(X, Y) <- B(X, Y)
              ?A(X, X)
           """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X, X)':
       X |   X
    -----+-----
       1 |   1
    """

    run_test(commands, expected_result)


def test_query_with_constant_value():
    commands = """
               new B(int, int)
               B(1, 1)
               B(1, 2)
               B(2, 3)

               A(X, Y) <- B(X, Y)
               ?A(1, X)
            """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(1, X)':
       X
    -----
       1
       2
    """

    run_test(commands, expected_result)


def test_remove_rule():
    commands = """
               new B(int, int)
               new C(int, int)
               B(1, 1)
               B(1, 2)
               B(2, 3)
               C(2, 2)
               C(1, 1)

               A(X, Y) <- B(X, Y)
               A(X, Y) <- C(X, Y)

            """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   3
     """

    session = run_test(commands)

    session.remove_rule("A(X, Y) <- C(X, Y)")

    run_test("?A(X, Y)", expected_result, test_session=session)


def test_select_and_join():
    commands = """
            new B(int)
            new C(int, int)
            B(2)
            C(1, 4)
            C(2, 5)
            A(X) <- B(X), C(X, 5)
            ?A(X)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(X)':
       X
    -----
       2
    """

    run_test(commands, expected_result)


def test_query_true_value():
    commands = """
            new A(int)
            A(1)
            ?A(1)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(1)':
    [()]
    """

    run_test(commands, expected_result)


def test_query_false_value():
    commands = """
            new A(int)
            A(1)
            ?A(2)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(2)':
    []
    """

    run_test(commands, expected_result)
