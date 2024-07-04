# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/006_primitive_data_types.ipynb.

# %% auto 0
__all__ = ['logger', 'STRING_PATTERN', 'Var', 'FreeVar', 'RelationDefinition', 'Relation', 'IEFunction', 'AGGFunction',
           'IERelation', 'Rule', 'pretty']

# %% ../nbs/006_primitive_data_types.ipynb 3
from abc import ABC, abstractmethod
import pytest
from collections import defaultdict

import pandas as pd
from pathlib import Path
from typing import no_type_check, Set, Sequence, Any,Optional,List,Callable,Dict,Union
from pydantic import BaseModel
import networkx as nx
import itertools
from graph_rewrite import draw, draw_match, rewrite, rewrite_iter
from .utils import serialize_graph,serialize_df_values,checkLogs,get_new_node_name
from .span import Span,SpanParser

import logging
logger = logging.getLogger(__name__)

# %% ../nbs/006_primitive_data_types.ipynb 4
from enum import Enum
from typing import Any
from pydantic import ConfigDict


class Var(BaseModel):
    name: str
    def __hash__(self):
        return hash(self.name)

class FreeVar(BaseModel):
    name: str
    def __hash__(self):
        return hash(self.name)




class RelationDefinition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    scheme: List

class Relation(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    terms: List
    agg: Optional[Dict[FreeVar,str]] = None

class IEFunction(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    func: Callable
    # either a fixed schema, or a callable that takes the expected arity and given us the schema
    in_schema: Union[List,Callable] 
    out_schema: Union[List,Callable]


class AGGFunction(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    func: Union[Callable,str]
    in_schema: List 
    out_schema: List

class IERelation(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    in_terms: List
    out_terms: List
    def __hash__(self):
        hash_str = f'''{self.name}_in_{'_'.join([str(x) for x in self.in_terms])}_out_{'_'.join([str(x) for x in self.out_terms])}'''
        return hash(hash_str)

class Rule(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    head: Relation
    body: List[Union[Relation,IERelation]]

# %% ../nbs/006_primitive_data_types.ipynb 5
def pretty(obj):
    """pretty printing dataclasses for user messages,
    making them look like spannerlog code instead of python code"""
    
    if isinstance(obj,Span):
        return f"[{obj.start},{obj.end})"
    elif isinstance(obj,(Var,FreeVar)):
        return obj.name
    elif isinstance(obj,RelationDefinition):
        return f"{obj.name}({','.join(pretty(o) for o in obj.scheme)})"
    elif isinstance(obj,Relation):
        if obj.agg:
            pretty_terms = [f"{obj.agg[term]}({pretty(term)})" if (term in obj.agg) else pretty(term) for term in obj.terms]
        else:
            pretty_terms = [pretty(t) for t in obj.terms]
        return f"{obj.name}({','.join(pretty_terms)})"
    elif isinstance(obj,IERelation):
        return f"{obj.name}({','.join(pretty(o) for o in obj.in_terms)}) -> ({','.join(pretty(o) for o in obj.out_terms)})"
    elif isinstance(obj,IEFunction):
        return f"{obj.name}({','.join(pretty(o) for o in obj.in_schema)}) -> ({','.join(pretty(o) for o in obj.out_schema)})"
    elif isinstance(obj,Rule):
        return f"{pretty(obj.head)} <- {','.join(pretty(o) for o in obj.body)}"
    elif isinstance(obj,type):
        return obj.__name__
    else:
        return str(obj)

# %% ../nbs/006_primitive_data_types.ipynb 9
import re
STRING_PATTERN = re.compile(r"^[^\r\n]+$")


def _infer_relation_schema(row) -> Sequence[type]: # Inferred type list of the given relation
    """
    Guess the relation type based on the data.
    We support both the actual types (e.g. 'Span'), and their string representation ( e.g. `"[0,8)"`).

    **@raise** ValueError: if there is a cell inside `row` of an illegal type.
    """
    relation_types = []
    for cell in row:
        try:
            int(cell)  # check if the cell can be converted to integer
            relation_types.append(int)
        except (ValueError, TypeError):
            if isinstance(cell, Span) or SpanParser.parse(cell):
                relation_types.append(Span)
            elif re.match(STRING_PATTERN, cell):
                relation_types.append(str)
            else:
                raise ValueError(f"value doesn't match any datatype: {cell}")

    return relation_types
