from tests.utils import run_test


def test_rust_regex():
    query = """
        string_rel(X) <- rgx_string("aa",".+") -> (X)
        span_rel(X) <- rgx_span("aa",".+") -> (X)
        ?string_rel(X)
        ?span_rel(X)
        """

    expected_result = """printing results for query 'string_rel(X)':
          X
        -----
          a
         aa

        printing results for query 'span_rel(X)':
           X
        --------
         [0, 1)
         [0, 2)
         [1, 2)
        """

    run_test(query, expected_result)


def test_rust_regex_reuse_function():
    query = """
            string_rel(X) <- rgx_string("bb",".+") -> (X)
            string_rel2(X) <- rgx_string("cc",".+") -> (X)
            ?string_rel(X)
            ?string_rel2(X)
            """

    expected_result = """printing results for query 'string_rel(X)':
                          X
                        -----
                          b
                         bb
                        
                        printing results for query 'string_rel2(X)':
                          X
                        -----
                          c
                         cc"""

    run_test(query, expected_result)


def test_rust_regex_groups():
    # @niv: @dean, how does the user know what order to expect, regarding the capture groups?
    # @response, when introducing this default ie function, you should tell him with some examples
    # TODO@niv: add example for the order in the introduction
    text = "aab"
    pattern = "(?P<group_all>(?P<group_a>a+)(?P<group_b>b+))"

    query = f"""
            group_string_rel(X,Y,Z) <- rgx_string("{text}","{pattern}") -> (X,Y,Z)
            group_span_rel(X,Y,Z) <- rgx_span("{text}","{pattern}") -> (X,Y,Z)
            ?group_string_rel(X, Y, Z)
            ?group_span_rel(X,Y, Z)
            """

    expected_result = """printing results for query 'group_string_rel(X, Y, Z)':
          X  |  Y  |  Z
        -----+-----+-----
         aa  |  b  | aab
          a  |  b  | ab

        printing results for query 'group_span_rel(X, Y, Z)':
           X    |   Y    |   Z
        --------+--------+--------
         [0, 2) | [2, 3) | [0, 3)
         [1, 2) | [2, 3) | [1, 3)"""

    run_test(query, expected_result)


def test_python_regex():
    query = """
           py_string_rel(X) <- py_rgx_string("aa",".+") -> (X)
           py_span_rel(X) <- py_rgx_span("aa",".+") -> (X)
           ?py_string_rel(X)
           ?py_span_rel(X)
           """

    expected_result = """printing results for query 'py_string_rel(X)':
              X
            -----
             aa
            
            printing results for query 'py_span_rel(X)':
               X
            --------
             [0, 2)"""

    run_test(query, expected_result)
