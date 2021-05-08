from typing import Tuple, List, Optional, Set, Iterable

from rgxlog.engine.session import query_to_string, Session


# def compare_relations(actual: list, output: list) -> bool:
#     if len(actual) != len(output):
#         return False
#     for rel in actual:
#         # TODO@niv: what if a line is printed twice? shouldn't happen but we shouldn't ignore that imo
#         ''''line can't be printed twice... check this code:
#             session = Session()
#             query = """
#                 new a(str)
#                 a("a")
#                 a("a")
#                 ?a(A)
#                 """
#             session.run_query(query)
#         '''
#         if output.count(rel) == 0:
#             return False
#
#     return True
#
#
# def str_relation_to_list(table: List[str], start: int) -> Tuple[list, int]:
#     offset_cnt = 0
#     relations = list()
#     for rel in table[start:]:
#         offset_cnt += 1
#         relations.append(rel)
#         if rel == "\n":
#             break
#
#     return relations, offset_cnt
#
#
# def compare_strings(expected: str, output: str) -> bool:
#     expected_lines = [line.strip() for line in expected.splitlines(True) if line.strip()]
#     output_lines = [line.strip() for line in output.splitlines(True) if line.strip()]
#     if len(expected_lines) != len(output_lines):
#         return False
#
#     curr_line = 0
#     while curr_line < len(expected_lines):
#         """
#             There are two formats of table printing:
#             1. for empty table we print the query and then [] or [()].
#             2. otherwise, we print the query, the free vairables inside the query, and finally the tuples.
#
#             curr_ranges stores the offset from the the line the query is printed to the line in which the first tuple is
#             printed. Therefore, if we are in case 1, the offset should be 3 otherwise it should be 2.
#         """
#         curr_range = 3
#
#         if expected_lines[curr_line + 1] in ["[()]\n", "[]\n"]:
#             curr_range = 2
#         for j in range(curr_range):
#             # check that everything until the first tuple is the same
#             if expected_lines[curr_line + j] != output_lines[curr_line + j]:
#                 return False
#         curr_line += curr_range
#         actual_rel, offset = str_relation_to_list(expected_lines, curr_line)
#         output_rel, _ = str_relation_to_list(output_lines, curr_line)
#         if not compare_relations(actual_rel, output_rel):
#             return False
#         curr_line += offset
#
#     return True


def table_to_query_free_vars_tuples(table: str) -> Iterable:
    tuples = [line.strip() for line in table.split("\n")]
    if tuples[1] in ["[()]", "[]"]:
        return tuples

    else:     # query    |free vars| tuples
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


def run_query_assert_output(session: Session, query: str, expected_out: str, pre_query: Optional[str] = None, ):
    if pre_query:
        session.run_query(pre_query, print_results=False)
    query_result = session.run_query(query, print_results=False)
    query_result_string = query_to_string(query_result)
    assert compare_strings(query_result_string, expected_out)


def run_test(query: str, expected_output: Optional[str] = None, functions_to_import: List[dict] = [],
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