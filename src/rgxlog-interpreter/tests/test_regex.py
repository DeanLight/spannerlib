import tempfile
from pathlib import Path

from rgxlog.engine.utils.general_utils import QUERY_RESULT_PREFIX
from tests.utils import run_test


def test_rust_regex() -> None:
    commands = """
        string_rel(X) <- rgx_string("aa",".+") -> (X)
        span_rel(X) <- rgx_span("aa",".+") -> (X)
        ?string_rel(X)
        ?span_rel(X)
        """

    expected_result = f"""{QUERY_RESULT_PREFIX}'string_rel(X)':
          X
        -----
          a
         aa

        {QUERY_RESULT_PREFIX}'span_rel(X)':
           X
        --------
         [0, 1)
         [0, 2)
         [1, 2)
        """

    run_test(commands, expected_result)


def test_rust_regex_from_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        rgx_text_file = Path(temp_dir) / "temp"
        with open(rgx_text_file, "w") as f:
            f.write("aa")

        commands = f"""
            string_rel(X) <- rgx_string_from_file("{rgx_text_file}",".+") -> (X)
            span_rel(X) <- rgx_span_from_file("{rgx_text_file}",".+") -> (X)
            ?string_rel(X)
            ?span_rel(X)
            """

        expected_result = f"""{QUERY_RESULT_PREFIX}'string_rel(X)':
              X
            -----
              a
             aa

            {QUERY_RESULT_PREFIX}'span_rel(X)':
               X
            --------
             [0, 1)
             [0, 2)
             [1, 2)
            """

        run_test(commands, expected_result)


def test_rust_regex_groups() -> None:
    text = "aab"
    pattern = "(?P<group_all>(?P<group_a>a+)(?P<group_b>b+))"

    commands = f"""
            group_string_rel(X,Y,Z) <- rgx_string("{text}","{pattern}") -> (X,Y,Z)
            ?group_string_rel(X, Y, Z)
            """

    expected_result = f"""{QUERY_RESULT_PREFIX}'group_string_rel(X, Y, Z)':
          X  |  Y  |  Z
        -----+-----+-----
         aa  |  b  | aab
          a  |  b  | ab"""

    run_test(commands, expected_result)


def test_python_regex() -> None:
    commands = """
           py_string_rel(X) <- py_rgx_string("aa",".+") -> (X)
           py_span_rel(X) <- py_rgx_span("aa",".+") -> (X)
           ?py_string_rel(X)
           ?py_span_rel(X)
           """

    expected_result = f"""{QUERY_RESULT_PREFIX}'py_string_rel(X)':
              X
            -----
             aa

            {QUERY_RESULT_PREFIX}'py_span_rel(X)':
               X
            --------
             [0, 2)"""

    run_test(commands, expected_result)
