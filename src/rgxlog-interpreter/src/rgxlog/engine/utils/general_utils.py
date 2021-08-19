"""
general utilities that are not specific to any kind of pass, execution engine, etc...
"""
import re

from rgxlog.engine.datatypes.ast_node_types import (Relation, IERelation, Rule)
from rgxlog.engine.datatypes.primitive_types import DataTypes, Span
from rgxlog.engine.state.symbol_table import SymbolTableBase
from typing import (Union, Tuple, Set, Dict, List, Optional)
from typing import Callable

SPAN_GROUP1 = "start"
SPAN_GROUP2 = "end"
# as of now, we don't support negative/float numbers (for both spans and integers)
SPAN_PATTERN = re.compile(r"^\[(?P<start>\d+), ?(?P<end>\d+)\)$")


def fixed_point(start, step: Callable, distance: Callable, thresh: int = 0):
    """
    Implementation of a generic fixed point algorithm - an algorithm that takes a step function and runs it until
    some distance is zero or below a threshold.
    """
    x = start
    y = step(x)
    while distance(x, y) > thresh:
        x = y
        y = step(x)
    return x


def get_free_var_names(term_list: List, type_list: List) -> Set:
    """
    @param term_list: a list of terms.
    @param type_list: a list of the term types.
    @return: a set of all the free variable names in term_list.
    """
    free_var_names = set(term for term, term_type in zip(term_list, type_list)
                         if term_type is DataTypes.free_var_name)
    return free_var_names


def get_numbered_free_var_pairs(relation: Union[Relation, IERelation]) -> List[Tuple]:
    """
    @param relation: a relation.
    @return: a list of all (free_var, index) pairs based on term_list.
    """
    term_list, type_list = relation.get_term_list(), relation.get_type_list()
    free_var_names = list(((i, term_pair[0]) for i, term_pair in enumerate(zip(term_list, type_list))
                           if term_pair[1] is DataTypes.free_var_name))
    return free_var_names


def get_input_free_var_names(relation: Union[Relation, IERelation]) -> Set:
    """
    @param relation: a relation (either a normal relation or an ie relation).
    @return: a set of the free variable names used as input terms in the relation.
    """

    if isinstance(relation, IERelation):
        return get_free_var_names(relation.input_term_list, relation.input_type_list)
    else:
        return set()


def get_output_free_var_names(relation: Union[Relation, IERelation]) -> Set:
    """
    @param relation: a relation (either a normal relation or an ie relation).
    @return: a set of the free variable names used as output terms in the relation.
    """
    return get_free_var_names(relation.get_term_list(), relation.get_type_list())


def get_numbered_output_free_var_names(relation: Union[Relation, IERelation]) -> List[Tuple]:
    """
    @param relation: a relation (either a normal relation or an ie relation).
    @return: a set of the free variable names used as output terms in the relation.
    """

    return get_numbered_free_var_pairs(relation)


def get_free_var_to_relations_dict(relations: Set[Union[Relation, IERelation]]) -> (
        Dict[str, List[Tuple[Union[Relation, IERelation], int]]]):
    """
    Finds for each free var in any of the relations, all the relations that contain it.
    also return the free vars' index in each relation (as pairs).
    for example:
        relations = [a(X,Y), b(Y)] ->
        dict = {X:[(a(X,Y),0)], Y:[(a(X,Y),1),(b(Y),0)]

    @param relations: a set of relations.
    @return: a mapping between each free var to the relations and corresponding columns in which it appears.
    """
    var_dict = {}

    # note: don't remove variables with less than 2 uses here, we need them as well
    for relation in relations:
        free_vars_pairs = get_numbered_output_free_var_names(relation)
        for i, var in free_vars_pairs:
            old_var_entry = var_dict.get(var, list())
            old_var_entry.append((relation, i))
            var_dict[var] = old_var_entry
    return var_dict


def check_properly_typed_term_list(term_list: list, type_list: list,
                                   correct_type_list: list, symbol_table: SymbolTableBase):
    """
    Checks if the term list is properly typed.
    the term list could include free variables, this method will assume their actual type is correct.

    @param term_list: the term list to be type checked.
    @param type_list: the types of the terms in term_list.
    @param correct_type_list: a list of the types that the terms must have to pass the type check.
    @param symbol_table: a symbol table (used to get the types of variables).
    @return: True if the type check passed, else False.
    """
    if len(term_list) != len(type_list) or len(term_list) != len(correct_type_list):
        raise Exception("the length of term_list, type_list and correct_type_list should be the same")

    # perform the type check
    for term, term_type, correct_type in zip(term_list, type_list, correct_type_list):

        if term_type is DataTypes.var_name:
            # current term is a variable, get its type from the symbol table
            term_type = symbol_table.get_variable_type(term)

        if term_type is not DataTypes.free_var_name and term_type != correct_type:
            # the term is a literal that is not properly typed, the type check failed
            return False

    # all variables are properly typed, the type check succeeded
    return True


