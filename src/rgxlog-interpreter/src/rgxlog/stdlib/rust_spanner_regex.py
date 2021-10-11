"""
this module contains implementation of regex ie functions using the rust package `enum-spanner-rs`
"""
import logging
import re
import tempfile
from pathlib import Path
from subprocess import Popen, PIPE
from sys import platform
from typing import Tuple, List, Union, Iterable, Sequence, no_type_check, Callable, Optional

from rgxlog.engine.datatypes.primitive_types import DataTypes, Span
from rgxlog.stdlib.utils import run_cli_command

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
CARGO_CMD_ARGS: Sequence[Union[Path, str]] = ["cargo", "+" + RUSTUP_TOOLCHAIN, "install", "--root", REGEX_FOLDER_PATH, "--git", PACKAGE_GIT_URL]
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

logger = logging.getLogger(__name__)


def _download_and_install_rust_regex() -> None:
    # don't use "cargo -V" because it starts downloading stuff sometimes
    with Popen([WHICH_WORD, "cargo"], stdout=PIPE, stderr=PIPE) as cargo:
        errcode = cargo.wait(SHORT_TIMEOUT)

    with Popen([WHICH_WORD, "rustup"], stdout=PIPE, stderr=PIPE) as rustup:
        errcode |= rustup.wait(SHORT_TIMEOUT)

    if errcode:
        raise IOError(f"cargo or rustup are not installed in $PATH. please install rust: {DOWNLOAD_RUST_URL}")

    logger.warning(f"{PACKAGE_NAME} was not found on your system")
    logger.warning(f"installing package. this might take up to {TIMEOUT_MINUTES} minutes...")

    # there's no pipe here to let the user to see the output
    with Popen(RUSTUP_CMD_ARGS) as rustup:
        rustup.wait(RUSTUP_TIMEOUT)

    with Popen(CARGO_CMD_ARGS) as cargo:
        cargo.wait(CARGO_TIMEOUT)

    if not _is_installed_package():
        raise Exception("installation failed - check the output")

    logger.warning("installation completed")


def _is_installed_package() -> bool:
    return Path(REGEX_EXE_PATH).is_file()


@no_type_check
def rgx_span_out_type(output_arity: int) -> Tuple[DataTypes]:
    return tuple([DataTypes.span] * output_arity)


@no_type_check
def rgx_string_out_type(output_arity: int) -> Tuple[DataTypes]:
    return tuple([DataTypes.string] * output_arity)


def _format_spanner_string_output(output: Iterable[str]) -> List[List[str]]:
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


def _format_spanner_span_output(output: Iterable[str]) -> List[List[Span]]:
    output_lists = []
    for out in output:
        out_list = []
        matches = SPAN_PATTERN.finditer(out)
        for match in matches:
            start, end = int(match.group("start")), int(match.group("end"))
            out_list.append(Span(start, end))
        output_lists.append(out_list)

    return output_lists


def rgx(regex_pattern: str, out_type: str, text: Optional[str] = None, text_file: Optional[str] = None) -> Iterable[Iterable[Union[str, Span]]]:
    """
    An IE function which runs regex using rust's `enum-spanner-rs` and yields tuples of strings/spans (not both).

    @param text: the string on which regex is run.
    @param regex_pattern: the pattern to run.
    @param out_type: string/span - decides which one will be returned.
    @param text_file: use text from this file instead of `text`. default: None
    @return: a tuple of strings/spans.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        if text_file:
            rgx_temp_file_name = Path(text_file)
        else:
            assert text is not None, "at least one of text/text_file must have a value"
            rgx_temp_file_name = Path(temp_dir) / TEMP_FILE_NAME
            with open(rgx_temp_file_name, "w+") as f:
                f.write(text)

        if out_type == "string":
            rust_regex_args = f"{REGEX_EXE_PATH} {regex_pattern} {rgx_temp_file_name}"
            format_function: Callable = _format_spanner_string_output
        elif out_type == "span":
            rust_regex_args = f"{REGEX_EXE_PATH} {regex_pattern} {rgx_temp_file_name} --bytes-offset"
            format_function = _format_spanner_span_output
        else:
            assert False, "illegal out_type"

        regex_output = format_function(run_cli_command(rust_regex_args, stderr=True))

        for out in regex_output:
            yield out


def rgx_span(text: str, regex_pattern: str) -> Iterable[Iterable[Union[str, Span]]]:
    """
    @param text: The input text for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of spans that represents the results.
    """
    return rgx(regex_pattern, "span", text=text)


RGX = dict(ie_function=rgx_span,
           ie_function_name='rgx_span',
           in_rel=RUST_RGX_IN_TYPES,
           out_rel=rgx_span_out_type)


def rgx_string(text: str, regex_pattern: str) -> Iterable[Iterable[Union[str, Span]]]:
    """
    @param text: The input text for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of strings that represents the results.
    """
    return rgx(regex_pattern, "string", text=text)


RGX_STRING = dict(ie_function=rgx_string,
                  ie_function_name='rgx_string',
                  in_rel=RUST_RGX_IN_TYPES,
                  out_rel=rgx_string_out_type)


def rgx_span_from_file(text_file: str, regex_pattern: str) -> Iterable[Iterable[Union[str, Span]]]:
    """
    @param text_file: The input file for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of spans that represents the results.
    """
    return rgx(regex_pattern, "span", text_file=text_file)


RGX_FROM_FILE = dict(ie_function=rgx_span_from_file,
                     ie_function_name='rgx_span_from_file',
                     in_rel=RUST_RGX_IN_TYPES,
                     out_rel=rgx_span_out_type)


def rgx_string_from_file(text_file: str, regex_pattern: str) -> Iterable[Iterable[Union[str, Span]]]:
    """
    @param text_file: The input file for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of strings that represents the results.
    """
    return rgx(regex_pattern, "string", text_file=text_file)


RGX_STRING_FROM_FILE = dict(ie_function=rgx_string_from_file,
                            ie_function_name='rgx_string_from_file',
                            in_rel=RUST_RGX_IN_TYPES,
                            out_rel=rgx_string_out_type)

# the package is installed when this module is imported
if not _is_installed_package():
    _download_and_install_rust_regex()
