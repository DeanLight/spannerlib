# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/009_term_graphs.ipynb.

# %% auto 0
__all__ = ['logger', 'add_select_constants', 'add_select_col_eq', 'add_project_uniq_free_vars', 'add_product_constants',
           'mask_terms', 'add_relation', 'add_ie_relation', 'get_bounding_order', 'rule_to_graph', 'graph_compose',
           'merge_term_graphs_pair', 'merge_term_graphs']

# %% ../nbs/009_term_graphs.ipynb 3
from IPython.display import display
import pandas as pd
import os
import networkx as nx
import itertools
import logging
import pytest
from collections import defaultdict
logger = logging.getLogger(__name__)

from graph_rewrite import draw

from .utils import checkLogs,serialize_df_values,serialize_graph,get_new_node_name
from .span import Span
from .ra import equalConstTheta,equalColTheta
from spannerlib.data_types import (
    _infer_relation_schema,
    Var,
    FreeVar,
    RelationDefinition,
    Relation,
    IEFunction,
    IERelation,
    Rule,
    pretty,
)

from .ra import _col_names


# %% ../nbs/009_term_graphs.ipynb 6
# utils for forming schema

def _rename_schema(old_schema,pos_val_tuples):
    try:
        new_schema  = old_schema.copy()
        for pos,val in pos_val_tuples:
            new_schema[pos] = val
    except KeyError as e:
        logger.error(f"Error renaming schema {old_schema} with position values {pos_val_tuples}: {e}")
    return new_schema

def _join_schema(schema1,schema2):

    new_schema = schema1.copy()
    for s in schema2:
        if s not in new_schema:
            new_schema.append(s)
    return new_schema

# %% ../nbs/009_term_graphs.ipynb 7
def add_select_constants(g,source,terms):
    """
    adds a select node as a father to source, with the constant terms defined in terms
    if no constant terms are defined, does nothing
    returns the select node if it was added or the source node if not


    Example - R(X,3):
    source <- select(theta(col1=3))
    """
    need_select = any(not isinstance(term,FreeVar) for term in terms)
    if not need_select:
        return source
    
    select_pos_val = list()
    for i,term in enumerate(terms):
        if not isinstance(term,FreeVar):
            select_pos_val.append((i,term))
    
    select_name = get_new_node_name(g)
    schema = g.nodes[source]['schema']
    g.add_node(select_name, op='select',theta=equalConstTheta(*select_pos_val),schema=schema)
    g.add_edge(select_name,source)
    return select_name

def add_select_col_eq(g,source,terms):
    """
    add nodes to filter source to include equality constraints between columns with the same free var
    if no such constraints are defined, does nothing 
    returns the top most node if it was added or the source node if not

    Example - R(X,Y,X):
    source <- select(theta(col1=col3))
    return project
    """
    
    # compute first position of each free var and store duplicates positions
    first_positions = {}
    duplicate_positions = defaultdict(list)
    for i,term in enumerate(terms):
        if isinstance(term,FreeVar):
            if term.name in first_positions:
                duplicate_positions[term.name].append(i)
            else:
                first_positions[term.name] = i

    # if no duplicates do nothing
    if len(duplicate_positions) == 0:
        return source

    # add equality constraints
    equality_constraints = []
    for duplicate_var,positions in duplicate_positions.items():
        i = first_positions[duplicate_var]
        for j in positions:
            equality_constraints.append((i,j))


    # override name so that select node remains the topmost node
    select_node = get_new_node_name(g)
    schema = g.nodes[source]['schema']
    g.add_node(select_node, op='select',theta=equalColTheta(*equality_constraints),schema=schema)
    g.add_edge(select_node,source)

    return select_node


def add_project_uniq_free_vars(g,source,terms):
    """
    add a rename and a project node to leave only the first appearance of each free var in a relation
    returns the project node if it was added or the source node if not

    Example - R(X,Y,X,3):
    source <- rename(names=[(1,X),(2,Y),(3,_F3),(4,_F4)]) <- project([X,Y])
    return project
    """
    seen_vars = []
    uniq_names = []
    for i,term in enumerate(terms):
        if isinstance(term,FreeVar) and term.name not in seen_vars:
            seen_vars.append(term.name)
            uniq_names.append(term.name)
        else:
            uniq_names.append(f'_F{i}')

    top_node = source
    # rename  to have unique names
    rename_node = get_new_node_name(g)
    
    source_schema = g.nodes[source]['schema'].copy()
    schema = _rename_schema(source_schema,list(enumerate(uniq_names)))

    g.add_node(rename_node, op='rename',schema=schema)
    g.add_edge(rename_node,top_node)
    top_node = rename_node
    # project to keep only the first appearance of each free var
    project_node = get_new_node_name(g)
    g.add_node(project_node, op='project',schema=list(seen_vars))
    g.add_edge(project_node,top_node)

    return project_node

