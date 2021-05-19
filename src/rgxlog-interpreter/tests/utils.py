from typing import List, Optional, Iterable

import numpy as np
from pandas import DataFrame

from rgxlog.engine.session import queries_to_string, Session


def is_equal_stripped_sorted_tables(result_text, expected_text):
    result_text = sorted([line.strip() for line in result_text.splitlines() if line.strip()])
    expected_text = sorted([line.strip() for line in expected_text.splitlines() if line.strip()])
    return result_text == expected_text


def is_equal_dataframes_ignore_order(result_df, expected_df):
    result_df_sorted = DataFrame(np.sort(result_df.values, axis=0), index=result_df.index, columns=result_df.columns)
    expected_df_sorted = DataFrame(np.sort(expected_df.values, axis=0), index=expected_df.index,
                                   columns=expected_df.columns)
    return result_df_sorted.equals(expected_df_sorted)


def table_to_query_free_vars_tuples(table: str) -> Iterable:
    tuples = [line.strip() for line in table.split("\n") if len(line.strip()) != 0]
    if tuples[1] in ["[()]", "[]"]:
        return tuples

    else:  # query   |free vars|     tuples
        return tuples[0], tuples[1], set(tuples[3:])


def split_to_tables(result: str) -> List[str]:
    return result.split("\n\n")


def compare_strings(expected: str, output: str) -> bool:
    expected = "\n".join([line.strip() for line in expected.splitlines()])
    output = "\n".join([line.strip() for line in output.splitlines()])

    expected_tables, output_tables = split_to_tables(expected), split_to_tables(output)
    if len(expected_tables) != len(output_tables):
        return False

    for expected_table, output_table in zip(expected_tables, output_tables):
        expected_table = table_to_query_free_vars_tuples(expected_table)
        output_table = table_to_query_free_vars_tuples(output_table)
        if expected_table != output_table:
            return False

    return True


def run_test(query: str, expected_output: Optional[str] = None, functions_to_import: Iterable[dict] = tuple(),
             test_session: Optional[Session] = None) -> Session:
    if test_session is None:
        test_session = Session()

    for ie_function in functions_to_import:
        test_session.register(**ie_function)

    # TODO@niv: i think printing results is more comfy for debugging
    query_result = test_session.run_query(query, print_results=True)

    if expected_output is not None:
        query_result_string = queries_to_string(query_result)
        assert compare_strings(expected_output, query_result_string), "expected string != result string"

    return test_session
