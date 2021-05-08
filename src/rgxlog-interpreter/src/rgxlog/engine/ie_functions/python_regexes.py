"""
this module contains implementation of regex ie functions using python's 're' module
"""

import re

from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.ie_functions.ie_function_base import IEFunction

PYTHON_RGX_IN_TYPES = [DataTypes.string, DataTypes.string]


def rgx_span_out_type(output_arity):
    return tuple([DataTypes.span] * output_arity)


def rgx_string_out_type(output_arity):
    return tuple([DataTypes.string] * output_arity)


def rgx_span(text, regex_pattern):
    """
    Args:
        text: The input text for the regex operation
        regex_pattern: the formula of the regex operation

    Returns: tuples of spans that represents the results
    """
    compiled_rgx = re.compile(regex_pattern)
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_spans = [match.span()]
        else:
            matched_spans = [match.span(i) for i in range(1, num_groups + 1)]
        yield matched_spans


def rgx_string(text, regex_pattern):
    """
    Args:
        text: The input text for the regex operation
        regex_pattern: the pattern of the regex operation

    Returns: tuples of strings that represents the results
    """
    compiled_rgx = re.compile(regex_pattern)
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_strings = [match.group()]
        else:
            matched_strings = [group for group in match.groups()]
        yield matched_strings


class PyRGXSpan(IEFunction):
    """
    Performs a regex information extraction.
    Results are tuples of spans
    """

    def __init__(self):
        super().__init__(rgx_span, PYTHON_RGX_IN_TYPES, rgx_span_out_type)


class PyRGXString(IEFunction):
    """
    Performs a regex information extraction.
    Results are tuples of strings
    """

    def __init__(self):
        super().__init__(rgx_string, PYTHON_RGX_IN_TYPES, rgx_string_out_type)
