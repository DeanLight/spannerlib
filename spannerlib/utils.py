# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/001_utils.ipynb.

# %% auto 0
__all__ = ['logger', 'DefaultIEs', 'DefaultAGGs', 'visualize_callback_df', 'schema_match', 'is_of_schema', 'type_merge',
           'schema_merge', 'df_to_list', 'serialize_tree', 'serialize_graph', 'serialize_df_values', 'assert_df',
           'span_to_str', 'assert_df_equals', 'checkLogs', 'patch_method', 'kill_process_and_children',
           'run_cli_command', 'is_node_in_graphs', 'get_new_node_name', 'get_git_root', 'load_env',
           'get_base_file_path', 'get_lib_name']

# %% ../nbs/001_utils.ipynb 4
import sys
import shlex
import psutil
import requests
import git
from dotenv import load_dotenv
import os
from pathlib import Path
import pandas as pd
import git
from configparser import ConfigParser
from subprocess import Popen, PIPE
from sys import platform
from threading import Timer
from typing import no_type_check, get_type_hints, Iterable, Any, Optional, Callable
from fastcore.basics import patch
import itertools
from singleton_decorator import singleton
import networkx as nx
from contextlib import contextmanager

import logging
logger = logging.getLogger(__name__)

from numbers import Real
from spannerflow.span import Span

# %% ../nbs/001_utils.ipynb 6
@singleton
class DefaultIEs():
    def __init__(self):
        self.ies = {}
    def add(self,*ie):
        assert len(ie) == 4, f"add should be called with 4 args: name, func, in schema, outschema"
        name = ie[0]
        self.ies[name] = ie
    def get(self,name:str):
        return self.ies[name]
    def remove(self,name):
        del self.ies[name]
    def as_list(self):
        return list(self.ies.values())

@singleton
class DefaultAGGs():
    def __init__(self):
        self.ies = {}
    def add(self,*ie):
        assert len(ie) == 4, f"add should be called with 4 args: name, func, in schema, outschema"
        name = ie[0]
        self.ies[name] = ie
    def get(self,name:str):
        return self.ies[name]
    def remove(self,name):
        del self.ies[name]
    def as_list(self):
        return list(self.ies.values())

# %% ../nbs/001_utils.ipynb 7
def _visualize_type(obj):
    if isinstance(obj,tuple):
        return tuple([type.__name__ for type in obj])
    else:
        return obj.__name__

def _visualize_registration_params(obj):
    if callable(obj):
        return obj.__name__
    elif isinstance(obj,list):
        return [_visualize_type(type) for type in obj]
    else:
        return obj

def _align_df_left(df):
    return (df.style
            .set_properties(**{'text-align': 'left'})
            .set_table_styles([{'selector': 'th', 'props': [('text-align', 'left')]}])
    )

def visualize_callback_df():
    """returns a dataframe summerising the registered callbacks"""
    to_concat = []
    ie_callbacks = pd.DataFrame(DefaultIEs().as_list(),columns=['name','function','input_schema','output_schema'])
    if len(ie_callbacks) > 0:
        ie_callbacks['type']='IE Function'
        to_concat.append(ie_callbacks)

    agg_callbacks = pd.DataFrame(DefaultAGGs().as_list(),columns=['name','function','input_schema','output_schema'])
    if len(agg_callbacks) > 0:
        agg_callbacks['type']='Aggregation Function'
        to_concat.append(agg_callbacks)

    df = pd.concat(to_concat).reset_index(drop=True)
    df = df.map(_visualize_registration_params)
    df = _align_df_left(df)
    return df.set_caption('Registered Callbacks')

# %% ../nbs/001_utils.ipynb 9
def schema_match(schema,expected,ignore_types=None):
    """checks if"""
    if len(schema) != len(expected):
        return False
    if ignore_types is None:
        ignore_types = []
    for x,y in zip(schema,expected):
        if x in ignore_types:
            continue
        if not issubclass(x,y):
            return False
    return True


