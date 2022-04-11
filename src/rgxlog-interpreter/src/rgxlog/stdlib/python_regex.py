import re
from typing import Iterable, Sequence

from rgxlog.engine.datatypes.primitive_types import DataTypes


def py_rgx_string(text: str, regex_pattern: str) -> Iterable[Sequence]:
    """
    An IE function which runs regex using python's `re` and yields tuples of strings.

    @param text: The input text for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of strings that represents the results.
    """
    compiled_rgx = re.compile(regex_pattern)
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_strings = [match.group()]
        else:
            matched_strings = [group for group in match.groups()]
        yield matched_strings


def py_rgx_string_out_types(output_arity: int) -> Sequence:
    return tuple([DataTypes.string] * output_arity)


PYRGX_STRING = dict(ie_function=py_rgx_string,
                    ie_function_name='py_rgx_string',
                    in_rel=[DataTypes.string, DataTypes.string],
                    out_rel=py_rgx_string_out_types)


def py_rgx(text: str, regex_pattern: str) -> Iterable[Sequence]:
    """
    An IE function which runs regex using python's `re` and yields tuples of spans.

    @param text: The input text for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of spans that represents the results.
    """
    compiled_rgx = re.compile(regex_pattern)
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_spans = [match.span()]
        else:
            matched_spans = [match.span(i) for i in range(1, num_groups + 1)]
        yield matched_spans


def py_rgx_out_type(output_arity: int) -> Sequence:
    return tuple([DataTypes.span] * output_arity)


PYRGX = dict(ie_function=py_rgx,
             ie_function_name='py_rgx_span',
             in_rel=[DataTypes.string, DataTypes.string],
             out_rel=py_rgx_out_type)
