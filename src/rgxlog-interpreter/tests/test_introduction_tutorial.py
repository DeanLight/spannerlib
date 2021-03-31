from ..src.rgxlog.rgxlog_client import Client


def test_introduction():
    client = Client()
    client.execute("new uncle(str, str)")
    client.execute('uncle("bob", "greg")')
    client.execute("?uncle(X,Y)")
