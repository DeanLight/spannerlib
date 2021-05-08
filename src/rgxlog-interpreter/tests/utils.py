from typing import List, Optional, Iterable

from rgxlog.engine.session import query_to_string, Session


def table_to_query_free_vars_tuples(table: str) -> Iterable:
    tuples = [line.strip() for line in table.split("\n")]
    if tuples[1] in ["[()]", "[]"]:
        return tuples

    else:  # query    |free vars| tuples
        return tuples[0], tuples[1], set(tuples[3:])


def compare_strings(expected: str, output: str) -> bool:
    def split_to_tables(result: str) -> List[str]:
        return result.split("\n\n")

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
             _session: Optional[Session] = None) -> Session:
    if _session is None:
        session = Session()
    else:
        session = _session
    for ie_function in functions_to_import:
        session.register(**ie_function)

    query_result = session.run_query(query, print_results=False)

    if expected_output is not None:
        query_result_string = query_to_string(query_result)
        assert compare_strings(expected_output, query_result_string), "fail"

    return session
