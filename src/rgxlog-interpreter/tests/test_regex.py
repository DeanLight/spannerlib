from tests.utils import run_test


def test_rust_regex():
    from rgxlog.stdlib.rust_spanner_regex import RGX_STRING
    from rgxlog.stdlib.rust_spanner_regex import RGX
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

    query = """
    string_rel(X) <- rgx_string("aa",".+") -> (X)
    span_rel(X) <- rgx_span("aa",".+") -> (X)
    ?string_rel(X)
    ?span_rel(X)
    """

    run_test(query, expected_result, [RGX, RGX_STRING])
