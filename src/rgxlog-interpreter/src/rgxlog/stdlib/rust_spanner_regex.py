"""
this module contains implementation of regex ie functions using the rust package `enum-spanner-rs`
"""
import logging
import re
import tempfile
from pathlib import Path
from subprocess import Popen, PIPE
from sys import platform
from typing import Iterable

from rgxlog.engine.datatypes.primitive_types import DataTypes, Span
from rgxlog.stdlib.utils import run_command

# types
RUST_RGX_IN_TYPES = [DataTypes.string, DataTypes.string]

# rust
DOWNLOAD_RUST_URL = "https://rustup.rs/"

# package info - @niv: i use my fork here because it's more stable than the original
PACKAGE_GIT_URL = "https://github.com/NNRepos/enum-spanner-rs"
PACKAGE_NAME = "enum-spanner-rs"
PACKAGE_WIN_FILENAME = PACKAGE_NAME + ".exe"
REGEX_FOLDER_NAME = "enum_spanner_regex"

# installation paths
REGEX_FOLDER_PATH = Path(__file__).parent / REGEX_FOLDER_NAME
REGEX_TEMP_PATH = Path(REGEX_FOLDER_PATH) / "temp{}.txt"
REGEX_EXE_PATH_POSIX = Path(REGEX_FOLDER_PATH) / "bin" / PACKAGE_NAME
REGEX_EXE_PATH_WIN = Path(REGEX_FOLDER_PATH) / "bin" / PACKAGE_WIN_FILENAME

# commands
RUSTUP_TOOLCHAIN = "1.34"
CARGO_CMD_ARGS = ["cargo", "+" + RUSTUP_TOOLCHAIN, "install", "--root", REGEX_FOLDER_PATH, "--git", PACKAGE_GIT_URL]
RUSTUP_CMD_ARGS = ["rustup", "toolchain", "install", RUSTUP_TOOLCHAIN]
SHORT_TIMEOUT = 3
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
    # don't use "cargo -V" because it starts downloading stuff sometimes
    with Popen([WHICH_WORD, "cargo"], stdout=PIPE, stderr=PIPE) as cargo:
        errcode = cargo.wait(SHORT_TIMEOUT)

    with Popen([WHICH_WORD, "rustup"], stdout=PIPE, stderr=PIPE) as rustup:
        errcode = errcode or rustup.wait(SHORT_TIMEOUT)

    if errcode:
        raise IOError(f"cargo or rustup are not installed in $PATH. please install rust: {DOWNLOAD_RUST_URL}")

    # @dean: why do you have a print here?
    #  the installation messages should be warnings too since they are not standard control flow and cause unexpected delay for the user
    #  additionally, the default is warning level and currently the install only shows the warning in the notebook
    # TODO@niv: let's talk about this sometime
    logging.warning(f"{PACKAGE_NAME} was not found on your system")
    logging.info(f"installing package. this might take up to {TIMEOUT_MINUTES} minutes...")
    print("\nstarting installation")

    # i didn't pipe here because i want the user to see the output
    with Popen(RUSTUP_CMD_ARGS) as rustup:
        rustup.wait(RUSTUP_TIMEOUT)

    with Popen(CARGO_CMD_ARGS) as cargo:
        cargo.wait(CARGO_TIMEOUT)

    if not _is_installed_package():
        raise Exception("installation failed - check the output")

    logging.info("installation completed")


def _is_installed_package():
    return Path(REGEX_EXE_PATH).is_file()


def rgx_span_out_type(output_arity):
    return tuple([DataTypes.span] * output_arity)


def rgx_string_out_type(output_arity):
    return tuple([DataTypes.string] * output_arity)


def _format_spanner_string_output(output: Iterable[str]):
    output_lists = []
    for out in output:
        out_list = []
        matches = ESCAPED_STRINGS_PATTERN.findall(out)
        for match in matches:
            # the pattern leaves the backslashes
            escaped_match = re.sub(r'\\"', '"', match)
            out_list.append(escaped_match)
        output_lists.append(out_list)

    return output_lists


def _format_spanner_span_output(output: Iterable[str]):
    output_lists = []
    for out in output:
        out_list = []
        matches = SPAN_PATTERN.finditer(out)
        for match in matches:
            start, end = int(match.group("start")), int(match.group("end"))
            out_list.append(Span(start, end))
        output_lists.append(out_list)

    return output_lists


def rgx(text, regex_pattern, out_type: str):
    """
    An IE function which runs regex using rust's `enum-spanner-rs` and yields tuples of strings/spans (not both).

    @param text: the string on which regex is run.
    @param regex_pattern: the pattern to run.
    @param out_type: string/span - decides which one will be returned.
    @return: a tuple of strings/spans.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        rgx_temp_file_name = Path(temp_dir) / TEMP_FILE_NAME
        with open(rgx_temp_file_name, "w+") as f:
            f.write(text)

        if out_type == "string":
            rust_regex_args = rf"{REGEX_EXE_PATH} {regex_pattern} {rgx_temp_file_name}"
            format_function = _format_spanner_string_output
        elif out_type == "span":
            rust_regex_args = rf"{REGEX_EXE_PATH} {regex_pattern} {rgx_temp_file_name} --bytes-offset"
            format_function = _format_spanner_span_output
        else:
            assert False, "illegal out_type"

        regex_output = format_function(run_command(rust_regex_args, stderr=True))

        for out in regex_output:
            yield out


def rgx_span(text, regex_pattern):
    """
    @param text: The input text for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of spans that represents the results.
    """
    return rgx(text, regex_pattern, "span")


RGX = dict(ie_function=rgx_span,
           ie_function_name='rgx_span',
           in_rel=RUST_RGX_IN_TYPES,
           out_rel=rgx_span_out_type)


def rgx_string(text, regex_pattern):
    """
    @param text: The input text for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of strings that represents the results.
    """
    return rgx(text, regex_pattern, "string")


RGX_STRING = dict(ie_function=rgx_string,
                  ie_function_name='rgx_string',
                  in_rel=RUST_RGX_IN_TYPES,
                  out_rel=rgx_string_out_type)

# currently, the package is installed when this module is imported
if not _is_installed_package():
    _download_and_install_rust_and_regex()
