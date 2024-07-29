# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/040_magic_system.ipynb.

# %% auto 0
__all__ = ['logger', 'magic_args_parser', 'parser', 'get_magic_session', 'set_magic_session', 'curly_brace_to_glob_var',
           'parse_options', 'clean_query_lines', 'spannerlogMagic', 'load_ipython_extension']

# %% ../nbs/040_magic_system.ipynb 3
from typing import Optional
import logging
logger = logging.getLogger(__name__)

from pathlib import Path
import pandas as pd
from IPython.core.magic import (Magics, magics_class, line_cell_magic)
from singleton_decorator import singleton
from .utils import assert_df_equals
from .session import Session

# %% ../nbs/040_magic_system.ipynb 4
@singleton
class _MagicSession():
    def __init__(self):
        self.session = Session()

def get_magic_session():
    """Returns the session used by the magic system

    Returns:
        Session
    """    
    return _MagicSession().session

def set_magic_session(session: Session):
    """Changes the session used by the magic system to the one provided

    Args:
        session (Session): the session to use in the magic system
    """
    _MagicSession().session = session


# %% ../nbs/040_magic_system.ipynb 7
import argparse
import shlex
magic_args_parser = parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output",type=str, help="write code to file")
parser.add_argument("-a", "--append",type=str, help="append code to file")

def curly_brace_to_glob_var(line:str):
    """If the line is a variable name enclosed in curly braces, return the variable from the global scope
    """
    if line.startswith("{") and line.endswith("}"):
        var = line[1:-1]
    else:
        return line

    if var in globals():
        return globals()[var]
    else:
        raise ValueError(f"Variable {var} not found in global scope")

def parse_options(line):
    namespace = magic_args_parser.parse_args(shlex.split(line))
    args_dict = namespace.__dict__
    args_dict = {k:v for k,v in args_dict.items() if v is not None}
    args_dict = {k:curly_brace_to_glob_var(v) for k,v in args_dict.items()}
    return args_dict


# %% ../nbs/040_magic_system.ipynb 9
def clean_query_lines(code)->str:
    """remove query lines from code by removing lines that start with '?' """
    code_lines = code.split('\n')
    non_query_lines = [line for line in code_lines if not line.startswith('?')]

    # remove double empty lines
    clean_code = []
    for i, line in enumerate(non_query_lines):
        if i>0 and not line and not non_query_lines[i-1]:
            continue
        clean_code.append(line)
    clean_code = '\n'.join(clean_code)
    return clean_code

@magics_class
class spannerlogMagic(Magics):
    @line_cell_magic
    def spannerlog(self, line: str, cell: str) -> None:
        # import locally to prevent circular import issues
        magic_session = get_magic_session()

        args = parse_options(line)

        code = cell if cell else line
        try:
            _ = magic_session.export(code,display_results=True
                # ,return_statements_meta=True
                )
        except Exception as e:
            raise e from None

        if 'output' in args or 'append' in args:
            clean_code = clean_query_lines(code)

        if 'output' in args:
            out_file = Path(args['output'])
            out_file.write_text(clean_code + '\n')
            
        if 'append' in args:
            out_file = Path(args['append'])
            if not clean_code in out_file.read_text():
                with open(out_file, "a") as f:
                    f.write(clean_code + '\n')

def load_ipython_extension(ipython):
    ipython.register_magics(spannerlogMagic)
