"""Execution spannerlog commands"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/010_engine.ipynb.

# %% auto 0
__all__ = ['logger', 'op_to_func', 'DB', 'Engine', 'get_rel', 'compute_acyclic_node', 'compute_recursive_node', 'compute_node']

# %% ../nbs/010_engine.ipynb 3
from abc import ABC, abstractmethod
import pytest
from collections import defaultdict
from spannerflow.engine import Engine as SpannerflowEngine
from spannerflow.span import Span

import pandas as pd
from pathlib import Path
from typing import no_type_check, Set, Sequence, Any,Optional,List,Callable,Dict,Union
from pydantic import BaseModel
import networkx as nx
import itertools
import logging
logger = logging.getLogger(__name__)

from graph_rewrite import draw, draw_match, rewrite, rewrite_iter
from spannerlib.utils import (
    serialize_graph,
    assert_df_equals,
    checkLogs,
    get_new_node_name
    )


from spannerlib.data_types import (
    Var, 
    FreeVar, 
    RelationDefinition, 
    Relation, 
    IEFunction,
    AGGFunction,
    IERelation, 
    Rule, 
    pretty
)
from spannerlib.ra import (
    _col_names,
    get_const,
    select,
    project,
    rename,
    union,
    intersection,
    difference,
    join,
    product,
    groupby,
    ie_map,
    merge_rows
)

from .term_graph import graph_compose, merge_term_graphs_pair,rule_to_graph,add_relation,add_project_uniq_free_vars



# %% ../nbs/010_engine.ipynb 5
def _pd_drop_row(df,row_vals):
    new_df = df[(df!=row_vals).all(axis=1)]
    return new_df



# %% ../nbs/010_engine.ipynb 7
class DB(dict):
    def __repr__(self):
        key_str=', '.join(self.keys())
        return f'DB({key_str})'

# %% ../nbs/010_engine.ipynb 9
from copy import deepcopy
from time import sleep
import os

class Engine():
    def __init__(self, rewrites=None):
        if rewrites is None:
            self.rewrites = []
        self.symbol_table={
            # key : type,val
        }
        self.Relation_defs={
            # key : RelationDefinition for both real and derived relations
        }
        self.ie_functions={
            # name : IEFunction class
        }

        self.agg_functions={
        }

        self.term_graph = nx.DiGraph()
        
        self.node_counter = itertools.count()
        self.rule_counter = itertools.count()

        self.db = DB(
            # relation_name: dataframe
        )
        self.collections = set()
        self.rules = set()
        # lets skip this for now and keep it a an attribute in the node graph
        self.rules_to_ids = {
            # rule pretty string: ( node id in term_graph, head_name)
        }
        self.head_to_rules = defaultdict(set)
        # head relation name to rule pretty string

        # self.rels_to_nodes() = {
        #     # relation name to node that represents it
        # }
        self.spannerflow_engine = SpannerflowEngine()
        self.spannerflow_engine.close()

    def set_var(self,var_name,value,read_from_file=False):
        symbol_table = self.symbol_table
        if var_name in symbol_table:
            existing_type,existing_value = symbol_table[var_name]
            if type(value) != existing_type:
                raise ValueError(f"Variable {var_name} was previously defined with {existing_value}({pretty(existing_type)})"
                                f" but is trying to be redefined to {value}({pretty(type(value))}) of a different type which might interfere with previous rule definitions")    
        symbol_table[var_name] = type(value),value
        return
    def get_var(self,var_name):
        return self.symbol_table.get(var_name,None)
    
    def del_var(self,var_name):
        del self.symbol_table[var_name]

    def get_relation(self,rel_name:str)-> RelationDefinition:
        return self.Relation_defs.get(rel_name,None)

    def set_relation(self,rel_def:RelationDefinition, rule=False):
        if rel_def.name in self.spannerflow_engine.get_collections():
            existing_def = self.Relation_defs[rel_def.name]
            if existing_def != rel_def:
                raise ValueError(f"Relation {rel_def.name} was previously defined with {existing_def}"
                                f"but is trying to be redefined to {rel_def} which might interfere with previous rule definitions")
            elif not rule:
                raise ValueError(f"Relation {rel_def.name} was previously defined")     
        SPANNER_LIB_TO_SPANNER_FLOW_TYPES_DICT = {
            str: "DATA_TYPE_STRING",
            int: "DATA_TYPE_INT",
            float: "DATA_TYPE_FLOAT",
            bool: "DATA_TYPE_BOOL"
        }

        spannerflow_schema = []
        for col_type in rel_def.scheme:
            if col_type not in SPANNER_LIB_TO_SPANNER_FLOW_TYPES_DICT:
                raise ValueError(f"Type {col_type} not supported by spannerflow")
            spannerflow_schema.append(SPANNER_LIB_TO_SPANNER_FLOW_TYPES_DICT[col_type])
        
        self.term_graph.add_node(rel_def.name, rel=rel_def.name, rule_id={'fact'})
        self.Relation_defs[rel_def.name] = rel_def
        if not rule:
            self.collections.add(rel_def.name)
            self.spannerflow_engine.add_collection(rel_def.name, spannerflow_schema)
        else:
            self.rules.add(rel_def.name)
        
    def del_relation(self,rel_name:str):
        if rel_name not in self.spannerflow_engine.get_collections():
            raise ValueError(f"Relation {rel_name.name} is not defined")
        
        if rel_name in self.Relation_defs:
            self.Relation_defs.pop(rel_name)
            if rel_name in self.rules:
                self.rules.remove(rel_name)
            elif rel_name in self.collections:
                self.collections.remove(rel_name)

        self.spannerflow_engine.delete_collection(rel_name)

    def add_fact(self,fact:Relation):
        self.spannerflow_engine.add_row(fact.name, fact.terms)
        
    def add_facts(self,rel_name,facts:pd.DataFrame):
        self.spannerflow_engine.add_rows(rel_name, facts.values.tolist())
        
    def load_csv(self, rel_name:str , path: str|Path, delim: str = ',', has_header: bool = False):
        if not os.path.exists(path):
            raise ValueError(f"Path {path} does not exist")
        self.spannerflow_engine.load_from_csv(rel_name, path, delim, has_header)
        
    def del_fact(self,fact:Relation):
        self.spannerflow_engine.delete_row(fact.name, fact.terms)
        # self.db[fact.name] = _pd_drop_row(df = self.db[fact.name],row_vals=fact.terms)

    def get_ie_function(self,name:str):
        return self.ie_functions.get(name,None)

    def set_ie_function(self,ie_func:IEFunction):
        self.ie_functions[ie_func.name]=ie_func
        self.spannerflow_engine.set_ie_function(ie_func.name, ie_func.func, ie_func.in_schema, ie_func.out_schema)

    def del_ie_function(self,name:str):
        del self.ie_functions[name]

    def get_agg_function(self,name:str):
        return self.agg_functions.get(name,None)
    
    def set_agg_function(self,agg_func:AGGFunction):
        self.agg_functions[agg_func.name]=agg_func
    
    def del_agg_function(self,name:str):
        del self.agg_functions[name]

    def add_rule(self,rule:Rule,schema:RelationDefinition=None):
        if not self.get_relation(rule.head.name) and schema is None:
            raise ValueError(f"Relation {rule.head.name} not defined before adding the rule with it's head\n"
                             f"And an relation schema was not supplied."
                             f"existing relations are {self.Relation_defs.keys()}")
        # if already defined, do nothing.
        if pretty(rule) in self.rules_to_ids:
            return

        if not schema is None:
            self.set_relation(schema, rule=True)

        rule_id = next(self.rule_counter)

        self.rules_to_ids[pretty(rule)] = rule_id,rule.head.name
        self.head_to_rules[rule.head.name].add(pretty(rule))

        g2 = rule_to_graph(rule,rule_id)

        merge_term_graph = merge_term_graphs_pair(self.term_graph,g2)
        self.term_graph = merge_term_graph
        

    def del_rule(self,rule_str:str):
        #TODO here we need to save rules by their head and when removing the last rule of a head, remove its definition from db as well
        if not rule_str in self.rules_to_ids:
            raise ValueError(f"Rule {rule_str} does not exist\n"
                             f"existing rules are {self.rules_to_ids.keys()}")
        rule_id,rule_head = self.rules_to_ids[rule_str]
        self.rules_to_ids.pop(rule_str)
        self.head_to_rules[rule_head].remove(rule_str)

        g = self.term_graph

        # if the head has no more rules, remove it from the relation defs and the term graph
        if len(self.head_to_rules[rule_head])==0:
            self.Relation_defs.pop(rule_head)
            g.remove_node(rule_head)

        nodes_to_delete=[]
        for u in g.nodes:
            node_rule_ids = g.nodes[u].get('rule_id',set())
            if rule_id in node_rule_ids:
                node_rule_ids.remove(rule_id)
                if len(node_rule_ids) == 0:
                    nodes_to_delete.append(u)
        g.remove_nodes_from(nodes_to_delete)
            
        return

    def del_head(self,head_name:str):
        """Deletes all rules whose head is head_name
        """
        rules_to_delete = self.head_to_rules[head_name].copy()
        for rule_str in rules_to_delete:
            self.del_rule(rule_str)

    def _inline_db_and_ies_in_graph(self,g:nx.DiGraph):
        g=deepcopy(g)
        for u in g.nodes:
            if g.out_degree(u)==0 and 'rel' in g.nodes[u]:
                g.nodes[u]['op'] = 'get_rel'
                g.nodes[u]['db'] = self.db
                g.nodes[u]['schema'] = _col_names(len(self.Relation_defs[g.nodes[u]['rel']].scheme))
            elif g.nodes[u]['op'] == 'ie_map':
                ie_func_name = g.nodes[u]['func']
                ie_definition = self.ie_functions[ie_func_name]
                g.nodes[u]['func'] = ie_definition.func
                g.nodes[u]['name'] = ie_definition.name
                g.nodes[u]['in_schema'] = ie_definition.in_schema
                g.nodes[u]['out_schema'] = ie_definition.out_schema
            elif g.nodes[u]['op'] == 'groupby':
                aggregate_func_names = g.nodes[u]['agg']
                aggregate_funcs = [self.agg_functions[name].func if name is not None else None for name in aggregate_func_names]
                g.nodes[u]['agg'] = aggregate_funcs
        return g


    def plan_query(self,q_rel:Relation,rewrites=None):
        if rewrites is None:
            rewrites = self.rewrites
        query_graph = self._inline_db_and_ies_in_graph(self.term_graph)

        # get the sub term graph induced by the relation head
        root_node = q_rel.name
        connected_nodes = list(nx.shortest_path(query_graph,root_node).keys())
        query_graph = nx.DiGraph(nx.subgraph(query_graph,connected_nodes))
        
        # add selects renames etc based on the query relation
        root_node,_ = add_relation(query_graph,name='query',terms=q_rel.terms,source=root_node)

        # TODO for all rewrites, run them
        return query_graph,root_node

    def execute_plan(self,query_graph,root_node,return_intermediate=False):
        results = compute_node(query_graph,root_node,ret_inter = return_intermediate)
        return results

    def run_query(self,q:Relation,rewrites=None,return_intermediate=False):
        query_graph,root_node = self.plan_query(q,rewrites)
        return self.spannerflow_engine.run_dataflow(nx.reverse(query_graph))


# %% ../nbs/010_engine.ipynb 29
def get_rel(rel,db,**kwargs):
    # helper function to get the relation from the db for external relations
    return db[rel]

op_to_func = {
    'union':union,
    'intersection':intersection,
    'difference':difference,
    'select':select,
    'project':project,
    'rename':rename,
    'join':join,
    'ie_map':ie_map,
    'get_rel':get_rel,
    'get_const':get_const,
    'product':product,
    'groupby':groupby
}

# %% ../nbs/010_engine.ipynb 30
def _in_cycle(g):
    return list(set(
        itertools.chain.from_iterable(nx.cycles.simple_cycles(g))
    ))

def _depends_on_cycle(g):
    in_cycle_nodes = _in_cycle(g)
    depends_on_cycle = {
        node for node in g.nodes if node in in_cycle_nodes or 
        len(set(nx.descendants(g,node)).intersection(in_cycle_nodes))>0
    }
    return depends_on_cycle

# %% ../nbs/010_engine.ipynb 31
def _collect_children_and_run(G,u,results,stack,log=False):
    children = list(G.successors(u))
    u_data = G.nodes[u]

    children_results = [results[v][-1] for v in children]
    op_func = op_to_func[u_data['op']]

    if log:
        logger.debug(f"computing node {u} with children {children} and data {u_data} , stack = {stack}")
        logger.debug(f"children results are {children_results}")
        logger.debug(f"children_data is {[G.nodes[v] for v in children]}")
    try:
        res = op_func(*children_results,**u_data)
    except Exception as e:
        raise Exception(f'During excution of node {u} with args {children_results} and kwargs {u_data}'
                        f' got error {e}'
        )
    if log:
        logger.debug(f"result of node {u} is {res}")
    results[u].append(res)
    return res


# %% ../nbs/010_engine.ipynb 32
def compute_acyclic_node(G,u,results,stack=None):
    res = _collect_children_and_run(G,u,results,[])
    logger.debug(f"setting {u} to final since it is acyclic\n")
    G.nodes[u]['final'] = True
    return res

def compute_recursive_node(G,u,results,stack=None):

    if stack is None:
        stack = []

    children = list(G.successors(u))
    u_data = G.nodes[u]
    op_func = op_to_func[u_data['op']]

    if u_data.get('final',False):
        return results[u][-1]    


    logger.debug(f"computing node {u} with stack {stack}")


    went_in_a_cycle = u in stack
    if went_in_a_cycle:
        logger.debug(f"went in a cycle at {u}, computing op with empty children if necessary\n")
        # for each child that doesnt have data, put an empty df instead of it
        res = _collect_children_and_run(G,u,results,stack,log=True)
        return res

    # if we are here we are in a cycle but didnt return to an old position yet
    # then we compute all our children first
    for v in children:
        stack.append(u)
        compute_recursive_node(G,v,results,stack)
        stack.pop()

    # compute and mark as final if reached fixed point
    res = _collect_children_and_run(G,u,results,stack,log=True)

    all_children_final = all(G.nodes[v].get('final',False) for v in children)
    fixed_point_reached = len(results[u])>1 and results[u][-1].equals(results[u][-2])

    if all_children_final:
        logger.debug(f"setting {u} to final since all children are final\n")
        G.nodes[u]['final'] = True
    elif fixed_point_reached:
        logger.debug(f"setting {u} to final since fixed point has been achieved\n")
        # if u==9:
        #     logger.debug(f"graph nodes are{g.nodes(data=True)}")
        G.nodes[u]['final'] = True
    else:
        logger.debug(f"{u} not final yet so we will need to run another iteration\n")

    return res



def compute_node(G,root,ret_inter=False):

    # makes sure there is always a last value in the list for each key
    # which is None
    list_with_none_factory = lambda : [None]
    results_dict = defaultdict(list_with_none_factory)

    depends_on_cycle = _depends_on_cycle(G)
    not_depends_on_cycle = [u for u in G.nodes if u not in depends_on_cycle]

    # compute non cyclic nodes in postorder
    non_cycle_topological_sort = list(nx.topological_sort(nx.DiGraph(nx.subgraph(G,not_depends_on_cycle))))
    for u in non_cycle_topological_sort[::-1]:
        compute_acyclic_node(G,u,results_dict)

    logger.debug(f"the following nodes were computed non cyclically {non_cycle_topological_sort}")
    # now that all initial conditions for recursions are set
    # run the compute_recursive_node on u
    logger.debug(f"running compute_recursive_node on {root}")

    while True:
        res = compute_recursive_node(G,root,results_dict)
        if G.nodes[root].get('final',False):
            break

    if ret_inter:
        return res,results_dict
    else:
        return res