def check_properly_typed_relation(relation: Union[Relation, IERelation], relation_type: str,
                                  symbol_table: SymbolTableBase):
    """
    Checks if a relation is properly typed, this check ignores free variables.

    @param relation: the relation to be checked.
    @param relation_type: the type of the relation.
    @param symbol_table: a symbol table (to check the types of regular variables).
    @return: true if the relation is properly typed, else false.
    """

    if relation_type == 'relation':
        # get the schema of the relation
        relation_schema = symbol_table.get_relation_schema(relation.relation_name)
        # check if the relation's term list is properly typed
        relation_is_properly_typed = check_properly_typed_term_list(
            relation.term_list, relation.type_list, relation_schema, symbol_table)

    elif relation_type == "ie_relation":

        # get the input and output schemas of the ie function
        ie_func_name = relation.relation_name
        ie_func_data = symbol_table.get_ie_func_data(ie_func_name)
        input_schema = ie_func_data.get_input_types()
        output_arity = len(relation.output_term_list)
        output_schema = ie_func_data.get_output_types(output_arity)

        # perform the type check on both the input and output term lists
        # both of them need to be properly typed for the check to pass
        input_type_check_passed = check_properly_typed_term_list(
            relation.input_term_list, relation.input_type_list, input_schema, symbol_table)
        output_type_check_passed = check_properly_typed_term_list(
            relation.output_term_list, relation.output_type_list, output_schema, symbol_table)
        relation_is_properly_typed = input_type_check_passed and output_type_check_passed

    else:
        raise Exception(f'unexpected relation type: {relation_type}')

    return relation_is_properly_typed


def type_check_rule_free_vars(rule: Rule, symbol_table: SymbolTableBase):
    """
    Free variables in rules get their type from the relations in the rule body.
    it is possible for a free variable to be expected to be more than one type (meaning it has conflicting types).
    for each free variable in the rule body relations, this method will check for its type and will check if it
    has conflicting types

    @param rule: the rule to be checked.
    @param symbol_table: a symbol table (used to get the schema of the relation).
    @return: a tuple (free_var_to_type, conflicted_free_vars) where
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
            type_check_rule_free_vars_aux(relation.term_list, relation.type_list, relation_schema,
                                          free_var_to_type, conflicted_free_vars)

        elif relation_type == "ie_relation":

            # get the input and output schema of the ie function
            ie_func_name = relation.relation_name
            ie_func_data = symbol_table.get_ie_func_data(ie_func_name)
            input_schema = ie_func_data.get_input_types()
            output_arity = len(relation.output_term_list)
            output_schema = ie_func_data.get_output_types(output_arity)

            # perform the free variable type checking on both the input and output term lists of the ie relation
            type_check_rule_free_vars_aux(relation.input_term_list, relation.input_type_list,
                                          input_schema, free_var_to_type, conflicted_free_vars)
            type_check_rule_free_vars_aux(relation.output_term_list, relation.output_type_list,
                                          output_schema, free_var_to_type, conflicted_free_vars)

        else:
            raise Exception(f'unexpected relation type: {relation_type}')

    return free_var_to_type, conflicted_free_vars


# TODO@tom: add params description
def type_check_rule_free_vars_aux(term_list: List, type_list: List, correct_type_list: List,
                                  free_var_to_type: Dict, conflicted_free_vars: Set):
    """
    A helper function for the method "type_check_rule_free_vars"
    performs the free variables type checking on term_list.

    @param term_list: the term list of a rule body relation.
    @param type_list: the types of the terms in term_list
                      correct_type_list: a list of the types that the terms in the term list should have
                      free_var_to_type: a mapping of free variables to their type (those that are currently known)
                      this function updates this mapping if it finds new free variables in term_list
                      conflicted_free_vars: a set of the free variables that are found to have conflicting types
                      this function adds conflicting free variables that it finds to this set.
    @param correct_type_list:
    @param free_var_to_type:
    @param conflicted_free_vars:
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


def rule_to_relation_name(rule: str) -> str:
    """
    Extracts the relation name from the rule string.

    @param rule: a string that represents a rule.
    @return:  the name of the rule relation
    """

    return rule.split('(')[0]


def string_to_span(string_of_span: str) -> Optional[Span]:
    span_match = re.match(SPAN_PATTERN, string_of_span)
    if not span_match:
        return None
    start, end = int(span_match.group(SPAN_GROUP1)), int(span_match.group(SPAN_GROUP2))
    return Span(span_start=start, span_end=end)
