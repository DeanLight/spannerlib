"""passes over the AST of a statement to do semantic checks and register state in the session object"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/020_micro_passes.ipynb.

# %% auto 0
__all__ = ['logger', 'convert_primitive_values_to_objects', 'CheckReservedRelationNames', 'dereference_vars',
           'check_referenced_paths_exist', 'inline_aggregation', 'relations_to_dataclasses',
           'verify_referenced_relations_and_functions', 'rules_to_dataclasses', 'is_rule_safe', 'check_rule_safety',
           'consistent_free_var_types_in_rule', 'assignments_to_name_val_tuple']

# %% ../nbs/020_micro_passes.ipynb 3
import os
import pytest
from pathlib import Path
from typing import no_type_check, Set, Sequence, Any,Optional,List,Callable,Dict,Union
from pydantic import BaseModel
import networkx as nx
from deepdiff import DeepDiff
from numbers import Real
import logging
logger = logging.getLogger(__name__)

from graph_rewrite import draw, draw_match, rewrite, rewrite_iter
from spannerlib.utils import (
    checkLogs,serialize_df_values,serialize_tree,
    schema_match,is_of_schema,type_merge,schema_merge
)
from .grammar import parse_spannerlog
from .span import Span
from spannerlib.engine import (
    Engine,
    Var,
    FreeVar,
    RelationDefinition,
    Relation,
    IEFunction,
    AGGFunction,
    IERelation,
    Rule,
    pretty,
    )

# %% ../nbs/020_micro_passes.ipynb 11
def convert_primitive_values_to_objects(ast,session):

    # primitive values
    def cast_new_value(match):
        val_type = match['var']['type']
        value = match['val_node']['val']
        match val_type:
            case 'var_name':
                value = Var(name=value)
            case 'free_var_name':
                value = FreeVar(name=value)
            case 'string':
                # remove the quotes
                value = str(value)[1:-1]
            case 'int':
                value = int(value)
            case 'int_neg':
                value = -int(value)
            case 'float':
                value = float(value)
            case 'float_neg':
                value = -float(value)
            case 'bool':
                value = True if value == 'True' else False
            case _:
                return value
        return value
    
    primitive_node_types = [
        'string','int','int_neg',
        'float','float_neg',"bool",
        'var_name','relation_name',
        'free_var_name','agg_name'
    ]
    #TODO FROM HERE
    rewrite(ast,
        lhs='var[type]->val_node[val]',
        p='var[type]',
        rhs='var[type,val={{new_val}}]',
        condition= lambda match: match['var']['type'] in primitive_node_types,
        render_rhs={'new_val': cast_new_value},
        # display_matches=True
        )


    # schema types into class types
    decl_type_to_class = {
        'decl_string':str,
        'decl_int':int,
        'decl_float':float,
        'decl_bool':bool,
    }

    for decl_type,decl_class in decl_type_to_class.items():
        for match in rewrite_iter(ast,lhs=f'x[val="{decl_type}"]'):
            match['x']['val']=decl_class


# %% ../nbs/020_micro_passes.ipynb 15
class CheckReservedRelationNames():
    def __init__(self,reserved_prefix):
        self.reserved_prefix = reserved_prefix
    def __call__(self,ast,engine):
        for match in rewrite_iter(ast,lhs='X[type="relation_name",val]'):
            relation_name = match['X']['val']
            if relation_name.startswith(self.reserved_prefix):
                raise ValueError(f"Relation name '{relation_name}' starts with reserved prefix '{self.reserved_prefix}'")

# %% ../nbs/020_micro_passes.ipynb 19
def dereference_vars(ast,engine):

    # first rename all left hand sign variables 
    # as type "var_name_lhs"
    # so we can seperate them from reference variables
    for assignment_type in ["assignment","read_assignment"]:
        for match in rewrite_iter(ast,
                lhs=f"""X[type="{assignment_type}"]-[idx=0]->LHS[type="var_name",val]"""
                ):
            match['LHS']['type'] = "var_name_lhs"

    # now for each reference variable check if it is in the symbol table and replace it with the value
    for match in rewrite_iter(ast,lhs=f"""X[type="var_name",val]"""):
        var_name = match['X']['val'].name
        if not engine.get_var(var_name):
            raise ValueError(f'Variable {var_name} is not defined')
        var_type,var_value = engine.get_var(var_name)
        match['X']['type'] = var_type
        match['X']['val'] = var_value


# %% ../nbs/020_micro_passes.ipynb 22
def check_referenced_paths_exist(ast,engine):
    for match in rewrite_iter(ast,
    lhs='X[type="read_assignment"]-[idx=1]->PathNode[val]',
    # display_matches=True
    ):
        path = Path(match['PathNode']['val'])
        print(repr(path))
        if not path.exists():
            raise ValueError(f'path {path} was not found in {os.getcwd()}')


# %% ../nbs/020_micro_passes.ipynb 25
def inline_aggregation(ast,engine):
    for match in rewrite_iter(ast,
        lhs='''
        agg_marker[type="aggregated_free_var"];
        agg_marker->agg_func[type="agg_name",val];
        agg_marker->agg_var[type="free_var_name",val]
        ''',
        #rhs='agg_marker[type="free_var_name",val=agg_var.val,agg=agg_func.val]',
        p='agg_marker[type]',
        # display_matches=True
        ):
        match['agg_marker']['type'] = 'free_var_name'
        match['agg_marker']['val'] = match['agg_var']['val']
        match['agg_marker']['agg'] = match['agg_func']['val']


# %% ../nbs/020_micro_passes.ipynb 29
def relations_to_dataclasses(ast,engine):

   # regular relations
   #TODO another example where i need to edit the graph imperatively because i dont have horizontal recursion in LHS
   for match in rewrite_iter(ast,
      lhs='''
         statement[type]->name[type="relation_name",val];
         statement->terms[type]
         ''',
         #TODO i expect to be able to put an rhs here only, and if a p is not given, assume it is the identity over nodes in LHS
         p='statement[type]',
         condition=lambda match: (match['statement']['type'] in ['add_fact','remove_fact','relation','rule_head','query']
                                   and match['terms']['type'] in ['term_list','free_var_name_list',]),
         # display_matches=True,
         ):
      term_nodes = list(ast.successors(match.mapping['terms']))
      #TODO check we iterate in order on the children
      logger.debug(f"casting relation to dataclasses - term_nodes: {term_nodes}")
      terms = [ast.nodes[term_node]['val'] for term_node in term_nodes]
      
      has_agg = any('agg' in ast.nodes[term_node] for term_node in term_nodes)
      if has_agg:
         agg_by_term = [ast.nodes[term_node].get('agg',None) for term_node in term_nodes]
      else:
         agg_by_term = None

      rel_object = Relation(name=match['name']['val'],terms=terms,agg=agg_by_term)
      if has_agg and match['statement']['type'] != 'rule_head':
            raise ValueError(f'''Aggregations are only allowed in rule heads, not in {match['statement']['type']}, found in {pretty(rel_object)}''')
      match['statement']['val'] = rel_object
      ast.remove_nodes_from(term_nodes)
   # relation declerations
   for match in rewrite_iter(ast,
      lhs='''
         statement[type="relation_declaration"]->name[type="relation_name",val];
         statement->terms[type="decl_term_list"]
         ''',
         p='statement[type]'):
      term_nodes = list(ast.successors(match.mapping['terms']))
      match['statement']['val'] = RelationDefinition(name=match['name']['val'],scheme=[ast.nodes[term_node]['val'] for term_node in term_nodes])
      ast.remove_nodes_from(term_nodes)

   # ie relations
   for match in rewrite_iter(ast,
      lhs='''
         statement[type="ie_relation"]->name[type="relation_name",val];
         statement-[idx=1]->in_terms[type="term_list"];
         statement-[idx=2]->out_terms[type="term_list"]
      ''',p='statement[type]'):
      in_term_nodes = list(ast.successors(match.mapping['in_terms']))
      out_term_nodes = list(ast.successors(match.mapping['out_terms']))



      ie_obj = IERelation(name=match['name']['val'],
                                             in_terms=[ast.nodes[term_node]['val'] for term_node in in_term_nodes],
                                             out_terms=[ast.nodes[term_node]['val'] for term_node in out_term_nodes]
                                             )
      for term_node in in_term_nodes+out_term_nodes:
         if 'agg' in ast.nodes[term_node]:
            raise ValueError(f'Aggregations are not allowed in IE relations, found in {pretty(ie_obj)}')
      match['statement']['val'] = ie_obj
      ast.remove_nodes_from(in_term_nodes+out_term_nodes)

# %% ../nbs/020_micro_passes.ipynb 35
def verify_referenced_relations_and_functions(ast,engine):

    def resolve_var_types(terms):
        return [engine.get_var(term.name)[0] if isinstance(term,Var) else term for term in terms]

    # check no free vars in adding or removing facts
    for match in rewrite_iter(ast,
            lhs='''rel[type]''',
            condition=lambda match: match['rel']['type'] in ['add_fact','remove_fact'],
            ):
        if any(isinstance(term,FreeVar) for term in match['rel']['val'].terms):
            raise ValueError(f"Adding or removing facts cannot have free variables, found in {pretty(match['rel']['val'])}")

    # regular relations
    for match in rewrite_iter(ast,
            lhs='''rel[type]''',
            condition=lambda match: match['rel']['type'] in ['add_fact','remove_fact','relation','query'],
            ):
        rel:Relation = match['rel']['val']
        if not engine.get_relation(rel.name):
            raise ValueError(f"Relation '{rel.name}' is not defined")
        expected_schema = engine.get_relation(rel.name).scheme
        if not is_of_schema(rel.terms,expected_schema,ignore_types=[FreeVar]):
            raise ValueError(f"Relation '{rel.name}' expected schema {pretty(engine.get_relation(rel.name))} but got called with {pretty(rel)}")

    # ie relations
    for match in rewrite_iter(ast,
            lhs='''rel[type="ie_relation"]''',
            ):
        rel:IERelation = match['rel']['val']
        if not engine.get_ie_function(rel.name):
            raise ValueError(f"ie function '{rel.name}' was not registered, registered functions are {list(engine.ie_functions.keys())}")
        in_schema = engine.get_ie_function(rel.name).in_schema
        if callable(in_schema):
            in_schema = in_schema(len(rel.in_terms))
        out_schema = engine.get_ie_function(rel.name).out_schema
        if callable(out_schema):
            out_schema = out_schema(len(rel.out_terms))
        if not is_of_schema(rel.in_terms,in_schema,ignore_types=[FreeVar]):
            raise ValueError(f"IERelation '{rel.name}' input expected schema {pretty(in_schema)} but got called with {pretty(rel.in_terms)}")
        if not is_of_schema(rel.out_terms,out_schema,ignore_types=[FreeVar]):
            raise ValueError(f"IERelation '{rel.name}' output expected schema {pretty(out_schema)} but got called with {pretty(rel.out_terms)}")
      
    # aggregation functions
    for match in rewrite_iter(ast,
        lhs='''rel[type="rule_head"]''',
        # display_matches=True
        ):
        rel = match['rel']['val']
        if rel.agg is None:
            continue
        agg_funcs = [func for func in rel.agg if func is not None]
        for agg_func in agg_funcs:
            if not engine.get_agg_function(agg_func):
                raise ValueError(f"agg function '{agg_func}' was not registered, registered functions are {list(engine.agg_functions.keys())}")


# %% ../nbs/020_micro_passes.ipynb 39
def rules_to_dataclasses(ast,engine):
   for match in rewrite_iter(ast,
      lhs='''
         statement[type="rule"]->head[type="rule_head",val];
         statement->body[type="rule_body_relation_list"]
      ''',p='statement[type]'):
      body_nodes = list(ast.successors(match.mapping['body']))
      head = match['head']['val']
      match['statement']['val'] = Rule(head=match['head']['val'],body=[ast.nodes[body_node]['val'] for body_node in body_nodes])
      ast.remove_nodes_from(body_nodes)
   return ast

# %% ../nbs/020_micro_passes.ipynb 42
def is_rule_safe(rule:Rule):
    """
    Checks that the Spannerlog Rule is safe
    ---
    In spannerlog, rule safety is a semantic property that ensures that IE relation's inputs are limited 
    in the values they can be assigned to by other relations in the rule body.
    This could include outputs of other IE relations.

    We call a free variable in a rule body "bound" if it exists in the output of any safe relation in the rule body.
    For normal relations, they only have output terms, so all their free variables are considered bound.

    We call a relation in a rule's body safe if all its input free variables are bound.
    For normal relations, they don't have input relations, so they are always considered safe.

    We call a rule safe if all of its body relations are safe.

    This basically means that we need to make sure there is at least one order of IE relation evaluation, in which
    each IE relation input variables is bound by the normal relations and the output relation of the previous IE relations.

    Examples:
    * `rel2(X,Y) <- rel1(X,Z), ie1(X)->(Y).` is a safe rule as the only input free variable, `X`, exists in the output of the safe relation `rel1(X, Z)`.  
    * `rel2(Y) <- ie1(Z)->(Y).` is not safe as the input free variable `Z` does not exist in the output of any safe relation.
    * `rel2(Z,W) <- rel1(X,Y),ie1(Z,Y)->(W),ie2(W,Y)->Z.` is not safe as both ie functions require each other's output as input, creating a circular dependency.
    ---
    """

    # get all free vars in regular relations
    normal_relations_free_vars = set()
    for body in rule.body:
        if isinstance(body,Relation):
            for term in body.terms:
                if isinstance(term,FreeVar):
                    normal_relations_free_vars.add(term.name)
    
    # get list of form [(ie_rel,{input_vars},{output_vars})]
    free_vars_per_ie_relation = {}
    for body in rule.body:
        if isinstance(body,IERelation):
            input_vars = set(term.name for term in body.in_terms if isinstance(term,FreeVar))
            output_vars = set(term.name for term in body.out_terms if isinstance(term,FreeVar))
            free_vars_per_ie_relation[body]=(input_vars,output_vars)
        
    # iteratively go over all previously unsafe ie relations and check if they are now safe

    safe_vars = normal_relations_free_vars.copy()
    safe_ie_relations = set()

    while True:
        if len(free_vars_per_ie_relation)==0:
            break
        
        safe_ie_relations_in_this_iteration = set()
        for ie_relation,(input_vars,output_vars) in free_vars_per_ie_relation.items():
            if input_vars.issubset(safe_vars):
                safe_ie_relations_in_this_iteration.add(ie_relation)
        
        if len(safe_ie_relations_in_this_iteration)== 0 :
            raise ValueError(f"Rule \'{pretty(rule)}\' is not safe:\n"
                            f"the following free vars where bound by normal relations: {normal_relations_free_vars}\n"
                            f"the following ie relations where safe: {safe_ie_relations}\n"
                            f"leading to the following free vars being bound: {safe_vars}\n"
                            f"However the following ie relations could not be bound: {[pretty(ie) for ie in free_vars_per_ie_relation.keys()]}\n"
                             )
    
        for ie_relation in safe_ie_relations_in_this_iteration:
            input_vars,output_vars = free_vars_per_ie_relation[ie_relation]
            safe_vars.update(output_vars)
            safe_ie_relations.add(ie_relation)
            del free_vars_per_ie_relation[ie_relation]



    return True

# %% ../nbs/020_micro_passes.ipynb 43
def check_rule_safety(ast,engine):
    for match in rewrite_iter(ast,lhs='X[type="rule",val]'):
        rule = match['X']['val']
        is_rule_safe(rule)
    return ast

# %% ../nbs/020_micro_passes.ipynb 46
from .term_graph import get_bounding_order

def _check_rule_consistency(rule,engine):
    # for each free var we encounter, what is the type is is according to the relation schema
    free_var_to_type = {}
    # what is the first relation we found each var in, useful for error messages
    first_rel_to_define_free_var = {}

    
    def verify_freevar_type(free_var,col_type):
        if free_var.name in free_var_to_type:
            try:
                new_type = type_merge(free_var_to_type[free_var.name],col_type)
                free_var_to_type[free_var.name] = new_type
            except:
                raise ValueError(f"FreeVar {free_var.name} is used with type {pretty(col_type)}\n"
                        f"but was previously defined with type {pretty(free_var_to_type[free_var.name])}\n"
                        f"in relation {first_rel_to_define_free_var[free_var.name]}")
        else:
            free_var_to_type[free_var.name] = col_type
            first_rel_to_define_free_var[free_var.name] = relation.name



    def verify_relation_types(rel_type,terms,expected_schema):
        logger.debug(f"verifying relation types for {rel_type} {pretty(relation)} expected_schema={pretty(expected_schema)}")
        if callable(expected_schema):
            expected_schema = expected_schema(len(terms))
        # for each term in the relation that is a free var
        for term,expected_type in zip(terms,expected_schema):
            if isinstance(term,FreeVar):
                try:
                    logger.debug(f"verifying free var type for {term} with type {expected_type}")
                    verify_freevar_type(term,expected_type)
                except ValueError as e:
                    raise ValueError(f"In rule {pretty(rule)}\nin {rel_type} {relation.name}\n{e}")
                

    for relation in get_bounding_order(rule):
        if isinstance(relation,Relation):
            verify_relation_types('relation',relation.terms,engine.get_relation(relation.name).scheme)
        elif isinstance(relation,IERelation):
            verify_relation_types('ie input relation',relation.in_terms,engine.get_ie_function(relation.name).in_schema)
            verify_relation_types('ie output relation',relation.out_terms,engine.get_ie_function(relation.name).out_schema)

    logger.debug(f"after deriving types from body clauses:free_var_to_type={free_var_to_type}")
           
    # for rule head, make sure all free vars are defined in the body
    # and if the rule head was used in another rule, make sure it has the same types
    head_name, head_terms = rule.head.name, rule.head.terms
    head_agg = rule.head.agg
    for term in head_terms:
        if isinstance(term,FreeVar) and not term.name in free_var_to_type:
            raise ValueError(f"In rule {pretty(rule)}\nFreeVar {term.name}\n"
                f"is used in the head but was not defined in the body")
    

    # if no aggregations, the head schema is the same as the free var types
    if head_agg is None:
        head_scheme = [free_var_to_type[term.name] if isinstance(term,FreeVar) else type(term) for term in head_terms]
    
    # if we do have aggregation, than we need to change the type of the free var to the type of the aggregation's output
    else:
        head_scheme = []
        for term,agg_name in zip(head_terms,head_agg):
            if not isinstance(term,FreeVar):
                head_scheme.append(type(term))
                continue

            if agg_name is not None:
                agg_func = engine.get_agg_function(agg_name)
                in_schema = agg_func.in_schema
                out_schema = agg_func.out_schema
                if not schema_match([free_var_to_type[term.name]],in_schema):
                    raise ValueError(f"In rule {pretty(rule)}\n"
                        f"in head clause {head_name}\n"
                        f"FreeVar {term.name} is aggregated with {agg_name}\n"
                        f"which expects input type {pretty(in_schema[0])}\n"
                        f"but got {pretty(free_var_to_type[term.name])}")
                head_scheme.append(out_schema[0])
            else:
                head_scheme.append(free_var_to_type[term.name])

    current_head_schema = RelationDefinition(name=head_name,scheme=head_scheme)

    if engine.get_relation(head_name):
        expected_head_schema = engine.get_relation(head_name)
        if expected_head_schema != current_head_schema:
            raise ValueError(f"In rule {pretty(rule)}\n"
                f"expected schema {pretty(expected_head_schema)}\n"
                f"from a previously defined rule to {head_name}\n"
                f"but got {pretty(current_head_schema)}")
    else:
        engine.set_relation(current_head_schema)


# %% ../nbs/020_micro_passes.ipynb 47
def consistent_free_var_types_in_rule(ast,engine):
    for match in rewrite_iter(ast,lhs='X[type="rule",val]'):
        rule = match['X']['val']
        _check_rule_consistency(rule,engine)
    return ast

# %% ../nbs/020_micro_passes.ipynb 50
def assignments_to_name_val_tuple(ast,engine):
    for match in rewrite_iter(ast,lhs='''
                                statement[type]-[idx=0]->var_name_node[val];
                                statement-[idx=1]->val_node[val]''',p='statement[type]',
                                condition=lambda match: match['statement']['type'] in ['assignment','read_assignment'],
                                # display_matches=True
                                ):
        match['statement']['val'] = (
            match['var_name_node']['val'].name,
            match['val_node']['val']
        )
    return ast
