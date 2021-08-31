from tests.utils import run_test


def test_recursive():
    query = '''
            new parent(str, str)
            parent("Liam", "Noah")
            parent("Noah", "Oliver")
            parent("James", "Lucas")
            parent("Noah", "Benjamin")
            parent("Benjamin", "Mason")
            ancestor(X,Y) <- parent(X,Y)
            ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y)

            ?ancestor("Liam", X)
            ?ancestor(X, "Mason")
            ?ancestor("Mason", X)
            '''

    expected_result = """printing results for query 'ancestor("Liam", X)':
            X
        ----------
          Mason
          Oliver
         Benjamin
           Noah

        printing results for query 'ancestor(X, "Mason")':
            X
        ----------
           Noah
           Liam
         Benjamin

        printing results for query 'ancestor("Mason", X)':
        []
        """

    run_test(query, expected_result)


def test_mutually_recursive_basic():
    query = """
            new C(int)
            C(1)
            C(2)
            C(3)

            B(X) <- C(X)
            A(X) <- B(X)
            B(X) <- A(X)

            ?A(X)
            """

    expected_result = """printing results for query 'A(X)':
        X
        -----
        1
        2
        3
    """

    run_test(query, expected_result)