import pytest
from rgxlog.engine.execution import SqliteEngine, RelationDeclaration, DataTypes, AddFact, Query


@pytest.mark.engine
def test_add_fact_twice():
    expected_output = [(8, "hihi")]

    my_engine = SqliteEngine(debug=False)

    # add relation
    my_relation = RelationDeclaration("yoyo", [DataTypes.integer, DataTypes.string])
    my_engine.declare_relation(my_relation)

    # add fact
    my_fact = AddFact("yoyo", [8, "hihi"], [DataTypes.integer, DataTypes.string])
    my_engine.add_fact(my_fact)
    my_engine.add_fact(my_fact)

    my_query = Query("yoyo", ["X", "Y"], [DataTypes.free_var_name, DataTypes.free_var_name])

    my_result = my_engine.query(my_query)
    assert expected_output==my_result
