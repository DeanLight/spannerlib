"""
this module contains implementation of regex ie functions using the rust package `enum-spanner-rs`
"""
import json
import logging
import os
from datetime import datetime
from os import path
from subprocess import Popen, PIPE, check_output
from sys import platform

from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.ie_functions.ie_function_base import IEFunction

# types
RUST_RGX_IN_TYPES = [DataTypes.string, DataTypes.string]

# rust
DOWNLOAD_RUST_URL = "https://rustup.rs/"

# package info
PACKAGE_GIT_URL = "https://github.com/PoDMR/enum-spanner-rs/"
PACKAGE_NAME = "enum-spanner-rs"
REGEX_FOLDER_NAME = "enum_spanner"
REGEX_FOLDER_PATH = path.join(path.dirname(__file__), REGEX_FOLDER_NAME)
REGEX_EXE_PATH = path.join(REGEX_FOLDER_PATH, "bin", PACKAGE_NAME)
REGEX_TEMP_PATH = path.join(REGEX_FOLDER_PATH, "temp{}.txt")
CARGO_CMD_ARGS = ["cargo", "install", "--root", REGEX_FOLDER_PATH, "--git", PACKAGE_GIT_URL]

# etc
TIME_FORMAT = "%Y_%m_%d_%H_%M_%S"
WINDOWS_OS = "win32"


def _download_and_install_rust_and_regex():
    with Popen(["cargo"], stdout=PIPE, stderr=PIPE) as cargo:
        errcode = cargo.wait(5)

    if errcode:
        raise IOError(f"cargo was not installed. please install rust: {DOWNLOAD_RUST_URL}")

    logging.info(f"{PACKAGE_NAME} was not found on your system")
    logging.info("installing package. this might take a couple minutes...")
    with Popen(CARGO_CMD_ARGS, stdout=PIPE) as cargo:
        line = True
        while line:
            line = cargo.stdout.readline()
            print(line.strip())

    if not _is_installed_package():
        raise Exception("installation failed")

    logging.info("installation completed")


def _is_installed_package():
    return path.isfile(REGEX_EXE_PATH)


def rgx_span_out_type(output_arity):
    return tuple([DataTypes.span] * output_arity)


def rgx_string_out_type(output_arity):
    return tuple([DataTypes.string] * output_arity)


def _format_spanner_output(output: bytes):
    ret = []
    output_jsons = [x.decode("utf-8").strip(">") for x in output.splitlines() if x]
    for out in output_jsons:
        dict_out = json.loads(out)
        ret.append(dict_out)

    return ret

def rgx(text, regex_pattern, out_type):
    if platform == WINDOWS_OS:
        raise Exception("not supported on windows")

    if not _is_installed_package():
        _download_and_install_rust_and_regex()

    date_for_temp_file = datetime.now().strftime(TIME_FORMAT)
    temp_file_path = REGEX_TEMP_PATH.format(date_for_temp_file)
    with open(temp_file_path, "w+") as f:
        f.write(text)

    try:
        rust_regex_args = [REGEX_EXE_PATH, regex_pattern, temp_file_path, "--compare"]
        regex_output = _format_spanner_output(check_output(rust_regex_args))
        if out_type == "string":
            print([x["match"] for x in regex_output])
            yield [x["match"] for x in regex_output]
        else:
            yield [x["span"] for x in regex_output]

    finally:
        os.remove(temp_file_path)


def rgx_span(text, regex_pattern):
    """
    Args:
        text: The input text for the regex operation
        regex_pattern: the formula of the regex operation

    Returns: tuples of spans that represents the results
    """
    rgx(text,regex_pattern, "span")


def rgx_string(text, regex_pattern):
    """
    Args:
        text: The input text for the regex operation
        regex_pattern: the pattern of the regex operation

    Returns: tuples of strings that represents the results
    """
    rgx(text, regex_pattern, "string")


class RustRGXSpan(IEFunction):
    """
    Performs a regex information extraction.
    Results are tuples of spans
    """

    def __init__(self):
        super().__init__(rgx_span, RUST_RGX_IN_TYPES, rgx_span_out_type)


class RustRGXString(IEFunction):
    """
    Performs a regex information extraction.
    Results are tuples of strings
    """

    def __init__(self):
        super().__init__(rgx_string, RUST_RGX_IN_TYPES, rgx_string_out_type)
