from rgxlog.rgxlog_client import Client

EXPECTED_RESULT_INTRO = """printing results for query 'uncle(X, Y)':
  X  |  Y
-----+------
 bob | greg
"""


# TODO add tests
def test_introduction():
    client = Client()
    client.execute("new uncle(str, str)")
    client.execute('uncle("bob", "greg")')
    query_result = client.execute("?uncle(X,Y)")
    assert query_result == EXPECTED_RESULT_INTRO, "output string changed"
