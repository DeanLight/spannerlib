import re
from rgxlog.engine.datatypes.primitive_types import DataTypes


def py_rgx_string(text, regex_formula):
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


def py_rgx_string_out_types(output_arity):
    return tuple([DataTypes.string] * output_arity)


PYRGX_STRING = dict(ie_function=py_rgx_string,
                    ie_function_name='RGXString',
                    in_rel=[DataTypes.string, DataTypes.string],
                    out_rel=py_rgx_string_out_types)


def py_rgx(text, regex_formula):
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


def py_rgx_out_type(output_arity):
    return tuple([DataTypes.span] * output_arity)


PYRGX = dict(ie_function=py_rgx,
             ie_function_name='RGX',
             in_rel=[DataTypes.string, DataTypes.string],
             out_rel=py_rgx_out_type)
