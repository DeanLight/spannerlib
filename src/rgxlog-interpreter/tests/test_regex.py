from rgxlog.engine.session import Session

from tests.utils import run_query_assert_output


def test_rust_regex():
    from rgxlog.stdlib.rust_spanner_regex import RGX_STRING
    from rgxlog.stdlib.rust_spanner_regex import RGX
    expected_result = """printing results for query 'string_rel(X)':
                          X
                        -----
                         aa
                        
                        printing results for query 'span_rel(X)':
                           X
                        --------
                         [0, 2)
                        """

    query = """
    string_rel(X) <- rust_rgx_string("aa","aa") -> (X)
    span_rel(X) <- rust_rgx_span("aa","aa") -> (X)
    ?string_rel(X)
    ?span_rel(X)
    """
    session = Session()
    session.register(**RGX)
    session.register(**RGX_STRING)
    run_query_assert_output(session, query, expected_result)
