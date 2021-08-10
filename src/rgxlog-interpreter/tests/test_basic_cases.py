from tests.utils import run_test


def test_introduction():
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


def test_copy_table_rule():
    expected_result = """printing results for query 'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   3
    """

    query = """
            new B(int, int)
            B(1, 1)
            B(1, 2)
            B(2, 3)
            A(X, Y) <- B(X, Y)
            ?A(X, Y)
        """

    run_test(query, expected_result)


def test_join_two_tables():
    expected_result = """printing results for query 'D(X, Y, Z)':
       X |   Y |   Z
    -----+-----+-----
       1 |   2 |   2
       1 |   1 |   1
    """

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

    run_test(query, expected_result)


def test_relation_with_same_free_var():
    expected_result = """printing results for query 'A(X)':
       X
    -----
       1
       2
    """

    query = """
        new B(int, int)
        B(1, 1)
        B(1, 2)
        B(2, 2)
        A(X) <- B(X, X)
        ?A(X)
    """

    run_test(query, expected_result)


def test_union_rule_with_same_vars():
    expected_result = """printing results for query 'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   2
       2 |   3
    """

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

    run_test(query, expected_result)


def test_union_rule_with_different_vars():
    expected_result = """printing results for query 'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   2
       2 |   3
    """

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

    run_test(query, expected_result)


def test_project():
    expected_result = """printing results for query 'A(X)':
       X
    -----
       1 
    """

    query = """
        new B(int, int)
        B(1, 1)
        B(1, 2)

        A(X) <- B(X, Y)
        ?A(X)
    """

    run_test(query, expected_result)


def test_add_fact_after_rule():
    expected_result = """printing results for query 'A(Z, W)':
       Z |   W
    -----+-----
       1 |   1
       1 |   2
    """

    query = """
        new B(int, int)
        B(1, 1)
        A(X, Y) <- B(X, Y)
        B(1, 2)
        ?A(Z, W)
    """

    run_test(query, expected_result)


def test_datatypes():
    expected_result = """printing results for query 'B(X, Y, Z)':
       X |   Y |   Z
    -----+-----+--------
       1 |   2 | [1, 2)
    """

    query = """
        new B(int, str, span)
        B(1, "2", [1, 2))
        ?B(X, Y, Z)
    """

    run_test(query, expected_result)

def test_join_same_relation():
    expected_result = """printing results for query 'GrandParent(X, "Isaac")':
      X
    -----
     God
    """

    query = """
        new Parent(str, str)
        Parent("God", "Abraham")
        Parent("Abraham", "Isaac")
        Parent("Isaac", "Benny")

        
        GrandParent(G, C) <- Parent(G, M), Parent(M, C)
        ?GrandParent(X, "Isaac")
    """
    run_test(query, expected_result)


def test_remove_rule():
    expected_result = """printing results for query 'A(X, Y)':
       X |   Y
    -----+-----
       1 |   1
       1 |   2
       2 |   3
     """

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
    session = run_test(query)

    session.remove_rule("A(X, Y) <- C(X, Y)")

    run_test("?A(X, Y)", expected_result, test_session=session)