def is_of_schema(relation,schema,ignore_types=None):
    """checks if a relation is of a given schema"""
    try:
        if len(relation) != len(schema):
            return False
        if ignore_types is None:
            ignore_types = []
        for x,y in zip(relation,schema):
            if type(x) in ignore_types:
                continue
            if not isinstance(x,y):
                return False
        return True
    except Exception as e:
        logger.error(f"Got Error when computing:\n"
                     f"is_of_scehma({relation},{schema})\n"
                     f"Error: {e}")
        raise e

def type_merge(type1,type2):
    if issubclass(type1,type2):
        return type1
    elif issubclass(type2,type1):
        return type2
    else:
        raise ValueError(f"Trying to merge types {type1},{type2}, types are incompatible")

def schema_merge(schema1,schema2):
    """merges two schemas, taking the stricter type between the two for each index"""
    if len(schema1) != len(schema2):
        raise ValueError(f"Trying to merge schemas {schema1},{schema2} schemas must be of the same length")
    
    new_schema = [type_merge(x,y) for x,y in zip(schema1,schema2)]
    return new_schema


# %% ../nbs/001_utils.ipynb 13
def df_to_list(df):
    return df.to_dict(orient='records')

# %% ../nbs/001_utils.ipynb 14
def serialize_tree(g):
    root = next(nx.topological_sort(g))
    return nx.tree_data(g,root) 


def serialize_graph(g):
    return list(g.nodes(data=True)),list(g.edges(data=True))


# %% ../nbs/001_utils.ipynb 15
def serialize_df_values(df):
    return set(df.itertuples(index=False,name=None))

def assert_df(df,values,columns=None):
    if columns is not None:
        assert list(df.columns)==columns, f"columns not equal: {list(df.columns)} != {columns}"
    assert serialize_df_values(df)==set(values) , f"values: {serialize_df_values(df)} != {values}"

def span_to_str(span):
    if isinstance(span,Span):
        return span.as_str()
    else:
        return str(span)

def assert_df_equals(df1,df2):

    df1 = df1.map(span_to_str)
    df2 = df2.map(span_to_str)

    assert list(df1.columns)==list(df2.columns), f"columns not equal: {list(df1.columns)} != {list(df2.columns)}"
    vals1 = serialize_df_values(df1)
    vals2 = serialize_df_values(df2) 
    assert vals1==vals2 , (
        f"values: {vals1} != {vals2}\n"
        f"values only in df1: {vals1-vals2}\n"
        f"values only in df2: {vals2-vals1}"
    )
    return df1

# %% ../nbs/001_utils.ipynb 22
from contextlib import contextmanager
import logging

@contextmanager
def checkLogs(level: int=logging.DEBUG, name :str='__main__', toFile=None):
    """context manager for temporarily changing logging levels. used for debugging purposes

    Args:
        level (logging.Level: optional): logging level to change the logger to. Defaults to logging.DEBUG.
        name (str: optional): module name to raise logging level for. Defaults to root logger
        toFile (Path: optional): File to output logs to. Defaults to None
        

    Yields:
        [logging.Logger]: the logger object that we raised the level of
    """
    logger = logging.getLogger(name)
    current_level = logger.getEffectiveLevel()
    format = "%(name)s - %(levelname)s - %(message)s"
    logger.setLevel(level)
    if len(logger.handlers) == 0:
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter(format))
        logger.addHandler(sh)
    if toFile != None:
        fh = logging.FileHandler(toFile)
        fh.setFormatter(logging.Formatter(format))
        logger.addHandler(fh)
    try:
        yield logger
    finally:
        logger.setLevel(current_level)
        if toFile != None:
            logger.removeHandler(fh)
        if len(logger.handlers) == 1:
            logger.handlers= []

