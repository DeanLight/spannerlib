import numpy as np
import tempfile
from pandas import DataFrame
from pathlib import Path
from typing import List, Optional, Iterable, Dict, no_type_check, Type

from rgxlog.engine.passes.lark_passes import GenericPass
from rgxlog.engine.session import queries_to_string, Session

TEMP_FILE_NAME = "temp"


def is_equal_stripped_sorted_tables(result_text: str, expected_text: str) -> bool:
    """
    Compares all lines in between two strings, ignoring the order of the lines.

    @param result_text: first string to compare, usually the output of a test.
    @param expected_text: second string to compare, usually the expected output of a test.
    @return: True if equal, else False.
    """
    sorted_result_text = sorted([line.strip() for line in result_text.splitlines() if line.strip()])
    sorted_expected_text = sorted([line.strip() for line in expected_text.splitlines() if line.strip()])
    return sorted_result_text == sorted_expected_text


def is_equal_dataframes_ignore_order(result_df: DataFrame, expected_df: DataFrame) -> bool:
    """
    Similarly to `is_equal_stripped_sorted_tables`, compares two dataframes while ignoring the order of the rows.

    @param result_df: first dataframe to compare.
    @param expected_df: second dataframe to compare.
    @return: True if equal, else False.
    """
    result_df_sorted = DataFrame(np.sort(result_df.values, axis=0), index=result_df.index, columns=result_df.columns)
    expected_df_sorted = DataFrame(np.sort(expected_df.values, axis=0), index=expected_df.index,
                                   columns=expected_df.columns)
    return result_df_sorted.equals(expected_df_sorted)


def table_to_query_free_vars_tuples(table: str) -> Iterable:
    """
    Parses the string table into a nicer format.

    @param table: the string that represents a table.
    @return: the clean format (see comments above return statements).
    """
    # split string into lines and ignore white spaces.
    # tuple[0] is always the print statement.
    tuples = [line.strip() for line in table.split("\n") if len(line.strip()) != 0]
    if len(tuples) < 2:
        raise ValueError("illegal output received: \n\"" + '\n'.join(tuples) + '"')
    # if table is empty (which means it contains one value of true/false) we return tuple.
    # tuple[0] is the print statement, tuple[1] is true/false.
    if tuples[1] in ["[()]", "[]"]:
        return tuples
    # if table is not empty, then: tuple[0] is the print statement, tuple[1] are the free vars and tuple[3:] contains
    # all the tuples inside the table .
    else:  # query   |free vars|     tuples
        return tuples[0], tuples[1], set(tuples[3:])


def split_to_tables(result: str) -> List[str]:
    """
    @param result: rgxlog's output.
    @return: List of strings, each string represents a table.
    """

    # in rgxlog's output, all tables are separated by two consecutive \n.
    return result.split("\n\n")


def compare_strings(expected: str, output: str) -> bool:
    """
    @param expected: expected output.
    @param output: actual output.
    @return: True if output and expected represent the same result, False otherwise.
    """
    expected = "\n".join([line.strip() for line in expected.splitlines()])
    output = "\n".join([line.strip() for line in output.splitlines()])

    expected_tables, output_tables = split_to_tables(expected), split_to_tables(output)
    # if there are different number of tables than false
    if len(expected_tables) != len(output_tables):
        return False

    # check that all the tables are equal
    for expected_table, output_table in zip(expected_tables, output_tables):
        if table_to_query_free_vars_tuples(expected_table) != table_to_query_free_vars_tuples(output_table):
            return False

    return True


@no_type_check
def run_test(commands: str, expected_output: Optional[str] = None, functions_to_import: Iterable[Dict] = (),
             session: Optional[Session] = None) -> Session:
    """
    A function that executes a test.

    @param commands: the commands to run.
    @param expected_output: the expected output of the commands. if it has value of None, than we won't check the output.
    @param functions_to_import: an iterable of functions we want to import to the session.
    @param session: the session in which we run the commands.
    @return: the session it created or got as an argument.
    """
    # if session wasn't passed as an arg than we create it
    if session is None:
        session = Session()

    # import all ie functions
    for ie_function in functions_to_import:
        session.register(**ie_function)

    commands_result = session.run_commands(commands, print_results=True)

    if expected_output is not None:
        commands_result_string = queries_to_string(commands_result)
        assert compare_strings(expected_output, commands_result_string), "expected string != result string"

    return session


def get_session_with_optimizations(parse_graph_optimization_passes: Iterable[Type[GenericPass]] = (),
                                   term_graph_optimization_passes: Iterable[Type[GenericPass]] = ()) -> Session:
    """
    Creates a session and adds optimization passes to the pass stack.
    @param parse_graph_optimization_passes: optimization passes that will be added before AddRulesToComputationTermGraph pass.
    @param term_graph_optimization_passes: optimization passes that will be added after AddRulesToComputationTermGraph pass
    @return: the session.
    """
    session = Session()
    pass_stack = session.get_pass_stack()
    term_graph_pass = pass_stack.pop()

    pass_stack.extend(parse_graph_optimization_passes)
    pass_stack.append(term_graph_pass)
    pass_stack.extend(term_graph_optimization_passes)

    session.set_pass_stack(pass_stack)
    return session


def run_commands_into_csv_test(expected_longrel: str, im_ex_session: Session, commands: str, query_for_csv: str) -> None:
    im_ex_session.run_commands(commands, print_results=False)
    # query into csv and compare with old file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_csv = Path(temp_dir) / TEMP_FILE_NAME
        im_ex_session.send_commands_result_into_csv(query_for_csv, temp_csv)
        assert Path(temp_csv).is_file(), "file was not created"

        with open(temp_csv) as f_temp:
            assert is_equal_stripped_sorted_tables(f_temp.read(), expected_longrel), "file was not written properly"
