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
PACKAGE_GIT_URL = "https://github.com/NNRepos/enum-spanner-rs"
PACKAGE_NAME = "enum-spanner-rs"
REGEX_FOLDER_NAME = "enum_spanner"

# installation paths
REGEX_FOLDER_PATH = path.join(path.dirname(__file__), REGEX_FOLDER_NAME)
REGEX_EXE_PATH_POSIX = path.join(REGEX_FOLDER_PATH, "bin", PACKAGE_NAME)
REGEX_EXE_PATH_WIN = path.join(REGEX_FOLDER_PATH, "bin", PACKAGE_NAME + ".exe")
REGEX_TEMP_PATH = path.join(REGEX_FOLDER_PATH, "temp{}.txt")

# commands
RUSTUP_TOOLCHAIN = "1.34"
CARGO_CMD_ARGS = ["cargo", "+" + RUSTUP_TOOLCHAIN, "install", "--root", REGEX_FOLDER_PATH, "--git", PACKAGE_GIT_URL]
RUSTUP_CMD_ARGS = ["rustup", "toolchain", "install", RUSTUP_TOOLCHAIN]
CARGO_TIMEOUT = 180
RUSTUP_TIMEOUT = 180
TIMEOUT_MINUTES = (CARGO_TIMEOUT + RUSTUP_TIMEOUT) // 60

# etc
TIME_FORMAT = "%Y_%m_%d_%H_%M_%S"
WINDOWS_OS = "win32"


def _download_and_install_rust_and_regex():
    # i can't use just "cargo -V" because it starts downloading stuff sometimes
    with Popen(["where", "cargo"], stdout=PIPE, stderr=PIPE) as cargo:
        errcode = cargo.wait(5)

    with Popen(["where", "rustup"], stdout=PIPE, stderr=PIPE) as rustup:
        errcode = errcode or rustup.wait(5)

    if errcode:
        raise IOError(f"cargo or rustup are not installed in $PATH. please install rust: {DOWNLOAD_RUST_URL}")

    logging.info(f"{PACKAGE_NAME} was not found on your system")
    logging.info(f"installing package. this might take up to {TIMEOUT_MINUTES} minutes...")
    with Popen(RUSTUP_CMD_ARGS) as rustup:
        rustup.wait(RUSTUP_TIMEOUT)

    with Popen(CARGO_CMD_ARGS) as cargo:
        cargo.wait(CARGO_TIMEOUT)

    if not _is_installed_package():
        raise Exception("installation failed - check the output")

    logging.info("installation completed")


def _is_installed_package():
    if platform == WINDOWS_OS:
        return path.isfile(REGEX_EXE_PATH_WIN)
    else:
        return path.isfile(REGEX_EXE_PATH_POSIX)


def rgx_span_out_type(output_arity):
    return tuple([DataTypes.span] * output_arity)


def rgx_string_out_type(output_arity):
    return tuple([DataTypes.string] * output_arity)


def _format_spanner_output(output: bytes):
    ret = []
    output_jsons = [x.decode("utf-8").strip(">") for x in output.splitlines() if x]
    for out in output_jsons:
        dict_out = json.loads(out)
        if dict_out["span"][0] > -1:
            ret.append(dict_out)

    return ret


def rgx(text, regex_pattern, out_type):
    if not _is_installed_package():
        _download_and_install_rust_and_regex()

    date_for_temp_file = datetime.now().strftime(TIME_FORMAT)
    temp_file_path = REGEX_TEMP_PATH.format(date_for_temp_file)
    with open(temp_file_path, "w+") as f:
        f.write(text)

    if platform == WINDOWS_OS:
        regex_cross_platform_path = REGEX_EXE_PATH_WIN
    else:
        regex_cross_platform_path = REGEX_EXE_PATH_POSIX

    try:
        rust_regex_args = [regex_cross_platform_path, regex_pattern, temp_file_path, "--compare"]
        regex_output = _format_spanner_output(check_output(rust_regex_args, stderr=PIPE))

        for out in regex_output:
            if out_type == "string":
                yield out["match"]
            elif out_type == "span":
                yield tuple(out["span"])
            else:
                assert False, "illegal out_type"

    finally:
        os.remove(temp_file_path)


def rgx_span(text, regex_pattern):
    """
    Args:
        text: The input text for the regex operation
        regex_pattern: the formula of the regex operation

    Returns: tuples of spans that represents the results
    """
    yield rgx(text, regex_pattern, "span")


RustRGXSpan = dict(ie_function=rgx_span,
                   ie_function_name='rust_rgx_span',
                   in_rel=RUST_RGX_IN_TYPES,
                   out_rel=rgx_span_out_type,
                   )


def rgx_string(text, regex_pattern):
    """
    Args:
        text: The input text for the regex operation
        regex_pattern: the pattern of the regex operation

    Returns: tuples of strings that represents the results
    """
    yield rgx(text, regex_pattern, "string")


RustRGXString = dict(ie_function=rgx_string,
                     ie_function_name='rust_rgx_string',
                     in_rel=RUST_RGX_IN_TYPES,
                     out_rel=rgx_string_out_type)
