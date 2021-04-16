from rgxlog.engine.datatypes.ast_node_types import Query
from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.session import Session


# TODO add tests
def test_introduction():
    expected_result = (Query("uncle", ['X', 'Y'],
                             [DataTypes.free_var_name, DataTypes.free_var_name]),
                       [('bob', 'greg')])

    session = Session()
    session.run_query("new uncle(str, str)")
    session.run_query('uncle("bob", "greg")')
    query_result = session.run_query("?uncle(X,Y)", print_results=False)
    assert query_result == expected_result
