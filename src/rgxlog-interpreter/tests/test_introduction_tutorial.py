from rgxlog.engine.session import Session

EXPECTED_RESULT_INTRO = """printing results for query 'uncle(X, Y)':
  X  |  Y
-----+------
 bob | greg
"""


# TODO add tests
def test_introduction():
    session = Session()
    session.run_query("new uncle(str, str)")
    session.run_query('uncle("bob", "greg")')
    query_result = session.execute("?uncle(X,Y)")