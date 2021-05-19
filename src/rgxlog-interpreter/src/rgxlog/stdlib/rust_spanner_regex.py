"""
this module contains implementation of regex ie functions using the rust package `enum-spanner-rs`
"""
import logging
import os
import re
import tempfile
from os import path
from subprocess import Popen, PIPE, check_output
from sys import platform

from rgxlog.engine.datatypes.primitive_types import DataTypes, Span

# types
RUST_RGX_IN_TYPES = [DataTypes.string, DataTypes.string]

# rust
DOWNLOAD_RUST_URL = "https://rustup.rs/"

# package info
PACKAGE_GIT_URL = "https://github.com/NNRepos/enum-spanner-rs"
PACKAGE_NAME = "enum-spanner-rs"
REGEX_FOLDER_NAME = "enum_spanner"

# installation paths
REGEX_FOLDER_PATH = path.join(path.dirname(__file__), REGEX_FOLDER_NAME)
REGEX_TEMP_PATH = path.join(REGEX_FOLDER_PATH, "temp{}.txt")
REGEX_EXE_PATH_POSIX = path.join(REGEX_FOLDER_PATH, "bin", PACKAGE_NAME)
REGEX_EXE_PATH_WIN = path.join(REGEX_FOLDER_PATH, "bin", PACKAGE_NAME + ".exe")

# commands
RUSTUP_TOOLCHAIN = "1.34"
CARGO_CMD_ARGS = ["cargo", "+" + RUSTUP_TOOLCHAIN, "install", "--root", REGEX_FOLDER_PATH, "--git", PACKAGE_GIT_URL]
RUSTUP_CMD_ARGS = ["rustup", "toolchain", "install", RUSTUP_TOOLCHAIN]
SHORT_TIMEOUT = 10
CARGO_TIMEOUT = 300
RUSTUP_TIMEOUT = 300
TIMEOUT_MINUTES = (CARGO_TIMEOUT + RUSTUP_TIMEOUT) // 60

# os-dependent variables
WINDOWS_OS = "win32"
WHICH_WORD = "where" if platform == WINDOWS_OS else "which"
REGEX_EXE_PATH = REGEX_EXE_PATH_WIN if platform == WINDOWS_OS else REGEX_EXE_PATH_POSIX

# patterns - taken from https://stackoverflow.com/questions/5452655/
ESCAPED_STRINGS_PATTERN = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"', re.DOTALL)
SPAN_PATTERN = re.compile(r"(?P<start>\d+), ?(?P<end>\d+)")

# etc
TEMP_FILE_NAME = "temp"


def _download_and_install_rust_and_regex():
    # i can't use just "cargo -V" because it starts downloading stuff sometimes
    with Popen([WHICH_WORD, "cargo"], stdout=PIPE, stderr=PIPE) as cargo:
        errcode = cargo.wait(SHORT_TIMEOUT)

    with Popen([WHICH_WORD, "rustup"], stdout=PIPE, stderr=PIPE) as rustup:
        errcode = errcode or rustup.wait(SHORT_TIMEOUT)

    if errcode:
        raise IOError(f"cargo or rustup are not installed in $PATH. please install rust: {DOWNLOAD_RUST_URL}")

    logging.info(f"{PACKAGE_NAME} was not found on your system")
    logging.info(f"installing package. this might take up to {TIMEOUT_MINUTES} minutes...")

    # i didn't pipe here because i want the user to see the output
    with Popen(RUSTUP_CMD_ARGS) as rustup:
        rustup.wait(RUSTUP_TIMEOUT)

    with Popen(CARGO_CMD_ARGS) as cargo:
        cargo.wait(CARGO_TIMEOUT)

    if not _is_installed_package():
        raise Exception("installation failed - check the output")

    logging.info("installation completed")


def _is_installed_package():
    return path.isfile(REGEX_EXE_PATH)


def rgx_span_out_type(output_arity):
    return tuple([DataTypes.span] * output_arity)


def rgx_string_out_type(output_arity):
    return tuple([DataTypes.string] * output_arity)


def _format_spanner_string_output(output: bytes):
    output_lists = []
    output_lines = [x.decode("utf-8") for x in output.splitlines() if x]
    for out in output_lines:
        out_list = []
        matches = ESCAPED_STRINGS_PATTERN.findall(out)
        for match in matches:
            # the pattern leaves the backslashes
            escaped_match = re.sub(r'\\"', '"', match)
            out_list.append(escaped_match)
        output_lists.append(out_list)

    return output_lists


def _format_spanner_span_output(output: bytes):
    output_lists = []
    output_lines = [x.decode("utf-8") for x in output.splitlines() if x]
    for out in output_lines:
        out_list = []
        matches = SPAN_PATTERN.finditer(out)
        for match in matches:
            start, end = int(match.group("start")), int(match.group("end"))
            out_list.append(Span(start, end))
        output_lists.append(out_list)

    return output_lists


def rgx(text, regex_pattern, out_type):
    if not _is_installed_package():
        _download_and_install_rust_and_regex()

    with tempfile.TemporaryDirectory() as temp_dir:
        rgx_temp_file_name = os.path.join(temp_dir, TEMP_FILE_NAME)
        with open(rgx_temp_file_name, "w+") as f:
            f.write(text)

        if out_type == "string":
            rust_regex_args = [REGEX_EXE_PATH, regex_pattern, rgx_temp_file_name]
            regex_output = _format_spanner_string_output(check_output(rust_regex_args, stderr=PIPE))

            for out in regex_output:
                yield out

        elif out_type == "span":
            rust_regex_args = [REGEX_EXE_PATH, regex_pattern, rgx_temp_file_name, "--bytes-offset"]
            regex_output = _format_spanner_span_output(check_output(rust_regex_args, stderr=PIPE))

            for out in regex_output:
                yield out

        else:
            assert False, "illegal out_type"


def rgx_span(text, regex_pattern):
    """
    Args:
        text: The input text for the regex operation
        regex_pattern: the pattern of the regex operation

    Returns: tuples of spans that represents the results
    """
    return rgx(text, regex_pattern, "span")


RGX = dict(ie_function=rgx_span,
           ie_function_name='rgx_span',
           in_rel=RUST_RGX_IN_TYPES,
           out_rel=rgx_span_out_type)


def rgx_string(text, regex_pattern):
    """
    Args:
        text: The input text for the regex operation
        regex_pattern: the pattern of the regex operation

    Returns: tuples of strings that represents the results
    """
    return rgx(text, regex_pattern, "string")


RGX_STRING = dict(ie_function=rgx_string,
                  ie_function_name='rgx_string',
                  in_rel=RUST_RGX_IN_TYPES,
                  out_rel=rgx_string_out_type)