def add_product_constants(g,source,terms):
    """
    adds a product node as a father to source, with the constant terms defined in terms
    if no constant terms are defined, does nothing
    returns the product node if it was added or the source not if not

    Example - F(X,3,Y,4)->(Z):
    source                       <- product() <- project([X,_C1,Y,_C2])
    get_const({'_C1':3,'_C2':4}) <- 

    example 2 - F(3,4)->(Z):
        get_const({'_C1':3,'_C2':4})


    """
    has_consts = any(not isinstance(term,FreeVar) for term in terms)
    has_vars = any(isinstance(term,FreeVar) for term in terms)
    if has_vars and not has_consts:
        return source
    

    product_pos_val = list()
    for i,term in enumerate(terms):
        if not isinstance(term,FreeVar):
            product_pos_val.append((i,term))
    
    const_dict = {f'_C{i}':val for i,val in product_pos_val}

    const_node = get_new_node_name(g)
    g.add_node(const_node, op='get_const',const_dict = const_dict,schema=list(const_dict.keys()))

    if has_consts and not has_vars:
        return const_node


    product_node = get_new_node_name(g)
    g.add_node(product_node, op='product',schema=g.nodes[source]['schema'] + g.nodes[const_node]['schema'])
    g.add_edge(product_node,source)
    g.add_edge(product_node,const_node)

    project_node = get_new_node_name(g)
    project_order = []
    for i,term in enumerate(terms):
        if isinstance(term,FreeVar):
            project_order.append(term.name)
        else:
            project_order.append(f'_C{i}')
    g.add_node(project_node, op='project',schema=project_order)
    g.add_edge(project_node,product_node)
    
    return project_node



# %% ../nbs/009_term_graphs.ipynb 11
def mask_terms(terms,mask):
    if mask is None:
        return terms
    if not len(mask) == len(terms):
        raise ValueError(f'mask_constant_select should have the same length as the relation terms, got terms={terms},mask={mask}')
    return [term if not mask[i] else FreeVar(name='_F{i}') for i,term in enumerate(terms)]

def add_relation(g,terms,name=None,source=None,mask_constant_select=None):
    """
    adds a relation to the graph
    WLOG a relation of the form R(X,Y,const)
    should be of the abstract form get(R)<-rename(0:X,1:Y)<-select(2:const)<-project([X,Y])
    if source is not None, source replaces get(R)
    returns (top most node, bottom most node) 
    """
    if source is None:
        rel_schema = _col_names(len(terms))
        g.add_node(name,rel=name,schema=rel_schema)
        source = name
        rename_node = get_new_node_name(g)

        # rename_schema = _rename_schema(rel_schema,[(i,term.name) for i,term in enumerate(terms) if isinstance(term,FreeVar)])
        # g.add_node(rename_node, op='rename',schema=rename_schema)
        # g.add_edge(rename_node,source)
        # source = rename_node

    # select on constant terms
    select_constant_terms = mask_terms(terms,mask_constant_select)
    select_node = add_select_constants(g,source,select_constant_terms)

    # add select on equal free vars assignments for freevars with the same name
    select_node = add_select_col_eq(g,select_node,terms)

    project_node = add_project_uniq_free_vars(g,select_node,terms)

    
    return (project_node,source)



