from rgxlog.engine.session import Session

from tests.utils import run_query_assert_output, run_test


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
    # session = Session()
    # session.register(**RGX)
    # session.register(**RGX_STRING)
    # run_query_assert_output(session, query, expected_result)
    run_test(query, expected_result, [RGX, RGX_STRING])
