from rgxlog.engine.datatypes.ast_node_types import Query
from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.session import Session


# TODO add tests
def test_introduction():
    # note - there's 2 ways to compare test output - using actual objects (like this), or using strings (easier)
    # TODO: since relations aren't sorted yet, we have to use the strings for outputs > 1
    expected_result = (Query("uncle", ['X', 'Y'],
                             [DataTypes.free_var_name, DataTypes.free_var_name]),
                       [('bob', 'greg')])

    session = Session()
    session.run_query("new uncle(str, str)")
    session.run_query('uncle("bob", "greg")')
    query_result = session.run_query("?uncle(X,Y)", print_results=False)
    assert query_result[0] == expected_result
