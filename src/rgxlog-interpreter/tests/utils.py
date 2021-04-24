from typing import Tuple, List

def compare_relations(actual: list, output: list) -> bool:
    if len(actual) != len(output):
        return False
    for rel in actual:
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


def compare_strings(actual: str, test_output: str) -> bool:
    actual_lines = [line.strip() for line in actual.splitlines(True) if line.strip()]
    output_lines = [line.strip() for line in test_output.splitlines(True) if line.strip()]
    if len(actual_lines) != len(output_lines):
        return False
    i = 0
    while i < len(actual_lines):
        rng = 3
        if actual_lines[i + 1] in ["[()]\n", "[]\n"]:
            rng = 2
        for j in range(rng):
            if actual_lines[i + j] != output_lines[i + j]:
                return False
        i += rng
        actual_rel, offset = str_relation_to_list(actual_lines, i)
        output_rel, _ = str_relation_to_list(output_lines, i)
        if not compare_relations(actual_rel, output_rel):
            return False
        i += offset

    return True



