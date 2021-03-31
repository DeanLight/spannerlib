"""
this module contains implementation of regex ie functions using python's 're' module
"""

import re
from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.ie_functions.ie_function_base import IEFunction


def rgx(text, regex_formula):
    """
    Args:
        text: The input text for the regex operation
        regex_formula: the formula of the regex operation

    Returns: tuples of spans that represents the results
    """
    compiled_rgx = re.compile(regex_formula)
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_spans = [match.span()]
        else:
            matched_spans = [match.span(i) for i in range(1, num_groups + 1)]
        yield matched_spans


def rgx_out_type(output_arity):
    return tuple([DataTypes.span] * output_arity)


rgx_in_type = [DataTypes.string, DataTypes.string]


class RGX(IEFunction):
    """
    Performs a regex information extraction.
    Results are tuples of spans
    """

    def __init__(self):
        super().__init__(rgx, rgx_in_type, rgx_out_type, True)


def rgx_string(text, regex_formula):
    """
    Args:
        text: The input text for the regex operation
        regex_formula: the formula of the regex operation

    Returns: tuples of strings that represents the results
    """
    compiled_rgx = re.compile(regex_formula)
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_strings = [match.group()]
        else:
            matched_strings = [group for group in match.groups()]
        yield matched_strings


def rgx_string_out_types(output_arity):
    return tuple([DataTypes.string] * output_arity)


rgx_string_in_type = [DataTypes.string, DataTypes.string]


class RGXString(IEFunction):
    """
    Performs a regex information extraction.
    Results are tuples of strings
    """
    def __init__(self):
        super().__init__(rgx_string, rgx_string_in_type, rgx_string_out_types, True)
