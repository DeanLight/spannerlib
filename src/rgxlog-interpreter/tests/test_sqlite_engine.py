import pytest

from rgxlog.engine.datatypes.ast_node_types import RelationDeclaration, AddFact, Query
from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.engine import SqliteEngine


@pytest.mark.engine
def test_add_fact_twice() -> None:
    expected_output = [(8, "hihi")]

    my_engine = SqliteEngine()

    # add relation
    my_relation = RelationDeclaration("yoyo", [DataTypes.integer, DataTypes.string])
    my_engine.declare_relation_table(my_relation)

    # add fact
    my_fact = AddFact("yoyo", [8, "hihi"], [DataTypes.integer, DataTypes.string])
    my_engine.add_fact(my_fact)
    my_engine.add_fact(my_fact)

    my_query = Query("yoyo", ["X", "Y"], [DataTypes.free_var_name, DataTypes.free_var_name])

    my_result = my_engine.query(my_query)
    assert expected_output == my_result