# %% ../nbs/009_term_graphs.ipynb 12
def add_ie_relation(g,rel):
    """
    adds an ie relation to the graph
    WLOG a relation of the form f(X,Y,c1)->(Z,X,c2)
    should be of the abstract form 
    project(X,Y)          <- product()<-project([X,Y,_C2])<-ie_map(f)<-select(col_5==c2)<-select(col_0==col_4)<-rename(0:X,1:Y,3:Z)<-project([X,Y,Z])
    get_const({'_C2':c1}) <-
    returns (top most node, bottom most node)
    """
    ie_has_variable_inputs = any(isinstance(term,FreeVar) for term in rel.in_terms)
    if ie_has_variable_inputs:
        project_input_vars = get_new_node_name(g)
        schema = [term.name for term in rel.in_terms if isinstance(term,FreeVar)]
        g.add_node(project_input_vars, op='project',schema=schema)
    else:
        project_input_vars = None
    product_node = add_product_constants(g,project_input_vars,rel.in_terms)
    ie_map_node = get_new_node_name(g)

    combined_schema = _col_names(len(rel.in_terms)+len(rel.out_terms))

    g.add_node(ie_map_node, op='ie_map',func=rel.name,
        in_arity=len(rel.in_terms),
        out_arity=len(rel.out_terms),
        schema=combined_schema)
    g.add_edge(ie_map_node,product_node)
    # we will get combined input+output relation from the ie map so now we reason based on it

    combined_terms = rel.in_terms+rel.out_terms
    # TODO add a naive rename node to rename the output variables so we can join input and output
    rename_node = get_new_node_name(g)

    rename_schema = _rename_schema(combined_schema,[(i,term.name) for i,term in enumerate(combined_terms) if isinstance(term,FreeVar)])
    g.add_node(rename_node, op='rename',schema=rename_schema)
    g.add_edge(rename_node,ie_map_node)

    
    # we only need to select on the output constants, since the input constants where generated via the product
    # so we mask the input terms
    mask_input_constants = [True]*len(rel.in_terms)+[False]*len(rel.out_terms)
    top_node,_ = add_relation(g,terms=combined_terms,source=rename_node,mask_constant_select=mask_input_constants)

    return top_node,project_input_vars


# %% ../nbs/009_term_graphs.ipynb 21
def get_bounding_order(rule:Rule):
    """Get an order of evaluation for the body of a rule
    this is a very naive ordering that can be heavily optimized"""

    # we start with all relations since they can be bound at once
    order = list()
    bounded_vars = set()
    for rel in rule.body:
        if isinstance(rel,Relation):
            order.append(rel)
            for term in rel.terms:
                if isinstance(term,FreeVar):
                    bounded_vars.add(term)

    unordered_ierelations = {rel for rel in rule.body if isinstance(rel,IERelation)}
    while len(unordered_ierelations) > 0:
        for ie_rel in unordered_ierelations:
            in_free_vars = {term for term in ie_rel.in_terms if isinstance(term,FreeVar)}
            if in_free_vars.issubset(bounded_vars):
                order.append(ie_rel)
                out_free_vars = {term for term in ie_rel.out_terms if isinstance(term,FreeVar)}
                bounded_vars = bounded_vars.union(out_free_vars)
                unordered_ierelations.remove(ie_rel)
                break

    return order

# %% ../nbs/009_term_graphs.ipynb 24
def rule_to_graph(rule:Rule,rule_id):
    """
    converts a rule to a graph
    """
    g=nx.DiGraph()
    body_rels = get_bounding_order(rule)

    top_bottom_nodes = []

    # add all body relations to the graph
    for rel in body_rels:
        if isinstance(rel,Relation):
            top,bottom = add_relation(g,name=rel.name,terms=rel.terms)
            top_bottom_nodes.append((top,bottom))
        elif isinstance(rel,IERelation):
            top,bottom = add_ie_relation(g,rel)
            top_bottom_nodes.append((top,bottom))

    # connect outputs of different rels via joins
    # and connect input of ie functons into the join
    for i,((top,bottom),rel) in enumerate(zip(top_bottom_nodes,body_rels)):
        logger.debug(f'connecting bodies iteration {i}')
        if i == 0:
            prev_top = top
            continue
        logger.debug(f'connecting {prev_top} to {top}')

        join_node_name = get_new_node_name(g)
        g.add_node(join_node_name, op='join',schema=_join_schema(g.nodes[prev_top]['schema'],g.nodes[top]['schema']))
        g.add_edge(join_node_name,prev_top)
        g.add_edge(join_node_name,top)

        if isinstance(rel,IERelation):
            ie_has_variable_inputs = any(isinstance(term,FreeVar) for term in rel.in_terms)
            if ie_has_variable_inputs:
                logger.debug(f'adding input of ie {bottom} to join {prev_top}')
                g.add_edge(bottom,prev_top)
        prev_top = join_node_name

    head = rule.head
    # project all assignments into the head
    head_project_name = get_new_node_name(g)
    g.add_node(head_project_name, op='project', schema =[term.name for term in head.terms],rel=f'_{head.name}_{rule_id}')
    g.add_edge(head_project_name,prev_top)
    top_node = head_project_name

    if head.agg is not None:
        agg_node_name = get_new_node_name(g)
        agg_mapping = {k.name:v for k,v in head.agg.items()}
        g.add_node(agg_node_name, op='groupby',schema = g.nodes[head_project_name]['schema'],agg=agg_mapping)
        g.add_edge(agg_node_name,top_node)
        top_node = agg_node_name


    # add a union for each rule for the given head
    g.add_node(head.name,op='union',rel=head.name,schema = _col_names(len(head.terms)))
    g.add_edge(head.name,top_node)

    # add rule id for each node
    for u in g.nodes:
        g.nodes[u]['rule_id'] = {rule_id}
    return g


