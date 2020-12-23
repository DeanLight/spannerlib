"""
this module contains helper functions and function decorators that are used in lark passes
"""

from lark import Tree as LarkNode
import rgxlog.engine.ie_functions as ie_functions
from rgxlog.engine.structured_nodes import *
from rgxlog.engine.symbol_table import SymbolTableBase
from typing import Union
from rgxlog.engine.expected_grammar import rgxlog_expected_children_names_lists


def assert_expected_node_structure_aux(lark_node):
    """
    checks whether a lark node has a structure that the lark passes expect

    Args:
        lark_node: the lark node to be checked
    """

    # check if lark_node is really a lark node. this is done because applying the check recursively might result in
    # some children being literal values and not lark nodes
    if isinstance(lark_node, LarkNode):
        node_type = lark_node.data
        if node_type in rgxlog_expected_children_names_lists:

            # this lark node's structure can be checked, get its children and expected children lists
            children_names = [child.data for child in lark_node.children if isinstance(child, LarkNode)]
            expected_children_names_lists = rgxlog_expected_children_names_lists[node_type]

            # check if the node's children names match one of the expected children names lists
            if children_names not in expected_children_names_lists:
                # the node has an unexpected structure, raise an exception
                expected_children_list_strings = [str(children) for children in expected_children_names_lists]
                expected_children_string = '\n'.join(expected_children_list_strings)
                raise Exception(f'node of type "{node_type}" has unexpected children: {children_names}\n'
                                f'expected one of the following children lists:\n'
                                f'{expected_children_string}')

        # recursively check the structure of the node's children
        for child in lark_node.children:
            assert_expected_node_structure_aux(child)


def assert_expected_node_structure(func):
    """
    use this decorator to check whether a method's input lark node has a structure that is expected by the lark passes
    the lark node and its children are checked recursively

    note that this decorator should only be used on methods that expect lark nodes that weren't converted to
    structured nodes

    some lark nodes may have multiple structures (e.g. assignment). in this case this check will succeed if the lark
    node has one of those structures
    """

    def wrapped_method(visitor, lark_node):
        assert_expected_node_structure_aux(lark_node)
        ret = func(visitor, lark_node)
        return ret

    return wrapped_method


def unravel_lark_node(func):
    """
    even after converting a lark tree to use structured nodes, the methods in lark passes will still receive a lark
    node as an input, and the child of said lark node will be the actual structured node that the method will work
    with.

    use this decorator to replace a method's lark node input with its child structured node
    """

    def wrapped_method(visitor, lark_node):
        structured_node = lark_node.children[0]
        ret = func(visitor, structured_node)
        return ret

    return wrapped_method


def get_set_of_free_var_names(term_list: list, type_list: list):
    """
    Args:
        term_list: a list of terms
        type_list: a list of the term types

    Returns: a set of all the free variable names in term_list
    """
    free_var_names = set(term for term, term_type in zip(term_list, type_list)
                         if term_type is DataTypes.free_var_name)
    return free_var_names


def get_set_of_input_free_var_names(relation: Union[Relation, IERelation], relation_type: str):
    """
    Args:
        relation: a relation (either a normal relation or an ie relation)
        relation_type: the type of the relation

    Returns: a set of the free variable names used as input terms in the relation
    """
    if relation_type == "relation":
        # normal relations don't have input terms, return an empty set
        return set()
    elif relation_type == "ie_relation":
        # return a set of the free variables in the input term list
        return get_set_of_free_var_names(relation.input_term_list, relation.input_type_list)
    else:
        raise Exception(f'unexpected relation type: {relation_type}')


def get_set_of_output_free_var_names(relation: Union[Relation, IERelation], relation_type: str):
    """
    Args:
        relation: a relation (either a normal relation or an ie relation)
        relation_type: the type of the relation

    Returns: a set of the free variable names used as output terms in the relation
    """
    if relation_type == "relation":
        # the term list of a normal relation serves as the output term list, return its free variables
        return get_set_of_free_var_names(relation.term_list, relation.type_list)
    elif relation_type == "ie_relation":
        # return a set of the free variables in the output term list
        return get_set_of_free_var_names(relation.output_term_list, relation.output_type_list)
    else:
        raise Exception(f'unexpected relation type: {relation_type}')


def check_if_term_list_is_properly_typed(term_list: list, type_list: list,
                                         correct_type_list: list, symbol_table: SymbolTableBase):
    """
    check if the term list is properly typed.
    the term list could include free variables, this method will assume their actual type is correct.
    Args:
        term_list: the term list to be type checked
        type_list: the types of the terms in term_list
        correct_type_list: a list of the types that the terms must have to pass the type check
        symbol_table: a symbol table (used to get the types of variables)

    Returns: True if the type check passed, else False
    """
    if len(term_list) != len(type_list) or len(term_list) != len(correct_type_list):
        raise Exception("the length of term_list, type_list and correct_type_list should be the same")

    # perform the type check
    for term, term_type, correct_type in zip(term_list, type_list, correct_type_list):
        if term_type is DataTypes.var_name:
            # current term is a variable, get its type from the symbol table and check if it is correct
            var_type = symbol_table.get_variable_type(term)
            if var_type != correct_type:
                # the variable is not properly typed, the type check failed
                return False
        elif term_type is not DataTypes.free_var_name and term_type != correct_type:
            # the term is a literal that is not properly typed, the type check failed
            return False
    # all variables are properly typed, the type check succeeded
    return True


