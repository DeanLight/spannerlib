from rgxlog import Session
from rgxlog.engine.utils.general_utils import QUERY_RESULT_PREFIX
from tests.utils import run_test


def test_assignment() -> None:
    commands = """
            new Relation(int, int)
            x = 1
            y = 2
            z = y
            Relation(x, y)
            Relation(y, x)
            ?Relation(X, x)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'Relation(X, 1)':
       X
    -----
       2
    """

    run_test(commands, expected_result)


def test_copy_table_rule() -> None:
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


def test_join_two_tables() -> None:
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


def test_relation_with_same_free_var() -> None:
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


def test_union_rule_with_same_vars() -> None:
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


def test_union_rule_with_different_vars() -> None:
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


def test_project() -> None:
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


def test_add_fact_after_rule() -> None:
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


def test_datatypes() -> None:
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


def test_join_same_relation() -> None:
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


def test_rule_with_constant() -> None:
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


def test_rule_with_true_value() -> None:
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


def test_rule_with_false_value() -> None:
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


def test_query_with_same_var() -> None:
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


def test_query_with_constant_value() -> None:
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


def test_remove_rule() -> None:
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

    run_test("?A(X, Y)", expected_result, session=session)


def test_select_and_join() -> None:
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


def test_query_true_value() -> None:
    commands = """
            new A(int)
            A(1)
            ?A(1)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(1)':
    [()]
    """

    run_test(commands, expected_result)


def test_query_false_value() -> None:
    commands = """
            new A(int)
            A(1)
            ?A(2)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'A(2)':
    []
    """

    run_test(commands, expected_result)


def test_nothing() -> None:
    # we can't use run_test when there is no output
    commands = ""

    expected_result = "[]"

    commands_result = str(Session().run_commands(commands, print_results=True))
    assert expected_result == commands_result, "expected string != result string"


def test_add_remove_fact() -> None:
    commands = """
                new rel(int)
                rel(8) <- True
                rel(16)
                rel(16) <- False
                rel(32)
                rel(16)
                rel(32) <- False
                ?rel(X)
                """

    expected_result = f"""{QUERY_RESULT_PREFIX}'rel(X)':
                           X
                        -----
                           8
                          16
                        """

    run_test(commands, expected_result)
