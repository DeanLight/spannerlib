from rgxlog import Session
from rgxlog.engine.datatypes.ast_node_types import Query
from rgxlog.engine.datatypes.primitive_types import DataTypes


def test_rust_regex():
    s = Session()

    expected_result_string = (Query("string_rel", ['X'],
                                    [DataTypes.free_var_name]),
                              [("aa",)])

    expected_result_span = (Query("span_rel", ['X'],
                                  [DataTypes.free_var_name]),
                            [((0, 2),)])

    s.run_query("""string_rel(X) <- rust_rgx_string("aa","aa") -> (X)""")
    query_result_string = s.run_query("""?string_rel(X)""", print_results=True)
    assert expected_result_string == query_result_string

    s.run_query("""span_rel(X) <- rust_rgx_span("aa","aa") -> (X)""")
    query_result_span = s.run_query("""?span_rel(X)""", print_results=True)
    assert expected_result_span == query_result_span
