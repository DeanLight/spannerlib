from rgxlog.engine.session import Session, query_to_string
from tests.utils import compare_strings


def test_rust_regex():
    from rgxlog.stdlib.rust_spanner_regex import RustRGXString
    from rgxlog.stdlib.rust_spanner_regex import RustRGXSpan
    EXPECTED_RESULT = """printing results for query 'string_rel(X)':
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

    session.register(**RustRGXSpan)
    session.register(**RustRGXString)
    query_result = session.run_query(query, print_results=False)
    query_result_string = query_to_string(query_result)
    assert compare_strings(EXPECTED_RESULT, query_result_string), "fail"

