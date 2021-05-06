from typing import Tuple, List, Optional

from rgxlog.engine.session import query_to_string, Session


def compare_relations(actual: list, output: list) -> bool:
    if len(actual) != len(output):
        return False
    for rel in actual:
        # TODO@niv: what if a line is printed twice? shouldn't happen but we shouldn't ignore that imo
        if output.count(rel) == 0:
            return False

    return True


def str_relation_to_list(table: List[str], start: int) -> Tuple[list, int]:
    offset_cnt = 0
    relations = list()
    for rel in table[start:]:
        offset_cnt += 1
        relations.append(rel)
        if rel == "\n":
            break

    return relations, offset_cnt


def compare_strings(expected: str, output: str) -> bool:
    expected_lines = [line.strip() for line in expected.splitlines(True) if line.strip()]
    output_lines = [line.strip() for line in output.splitlines(True) if line.strip()]
    if len(expected_lines) != len(output_lines):
        return False

    curr_line = 0
    while curr_line < len(expected_lines):
        curr_range = 3
        # TODO@niv: tom, can you add some comments explaining what this does?
        if expected_lines[curr_line + 1] in ["[()]\n", "[]\n"]:
            curr_range = 2
        for j in range(curr_range):
            if expected_lines[curr_line + j] != output_lines[curr_line + j]:
                return False
        curr_line += curr_range
        actual_rel, offset = str_relation_to_list(expected_lines, curr_line)
        output_rel, _ = str_relation_to_list(output_lines, curr_line)
        if not compare_relations(actual_rel, output_rel):
            return False
        curr_line += offset

    return True


def run_query_assert_output(session: Session, query: str, expected_out: str, pre_query: Optional[str] = None):
    if pre_query:
        session.run_query(pre_query, print_results=False)
    query_result = session.run_query(query, print_results=False)
    query_result_string = query_to_string(query_result)
    assert compare_strings(query_result_string, expected_out)
