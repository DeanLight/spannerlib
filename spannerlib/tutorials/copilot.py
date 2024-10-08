# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/tutorials/002_llm_code_documentation_example.ipynb.

# %% auto 0
__all__ = ['ast_xpath', 'ast_to_span', 'lex_concat']

# %% ../../nbs/tutorials/002_llm_code_documentation_example.ipynb 4
# importing dependencies
import re
import pandas as pd
from pandas import DataFrame
from pathlib import Path
from ..utils import load_env
from .. import get_magic_session,Session,Span

# %% ../../nbs/tutorials/002_llm_code_documentation_example.ipynb 15
from .basic import llm,format_ie,string_schema

# %% ../../nbs/tutorials/002_llm_code_documentation_example.ipynb 20
import ast
from functools import cache
from pyastgrep.search import search_python_files,Match
from pyastgrep.asts import ast_to_xml
from lxml import etree


# %% ../../nbs/tutorials/002_llm_code_documentation_example.ipynb 21
@cache
def _py_to_xml(py:str)->str:
    ast_tree = ast.parse(py)
    node_mappings = {}
    xml_tree = ast_to_xml(ast_tree, node_mappings)
    return xml_tree,ast_tree,node_mappings

def _xml_to_string(xml_tree):
    return etree.tostring(xml_tree, pretty_print=True).decode('utf-8')

def _print_file_xml(file_path):
    text = Path(file_path).read_text()
    xml_tree,_,_ = _py_to_xml(text)
    print(_xml_to_string(xml_tree))


def _ast_to_string(ast_tree):
    if isinstance(ast_tree,ast.AST):
        return ast.unparse(ast_tree)
    else:
        return ast_tree

def ast_xpath(py_str,xpath_query):
    if isinstance(py_str,Path):
        py_str = py_str.read_text()
    if isinstance(py_str,Span):
        py_str = str(py_str)
    xml_tree,ast_tree,node_mappings = _py_to_xml(py_str)
    xml_matches = xml_tree.xpath(xpath_query)
    ast_matches = [node_mappings[match] if match in node_mappings else match for match in xml_matches]
    return ast_matches

# %% ../../nbs/tutorials/002_llm_code_documentation_example.ipynb 26
@cache
def _get_lines(path):
    if isinstance(path,Path):
        tuple(path.read_text().split('\n'))
    else:
        return tuple(path.split('\n'))

def _get_character_position(path, line_number, column_offset):
    """gets a character position from a line number and column offset"""
    lines = _get_lines(path)
    if line_number < 1 or line_number > len(lines):
        raise ValueError("Invalid line number")
    line = lines[line_number - 1]
    if column_offset < 0 or column_offset > len(line):
        raise ValueError("Invalid column offset")
    return sum(len(lines[i]) + 1 for i in range(line_number - 1)) + column_offset

def ast_to_span(string,node):
    """given a node <node> of an ast from file <path>,
    returns the location of the node in the file as a Span object"""
    if isinstance(string,Path):
        text = string.read_text()
        name = string.name
    else:
        text = string
        name = None
    start = _get_character_position(str(text),node.lineno,node.col_offset)
    if hasattr(node,'end_lineno') and hasattr(node,'end_col_offset'):
        end = _get_character_position(str(text),node.end_lineno,node.end_col_offset)
    else:
        end = start + len(ast.unparse(node))
    return [Span(text,start,end,name=name)]

# %% ../../nbs/tutorials/002_llm_code_documentation_example.ipynb 29
def lex_concat(strings):
    return '\n'.join(sorted([str(s) for s in strings]))
