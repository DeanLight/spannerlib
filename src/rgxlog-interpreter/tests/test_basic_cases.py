from tests.utils import run_test


def test_introduction():
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


def test_copy_table_rule():
    query = """
            new B(int, int)
            B(1, 1)
            B(1, 2)
            B(2, 3)
            A(X, Y) <- B(X, Y)
            ?A(X, Y)
        """

    expected_result = """printing results for query 'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   3
    """

    run_test(query, expected_result)


def test_join_two_tables():
    query = """
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

    expected_result = """printing results for query 'D(X, Y, Z)':
       X |   Y |   Z
    -----+-----+-----
       1 |   2 |   2
       1 |   1 |   1
    """

    run_test(query, expected_result)


def test_relation_with_same_free_var():
    query = """
        new B(int, int)
        B(1, 1)
        B(1, 2)
        B(2, 2)
        A(X) <- B(X, X)
        ?A(X)
    """

    expected_result = """printing results for query 'A(X)':
       X
    -----
       1
       2
    """

    run_test(query, expected_result)


def test_union_rule_with_same_vars():
    query = """
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

    expected_result = """printing results for query 'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   2
       2 |   3
    """

    run_test(query, expected_result)


def test_union_rule_with_different_vars():
    query = """
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

    expected_result = """printing results for query 'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   2
       2 |   3
    """

    run_test(query, expected_result)


def test_project():
    query = """
            new B(int, int)
            B(1, 1)
            B(1, 2)

            A(X) <- B(X, Y)
            ?A(X)
        """

    expected_result = """printing results for query 'A(X)':
       X
    -----
       1 
    """

    run_test(query, expected_result)


def test_add_fact_after_rule():
    query = """
            new B(int, int)
            B(1, 1)
            A(X, Y) <- B(X, Y)
            B(1, 2)
            ?A(Z, W)
        """

    expected_result = """printing results for query 'A(Z, W)':
       Z |   W
    -----+-----
       1 |   1
       1 |   2
    """

    run_test(query, expected_result)


def test_datatypes():
    query = """
            new B(int, str, span)
            B(1, "2", [1, 2))
            ?B(X, Y, Z)
        """

    expected_result = """printing results for query 'B(X, Y, Z)':
       X |   Y |   Z
    -----+-----+--------
       1 |   2 | [1, 2)
    """

    run_test(query, expected_result)


def test_join_same_relation():
    query = """
            new Parent(str, str)
            Parent("God", "Abraham")
            Parent("Abraham", "Isaac")
            Parent("Isaac", "Benny")


            GrandParent(G, C) <- Parent(G, M), Parent(M, C)
            ?GrandParent(X, "Isaac")
        """

    expected_result = """printing results for query 'GrandParent(X, "Isaac")':
      X
    -----
     God
    """

    run_test(query, expected_result)


def test_rule_with_constant():
    query = """
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

    expected_result = """printing results for query 'A(X)':
       X
    -----
       1
       2
    """

    run_test(query, expected_result)


def test_rule_with_true_value():
    query = """
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

    expected_result = """printing results for query 'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   3
    """

    run_test(query, expected_result)


def test_rule_with_false_value():
    query = """
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

    expected_result = """printing results for query 'A(X, Y)':
    []
    """

    run_test(query, expected_result)


def test_query_with_same_var():
    query = """
              new B(int, int)
              B(1, 1)
              B(1, 2)
              B(2, 3)

              A(X, Y) <- B(X, Y)
              ?A(X, X)
           """

    expected_result = """printing results for query 'A(X, X)':
       X |   X
    -----+-----
       1 |   1
    """

    run_test(query, expected_result)


def test_query_with_constant_value():
    query = """
               new B(int, int)
               B(1, 1)
               B(1, 2)
               B(2, 3)

               A(X, Y) <- B(X, Y)
               ?A(1, X)
            """

    expected_result = """printing results for query 'A(1, X)':
       X
    -----
       1
       2
    """

    run_test(query, expected_result)


def test_remove_rule():
    query = """
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

    expected_result = """printing results for query 'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   3
     """

    session = run_test(query)

    session.remove_rule("A(X, Y) <- C(X, Y)")

    run_test("?A(X, Y)", expected_result, test_session=session)


def test_select_and_join():
    query = """
            new B(int)
            new C(int, int)
            B(2)
            C(1, 4)
            C(2, 5)
            A(X) <- B(X), C(X, 5)
            ?A(X)
        """

    expected_result = """printing results for query 'A(X)':
       X
    -----
       2
    """

    run_test(query, expected_result)


def test_query_true_value():
    query = """
            new A(int)
            A(1)
            ?A(1)
        """

    expected_result = """printing results for query 'A(1)':
    [()]
    """

    run_test(query, expected_result)


def test_query_false_value():
    query = """
            new A(int)
            A(1)
            ?A(2)
        """

    expected_result = """printing results for query 'A(2)':
    []
    """

    run_test(query, expected_result)