# %% ../nbs/009_term_graphs.ipynb 32
def graph_compose(g1,g2,mapping_dict,debug=False):
    """compose two graphs with a mapping dict"""
    # if there is a node in g2 that is renamed but has a name collision with an existing node that is not renamed, we will rename the existing node to a uniq name
    # making new names into a digraph is a dirty hack, TODO resolve this
    save_new_names= nx.DiGraph()
    original_mapping_dict = mapping_dict.copy()
    for u2 in g2.nodes():
        if u2 not in mapping_dict and u2 in g1.nodes():
            mapping_dict[u2] = get_new_node_name(g2,avoid_names_from=[g1,save_new_names])
            save_new_names.add_node(mapping_dict[u2])
    if debug:
        return mapping_dict
    g2 = nx.relabel_nodes(g2,mapping_dict,copy=True)

    merged_graph = nx.compose(g1,g2)
    for old_name,new_name in original_mapping_dict.items():
        rule_ids1 = g1.nodes[old_name].get('rule_id',set())
        rule_ids2 = g2.nodes[new_name].get('rule_id',set())
        merged_rule_ids = rule_ids1.union(rule_ids2)
        merged_graph.nodes[new_name]['rule_id'] = merged_rule_ids



    return merged_graph


# %% ../nbs/009_term_graphs.ipynb 38
def merge_term_graphs_pair(g1,g2,exclude_props = ['label'],debug=False):
    """merge two term graphs into one term graph
    when talking about term graphs, 2 nodes if their data is identical and all of their children are identical
    but we would also like to merge rules for the same head, so we will also nodes that have the same 'rel' attribute
    """

    def _are_nodes_equal(g1,u1,g2,u2):

        u1_data = g1.nodes[u1]
        u2_data = g2.nodes[u2]
        
        if 'rel' in u1_data and 'rel' in u2_data:
            return u1_data['rel'] == u2_data['rel']


        
        return False
        # TODO this old code tries to merge nodes, but then its hard to remember which belong to which rules so we only merge
        # so we will do this merging per query
        u1_clean_data = {k:v for k,v in u1_data.items() if k not in exclude_props}
        u2_clean_data = {k:v for k,v in u2_data.items() if k not in exclude_props}

        are_equal = u1_clean_data == u2_clean_data and all(v2 in node_mappings for v2 in g2.successors(u2))
        return are_equal
        

    # we will check for each node in g2 if it has a node in g1 which is it's equal.
    # and save that in a mapping
    node_mappings=dict()# g2 node name to g1 node name
    # we use the fact that g2 is going to be acyclic to travers it in postorder
    for u2 in nx.dfs_postorder_nodes(g2):
        for u1 in g1.nodes():
            if _are_nodes_equal(g1,u1,g2,u2):
                node_mappings[u2] = u1
                break



    if debug:
        return node_mappings
    else:
        return graph_compose(g1,g2,node_mappings)



def merge_term_graphs(gs,exclude_props = ['label'],debug=False):
    """merge a list of term graphs into one term graph
    """
    merge = gs[0]
    for g in gs[1:-1]:
        merge = merge_term_graphs_pair(merge,g,exclude_props,debug=False)
    # if debug, we run debug only on the last merge so we can iteratively debug a list of merges
    return merge_term_graphs_pair(merge,gs[-1],exclude_props,debug=debug)

