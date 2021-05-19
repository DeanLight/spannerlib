from tests.utils import run_test

# TODO: there's a bug when using the same function twice (i.e. rule1 <- f1, rule2 <- f1)
#  not sure how to solve that right now
# @response, make a minimal bug reproduction test.
# this will probably go away when we revamp the engine anyway so dont sweat it

# def test_rust_regex():
#     # TODO@niv: @dean, see my comment at execution.py:~460 about repetition
#     # @response: this makes sense and is the intended behavior.
#     # That is why the algorithm developers use spans and not strings most of the time
#     expected_result = """printing results for query 'string_rel(X)':
#           X
#         -----
#           a
#          aa
#
#         printing results for query 'span_rel(X)':
#            X
#         --------
#          [0, 1)
#          [0, 2)
#          [1, 2)
#         """
#
#     query = """
#     string_rel(X) <- rgx_string("aa",".+") -> (X)
#     span_rel(X) <- rgx_span("aa",".+") -> (X)
#     ?string_rel(X)
#     ?span_rel(X)
#     """
#
#     run_test(query, expected_result)


def test_rust_regex_groups():
    # TODO@niv: @dean, how does the user know what order to expect, regarding the capture groups?
    # @response, when introducing this default ie function, you should tell him with some examples
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

    text = "aab"
    pattern = "(?P<group_all>(?P<group_a>a+)(?P<group_b>b+))"

    query = f"""
        group_string_rel(X,Y,Z) <- rgx_string("{text}","{pattern}") -> (X,Y,Z)
        group_span_rel(X,Y,Z) <- rgx_span("{text}","{pattern}") -> (X,Y,Z)
        ?group_string_rel(X, Y, Z)
        ?group_span_rel(X,Y, Z)
        """

    run_test(query, expected_result)


def test_python_regex():
    expected_result = """printing results for query 'py_string_rel(X)':
              X
            -----
             aa
            
            printing results for query 'py_span_rel(X)':
               X
            --------
             [0, 2)"""

    query = """
        py_string_rel(X) <- py_rgx_string("aa",".+") -> (X)
        py_span_rel(X) <- py_rgx_span("aa",".+") -> (X)
        ?py_string_rel(X)
        ?py_span_rel(X)
        """

    run_test(query, expected_result)
