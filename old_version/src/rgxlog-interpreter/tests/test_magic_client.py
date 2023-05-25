from rgxlog.engine.utils.general_utils import QUERY_RESULT_PREFIX
from tests.utils import run_test


def test_magic_session_basic() -> None:
    commands = """
        new uncle(str, str)
        uncle("bob", "greg")
        ?uncle(X,Y)
        """

    expected_result_intro = f"""{QUERY_RESULT_PREFIX}'uncle(X, Y)':
              X  |  Y
            -----+------
             bob | greg
            """

    run_test(commands, expected_result_intro)