# %% ../nbs/001_utils.ipynb 23
def patch_method(func : Callable, *args, **kwargs) -> None:
    """
    Applies fastcore's `patch` decorator and removes `func` from `cls.__abstractsmethods__` in case <br>
    `func` is an `abstractmethods`
    """
    cls = next(iter(get_type_hints(func).values()))
    try:
        abstracts_needed = set(cls.__abstractmethods__)
        abstracts_needed.discard(func.__name__)
        cls.__abstractmethods__ = abstracts_needed
    except AttributeError: # If the class does not inherit from an abstract class
        pass
    finally:
        # Apply the original `patch` decorator
        patch(*args, **kwargs)(func)

# %% ../nbs/001_utils.ipynb 25
def kill_process_and_children(process: Popen) -> None:
    logger.info("~~~~ process timed out ~~~~")
    if process.poll() is not None:
        ps_process = psutil.Process(process.pid)
        for child in ps_process.children(recursive=True):  # first, kill the children :)
            child.kill()  # not recommended in real life
        process.kill()  # lastly, kill the process

# %% ../nbs/001_utils.ipynb 26
def run_cli_command(command: str, # a single command string
                    stderr: bool = False, # if true, suppress stderr output. default: `False`
                    # if true, spawn shell process (e.g. /bin/sh), which allows using system variables (e.g. $HOME),
                    # but is considered a security risk (see: https://docs.python.org/3/library/subprocess.html#security-considerations)
                    shell: bool = False, 
                    timeout: float = -1 # if positive, kill the process after `timeout` seconds. default: `-1`
                    ) -> Iterable[str]: # string iterator
    """
    This utility can be used to run any cli command, and iterate over the output.
    """
    # `shlex.split` just splits the command into a list properly
    command_list = shlex.split(command, posix=IS_POSIX)
    stdout = PIPE  # we always use stdout
    stderr_channel = PIPE if stderr else None

    process = Popen(command_list, stdout=stdout, stderr=stderr_channel, shell=shell)

    # set timer
    if timeout > 0:
        # set timer to kill the process
        process_timer = Timer(timeout, kill_process_and_children, [process])
        process_timer.start()

    # get output
    if process.stdout:
        process.stdout.flush()
    process_stdout, process_stderr = [s.decode("utf-8") for s in process.communicate()]
    for output in process_stdout.splitlines():
        output = output.strip()
        if output:
            yield output

    if stderr:
        logger.info(f"stderr from process {command_list[0]}: {process_stderr}")

# %% ../nbs/001_utils.ipynb 28
def _biggest_int_node_name(g:nx.Graph):
    return max([n for n in g.nodes if isinstance(n,int)],default=-1)

def is_node_in_graphs(name,gs):
    return any(name in g.nodes for g in gs)

def get_new_node_name(g,prefix=None,avoid_names_from=None):
    if avoid_names_from is None:
        avoid_names_from = []
    graphs_to_avoid = [g]+avoid_names_from
    # ints
    if prefix is None:
        max_int = _biggest_int_node_name(g)+1
        while is_node_in_graphs(max_int,graphs_to_avoid):
            max_int+=1
        return max_int
    # strings
    else: 
        if not is_node_in_graphs(prefix,graphs_to_avoid):
            return prefix
        for i in itertools.count():
            name = f"{prefix}_{i}"
            if not is_node_in_graphs(name,graphs_to_avoid):
                return name

# %% ../nbs/001_utils.ipynb 33
def get_git_root(path='.'):

        git_repo = git.Repo(path, search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        return Path(git_root)

# %% ../nbs/001_utils.ipynb 35
def load_env(path=None):
    if path is None:
        path = get_git_root() / '.env.dev'
    load_dotenv(path)
    logger.warning(f'Loaded env from {path.relative_to(get_git_root())}')

# %% ../nbs/001_utils.ipynb 37
def get_base_file_path() -> Path: # The absolute path of parent folder of nbs
    return get_git_root()


def get_lib_name() -> str:
    setting_ini = ConfigParser()
    setting_ini.read(get_base_file_path()/'settings.ini')
    setting_ini = setting_ini['DEFAULT']
    return setting_ini['lib_name']