def check_if_relation_is_properly_typed(relation: Union[Relation, IERelation], relation_type: str,
                                        symbol_table: SymbolTableBase):
    """
    checks if a relation is properly typed
    this check ignores free variables

    Args:
        relation: the relation to be checked
        relation_type: the type of the relation
        symbol_table: a symbol table (to check the types of regular variables)

    Returns: true if the relation is properly typed, else false
    """

    if relation_type == 'relation':
        # get the schema of the relation
        relation_schema = symbol_table.get_relation_schema(relation.relation_name)
        # check if the relation's term list is properly typed
        relation_is_properly_typed = check_if_term_list_is_properly_typed(
            relation.term_list, relation.type_list, relation_schema, symbol_table)

    elif relation_type == "ie_relation":

        # get the input and output schemas of the ie function
        ie_func_name = relation.relation_name
        ie_func_data = getattr(ie_functions, ie_func_name)
        input_schema = ie_func_data.get_input_types()
        output_arity = len(relation.output_term_list)
        output_schema = ie_func_data.get_output_types(output_arity)

        # perform the type check on both the input and output term lists
        # both of them need to be properly typed for the check to pass
        input_type_check_passed = check_if_term_list_is_properly_typed(
            relation.input_term_list, relation.input_type_list, input_schema, symbol_table)
        output_type_check_passed = check_if_term_list_is_properly_typed(
            relation.output_term_list, relation.output_type_list, output_schema, symbol_table)
        relation_is_properly_typed = input_type_check_passed and output_type_check_passed

    else:
        raise Exception(f'unexpected relation type: {relation_type}')

    return relation_is_properly_typed


def type_check_rule_free_vars(rule: Rule, symbol_table: SymbolTableBase):
    """
    free variables in rules get their type from the relations in the rule body.
    it is possible for a free variable to be expected to be more than one type (meaning it has conflicting types).
    for each free variable in the rule body relations, this method will check for its type and will check if it
    has conflicting types

    Args:
        rule: the rule to be checked
        symbol_table: a symbol table (used to get the schema of the relation)

    Returns: a tuple (free_var_to_type, conflicted_free_vars) where
        free_var_to_type: a mapping from a free variable to its type
        conflicted_free_vars: a set of all the conflicted free variables
    """
    free_var_to_type = dict()
    conflicted_free_vars = set()

    for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):

        if relation_type == 'relation':
            # get the schema for the relation
            relation_schema = symbol_table.get_relation_schema(relation.relation_name)
            # perform the free variable type checking
            type_check_rule_body_relation_free_vars(
                relation.term_list, relation.type_list, relation_schema, free_var_to_type, conflicted_free_vars)

        elif relation_type == "ie_relation":

            # get the input and output schema of the ie function
            ie_func_name = relation.relation_name
            ie_func_data = getattr(ie_functions, ie_func_name)
            input_schema = ie_func_data.get_input_types()
            output_arity = len(relation.output_term_list)
            output_schema = ie_func_data.get_output_types(output_arity)

            # perform the free variable type checking on both the input and output term lists of the ie relation
            type_check_rule_body_relation_free_vars(relation.input_term_list, relation.input_type_list,
                                                    input_schema, free_var_to_type, conflicted_free_vars)
            type_check_rule_body_relation_free_vars(relation.output_term_list, relation.output_type_list,
                                                    output_schema, free_var_to_type, conflicted_free_vars)

        else:
            raise Exception(f'unexpected relation type: {relation_type}')

    return free_var_to_type, conflicted_free_vars


def type_check_rule_body_relation_free_vars(term_list: list, type_list: list, correct_type_list: list,
                                            free_var_to_type: dict, conflicted_free_vars: set):
    """
    a helper function for the method "type_check_rule_free_vars"
    performs the free variables type checking on term_list

    Args:
        term_list: the term list of a rule body relation
        type_list: the types of the terms in term_list
        correct_type_list: a list of the types that the terms in the term list should have
        free_var_to_type: a mapping of free variables to their type (those that are currently known)
        this function updates this mapping if it finds new free variables in term_list
        conflicted_free_vars: a set of the free variables that are found to have conflicting types
        this function adds conflicting free variables that it finds to this set
    """
    if len(term_list) != len(type_list) or len(term_list) != len(correct_type_list):
        raise Exception("the length of term_list, type_list and correct_type_list should be the same")

    for term, term_type, correct_type in zip(term_list, type_list, correct_type_list):
        if term_type is DataTypes.free_var_name:
            # found a free variable, check for conflicting types
            free_var = term
            if free_var in free_var_to_type:
                # free var already has a type, make sure there's no conflict with the expected type.
                free_var_type = free_var_to_type[free_var]
                if free_var_type != correct_type:
                    # found a conflicted free var, add it to the conflicted free vars set
                    conflicted_free_vars.add(free_var)
            else:
                # free var does not currently have a type, map it to the correct type
                free_var_to_type[free_var] = correct_type
