from tests.utils import run_test


def test_recursive():
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

    run_test(query, expected_result)