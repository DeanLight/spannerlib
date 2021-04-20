"""
this module contains implementation of regex ie functions using the rust package `enum-spanner-rs`
"""
import logging
import re

from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.ie_functions.ie_function_base import IEFunction
from os import path

RUST_RGX_IN_TYPES = [DataTypes.string, DataTypes.string]

PACKAGE_NAME = "enum-spanner-rs"


def _download_and_install_regex_package():
    logging.info(f"{PACKAGE_NAME} was not found on your system. downloading...")


def _is_installed_package():
    return path.isdir()

def rgx_out_type(output_arity):
    return tuple([DataTypes.span] * output_arity)


def rgx_span(text, regex_pattern):
    """
    Args:
        text: The input text for the regex operation
        regex_pattern: the formula of the regex operation

    Returns: tuples of spans that represents the results
    """
    if not _is_installed_package():
        _download_and_install_regex_package()

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
    if not _is_installed_package():
        _download_and_install_regex_package()

    compiled_rgx = re.compile(regex_pattern)
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_strings = [match.group()]
        else:
            matched_strings = [group for group in match.groups()]
        yield matched_strings


class RustRGXSpan(IEFunction):
    """
    Performs a regex information extraction.
    Results are tuples of spans
    """

    def __init__(self):
        super().__init__(rgx_span, RUST_RGX_IN_TYPES, rgx_out_type)


class RustRGXString(IEFunction):
    """
    Performs a regex information extraction.
    Results are tuples of strings
    """

    def __init__(self):
        super().__init__(rgx_string, RUST_RGX_IN_TYPES, rgx_out_type)
