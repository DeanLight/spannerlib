"""
all the passes in this module are based on Lark.

Each pass inherits from one of the following classes:

1. Transformer - Takes a lark tree as an input and returns a completely new lark tree. The order of the nodes
that are visited could be defined by the user.

2. Visitor/Visitor_Recursive - Takes a lark tree as an input. If changes are performed to the lark tree,
they are done in place. The order in which the visitor visits the nodes is not defined, so you should only
use this class if you want to visit nodes without any context. Visitor_Recursive is mostly used because
according to the documentation it is faster.

3. Interpreter - Same as 'Visitor', only the order of node is defined (by default it is bfs from the root
of the lark tree, hence the name interpreter).

Below are some relevant links that will allow you to learn about lark.

The official documentation for lark can be found at:
https://lark-parser.readthedocs.io/en/stable/

A useful cheat sheet that should be handy for understanding the code in this module:
https://lark-parser.readthedocs.io/en/stable/lark_cheatsheet.pdf

A short tutorial on lark:
https://github.com/lark-parser/lark/blob/master/docs/json_tutorial.md
"""

from lark import Transformer
from lark import Tree as LarkNode
from lark.visitors import Interpreter, Visitor_Recursive
import rgxlog.engine.ie_functions as ie_functions
from rgxlog.engine.structured_nodes import *
from rgxlog.engine.datatypes import Span
from typing import Union

rgxlog_expected_children_names_lists = {

    'assignment': [
        ['var_name', 'string'],
        ['var_name', 'int'],
        ['var_name', 'span'],
        ['var_name', 'var_name'],
    ],

    'read_assignment': [
        ['var_name', 'string'],
        ['var_name', 'var_name']
    ],

    'relation_declaration': [['relation_name', 'decl_term_list']],

    'rule': [['rule_head', 'rule_body_relation_list']],

    'rule_head': [['relation_name', 'free_var_name_list']],

    'relation': [['relation_name', 'term_list']],

    'ie_relation': [['relation_name', 'term_list', 'term_list']],

    'query': [['relation_name', 'term_list']],

    'add_fact': [['relation_name', 'const_term_list']],

    'remove_fact': [['relation_name', 'const_term_list']],

    'span': [
        ['integer', 'integer'],
        []  # allow empty list to support spans that were converted a datatypes.Span instance
    ],

    'integer': [[]],

    'string': [[]],

    'relation_name': [[]],

    'var_name': [[]],

    'free_var_name': [[]]
}


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


class RemoveTokens(Transformer):
    """
    a lark pass that should be used before the semantic checks
    transforms the lark tree by removing the redundant tokens
    note that we inherit from 'Transformer' in order to be able to visit token nodes
    """

    def __init__(self, **kw):
        super().__init__(visit_tokens=True)

    @staticmethod
    def INT(args):
        string_of_integer = args[0:]
        integer = int(string_of_integer)
        return integer

    @staticmethod
    def LOWER_CASE_NAME(args):
        name_string = args[0:]
        return name_string

    @staticmethod
    def UPPER_CASE_NAME(args):
        name_string = args[0:]
        return name_string

    @staticmethod
    def STRING(args):
        quoted_string = args
        unquoted_string = quoted_string[1:-1]
        return unquoted_string


class CheckReservedRelationNames(Interpreter):
    """
    A lark tree semantic check.
    Checks if there are relations in the program with a name that starts with "__rgxlog__"
    if such relations exist, throw an exception as this is a reserved name for rgxlog.
    """

    def __init__(self, **kw):
        super().__init__()

    @assert_expected_node_structure
    def relation_name(self, relation_name_node: LarkNode):
        # get the name of the relation and check if it is not reserved (starts with '__rgxlog__')
        relation_name = relation_name_node.children[0]
        if relation_name.startswith("__rgxlog__"):
            raise Exception(f'encountered relation name: {relation_name}. '
                            f'names starting with __rgxlog__ are reserved')


class FixStrings(Visitor_Recursive):
    """
     Fixes the strings in the lark tree.
     Removes the line overflow escapes from strings
     """

    def __init__(self, **kw):
        super().__init__()

    @assert_expected_node_structure
    def string(self, string_node: LarkNode):
        # get and fix the string that is stored in the node
        cur_string_value = string_node.children[0]
        # remove line overflow escapes
        fixed_string_value = cur_string_value.replace('\\\n', '')

        # replace the string that is stored in the node with the fixed string
        string_node.children[0] = fixed_string_value


class ConvertSpanNodesToSpanInstances(Visitor_Recursive):
    """
    Converts each span node in the ast to a span instance.
    This means that a span in the tree will be represented by a single value (a "DataTypes.Span" instance)
    instead of two integer nodes, making it easier to work with (as other data types are also represented by
    a single value).
    """

    def __init__(self, **kw):
        super().__init__()

    @assert_expected_node_structure
    def span(self, span_node: LarkNode):
        # get the span start and end
        span_start = span_node.children[0].children[0]
        span_end = span_node.children[1].children[0]

        # replace the current representation of the span in the ast with a matching Span instance
        span_node.children = [Span(span_start, span_end)]


class ConvertStatementsToStructuredNodes(Visitor_Recursive):
    """
    converts each statement node in the tree to a structured node, making it easier to parse in future passes.
    a structured node is a class representation of a node in the abstract syntax tree.
    note that after using this pass, non statement nodes will no longer appear in the tree, so passes that
    should work on said nodes need to be used before this pass in the passes pipeline (e.g. FixString)
    """

    def __init__(self, **kw):
        super().__init__()

    @assert_expected_node_structure
    def assignment(self, assignment_node: LarkNode):

        # get the attributes that defines this assignment: the variable name, the assigned value and the
        # assigned value type
        var_name_node = assignment_node.children[0]
        value_node = assignment_node.children[1]
        var_name = var_name_node.children[0]
        value = value_node.children[0]
        value_type = DataTypes.from_string(value_node.data)

        # create the structured node and use it as a replacement for the current assignment representation
        structured_assignment_node = Assignment(var_name, value, value_type)
        assignment_node.children = [structured_assignment_node]

    @assert_expected_node_structure
    def read_assignment(self, assignment_node: LarkNode):

        # get the attributes that defines this read assignment: the variable name, the argument for the read function
        # and its type
        var_name_node = assignment_node.children[0]
        read_arg_node = assignment_node.children[1]
        var_name = var_name_node.children[0]
        read_arg = read_arg_node.children[0]
        read_arg_type = DataTypes.from_string(read_arg_node.data)

        # create the structured node and use it as a replacement for the current assignment representation
        structured_assignment_node = ReadAssignment(var_name, read_arg, read_arg_type)
        assignment_node.children = [structured_assignment_node]

    @assert_expected_node_structure
    def add_fact(self, fact_node: LarkNode):

        # a fact is defined by a relation, create that relation using the utility function
        relation = self.__create_structured_relation_node(fact_node)

        # create a structured node and use it to replace the current fact representation
        structured_fact_node = AddFact(relation.relation_name, relation.term_list, relation.type_list)
        fact_node.children = [structured_fact_node]

    @assert_expected_node_structure
    def remove_fact(self, fact_node: LarkNode):

        # a fact is defined by a relation, create that relation using the utility function
        relation = self.__create_structured_relation_node(fact_node)

        # create a structured node and use it to replace the current fact representation
        structured_fact_node = RemoveFact(relation.relation_name, relation.term_list, relation.type_list)
        fact_node.children = [structured_fact_node]

    @assert_expected_node_structure
    def query(self, query_node: LarkNode):

        # a query is defined by a relation, create that relation using the utility function
        relation = self.__create_structured_relation_node(query_node)

        # create a structured node and use it to replace the current query representation
        structured_query_node = Query(relation.relation_name, relation.term_list, relation.type_list)
        query_node.children = [structured_query_node]

    @assert_expected_node_structure
    def relation_declaration(self, relation_decl_node: LarkNode):
        relation_name_node = relation_decl_node.children[0]
        decl_term_list_node = relation_decl_node.children[1]

        # get the attributes of the relation declaration: the declared relation name and the types of its terms
        relation_name = relation_name_node.children[0]
        type_list = []
        for decl_term_node in decl_term_list_node.children:
            decl_term_type = decl_term_node.data
            if decl_term_type == "decl_string":
                type_list.append(DataTypes.string)
            elif decl_term_type == "decl_span":
                type_list.append(DataTypes.span)
            elif decl_term_type == "decl_int":
                type_list.append(DataTypes.int)
            else:
                raise Exception(f'unexpected declaration term node type: {decl_term_type}')

        # create a structured node and use it to replace the current relation declaration representation
        relation_decl_struct_node = RelationDeclaration(relation_name, type_list)
        relation_decl_node.children = [relation_decl_struct_node]

    @assert_expected_node_structure
    def rule(self, rule_node: LarkNode):
        rule_head_node = rule_node.children[0]
        rule_body_relation_nodes = rule_node.children[1]

        # create the structured relation node that defines the head relation of the rule
        structured_head_relation_node = self.__create_structured_relation_node(rule_head_node)

        # for each rule body relation, create a matching structured relation node
        structured_body_relation_list = []
        for relation_node in rule_body_relation_nodes.children:

            relation_type = relation_node.data
            if relation_type == "relation":
                structured_relation_node = self.__create_structured_relation_node(relation_node)
            elif relation_type == "ie_relation":
                structured_relation_node = self.__create_structured_ie_relation_node(relation_node)
            else:
                raise Exception(f'unexpected relation type: {relation_type}')

            structured_body_relation_list.append(structured_relation_node)

        # create a list of the types of the relations in the rule body
        body_relation_type_list = [relation_node.data for relation_node in rule_body_relation_nodes.children]

        # create a structured rule node
        structured_rule_node = Rule(structured_head_relation_node, structured_body_relation_list,
                                    body_relation_type_list)

        # replace the current rule representation with the structured rule node
        rule_node.children = [structured_rule_node]

    @staticmethod
    def __create_structured_relation_node(relation_node: LarkNode) -> Relation:
        """
        an utility function that constructs a structured relation node.
        while a relation node isn't a statement in and of itself, it is useful for defining
        a structured rule node (which is constructed from multiple relations).
        This is also a useful method for getting the attributes of a relation that defines a fact or a query
        (as facts and queries are actions that are defined by a relation)

        Args:
            relation_node: a lark node that is structured like a relation (e.g. relation, add_fact, query)

        Returns: a structured node that represents the relation (structured_nodes.Relation instance)
        """
        relation_name_node = relation_node.children[0]
        term_list_node = relation_node.children[1]

        # get the attributes that define a relation: its name, its terms, and the type of its terms
        relation_name = relation_name_node.children[0]
        term_list = [term_node.children[0] for term_node in term_list_node.children]
        type_list = [DataTypes.from_string(term_node.data) for term_node in term_list_node.children]

        # create a structured relation node and return it
        structured_relation_node = Relation(relation_name, term_list, type_list)
        return structured_relation_node

    @staticmethod
    def __create_structured_ie_relation_node(ie_relation_node: LarkNode) -> IERelation:
        """
        an utility function that constructs a structured ie relation node.
        while an ie relation node isn't a statement in and of itself, it is useful for defining
        a structured rule node (which is constructed from multiple relations which may include ie relations).

        Args:
            ie_relation_node: an ie_relation lark node

        Returns: a structured node that represents the ie relation (a structured_nodes.IERelation instance)
        """
        relation_name_node = ie_relation_node.children[0]
        input_term_list_node = ie_relation_node.children[1]
        output_term_list_node = ie_relation_node.children[2]

        # get the name of the ie relation
        relation_name = relation_name_node.children[0]

        # get the input terms of the ie relation and their types
        input_term_list = [term_node.children[0] for term_node in input_term_list_node.children]
        input_type_list = [DataTypes.from_string(term_node.data) for term_node in input_term_list_node.children]

        # get the output terms of the ie relation and their types
        output_term_list = [term_node.children[0] for term_node in output_term_list_node.children]
        output_type_list = [DataTypes.from_string(term_node.data) for term_node in output_term_list_node.children]

        # create a structured ie relation node and return it
        structured_ie_relation_node = IERelation(relation_name, input_term_list, input_type_list,
                                                 output_term_list, output_type_list)
        return structured_ie_relation_node


class CheckDefinedReferencedVariables(Interpreter):
    """
    A lark tree semantic check.
    checks whether each variable reference refers to a defined variable.
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def __check_if_var_is_defined(self, var_name):
        """
        an utility function that checks if a variable is a defined variable in the symbol table
        if not, raises an exception

        Args:
            var_name: the name of the variable that will be checked
        """
        if not self.symbol_table.contains_variable(var_name):
            raise Exception(f'variable "{var_name}" is not defined')

    def __check_if_vars_in_list_are_defined(self, term_list, type_list):
        """
        an utility function that checks if the non free variables in a term list are defined
        if one of them is not defined, raises an exception

        Args:
            term_list: a list of terms
            type_list: the type of terms in term_list
        """
        for term, term_type in zip(term_list, type_list):
            if term_type is DataTypes.var_name:
                # found a variable, check if it is defined
                self.__check_if_var_is_defined(term)

    @unravel_lark_node
    def assignment(self, assignment: Assignment):
        if assignment.value_type is DataTypes.var_name:
            # the assigned expression is a variable, check if it is defined
            self.__check_if_var_is_defined(assignment.value)

    @unravel_lark_node
    def read_assignment(self, assignment: ReadAssignment):
        if assignment.read_arg_type is DataTypes.var_name:
            # a variable is used as the argument for read(), check if it is defined
            self.__check_if_var_is_defined(assignment.read_arg)

    @unravel_lark_node
    def add_fact(self, fact: AddFact):
        self.__check_if_vars_in_list_are_defined(fact.term_list, fact.type_list)

    @unravel_lark_node
    def remove_fact(self, fact: RemoveFact):
        self.__check_if_vars_in_list_are_defined(fact.term_list, fact.type_list)

    @unravel_lark_node
    def query(self, query: Query):
        self.__check_if_vars_in_list_are_defined(query.term_list, query.type_list)

    @unravel_lark_node
    def rule(self, rule: Rule):

        # for each relation in the rule body, check if its variable terms are defined
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            if relation_type == "relation":
                self.__check_if_vars_in_list_are_defined(relation.term_list, relation.type_list)
            elif relation_type == "ie_relation":
                # ie relations have input terms and output terms, check them both
                self.__check_if_vars_in_list_are_defined(relation.input_term_list, relation.input_type_list)
                self.__check_if_vars_in_list_are_defined(relation.output_term_list, relation.output_type_list)
            else:
                raise Exception(f'unexpected relation type: {relation_type}')


class CheckForRelationRedefinitions(Interpreter):
    """
    A lark tree semantic check.
    checks if a relation is being redefined, and raises an exception if this is the case.
    relations can be defined either by a relation declaration or by appearing in a rule head
    """
    """
    TODO: in a future version of rgxlog we might want to allow for a rule head to be "redefined", meaning
    a relation could be defined by multiple rule heads, allowing for recursion. 
    This would mean changing this pass as it does not allow a relation to appear in multiple rule heads.
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def __check_if_relation_is_already_defined(self, relation_name):
        """
        an utility function that checks if a relation is already defined and raises an exception
        if it does.

        Args:
            relation_name: the relation name to be checked for redefinition
        """
        if self.symbol_table.contains_relation(relation_name):
            raise Exception(f'relation "{relation_name}" is already defined. relation redefinitions are not allowed')

    @unravel_lark_node
    def relation_declaration(self, relation_decl: RelationDeclaration):
        self.__check_if_relation_is_already_defined(relation_decl.relation_name)

    @unravel_lark_node
    def rule(self, rule: Rule):
        """
        a rule is a definition of the relation that appears in the rule head.
        this function checks that the relation that appears in the rule head is not being redefined.
        """
        self.__check_if_relation_is_already_defined(rule.head_relation.relation_name)


class CheckReferencedRelationsExistenceAndArity(Interpreter):
    """
    A lark tree semantic check.
    Checks whether each normal relation (that is not an ie relation) reference refers to a defined relation.
    Also checks if the relation reference uses the correct arity.
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def __check_relation_exists_and_correct_arity(self, relation: Relation):
        """
        An utility function that checks if a relation exists in the symbol table
        and if the correct arity was used

        Args:
            relation: the relation that will be checked.
        """

        # get the relation name and the arity that was used by the user
        relation_name = relation.relation_name
        used_arity = len(relation.term_list)

        # check if the relation exists using the symbol table
        if not self.symbol_table.contains_relation(relation_name):
            raise Exception(f'relation "{relation_name}" is not defined')

        # at this point we know the relation exists but we still need to check that the correct arity was used
        # get the correct arity
        relation_schema = self.symbol_table.get_relation_schema(relation_name)
        correct_arity = len(relation_schema)

        # check if that arity that was used is correct
        if used_arity != correct_arity:
            raise Exception(f'relation "{relation_name}" was referenced with an incorrect arity: {used_arity}. The'
                            f'correct arity is: {correct_arity}')

    @unravel_lark_node
    def query(self, query: Query):
        # a query is defined by a relation reference, so we can simply use the utility function
        self.__check_relation_exists_and_correct_arity(query)

    @unravel_lark_node
    def add_fact(self, fact: AddFact):
        # a fact is defined by a relation reference, so we can simply use the utility function
        self.__check_relation_exists_and_correct_arity(fact)

    @unravel_lark_node
    def remove_fact(self, fact: RemoveFact):
        # a fact is defined by a relation reference, so we can simply use the utility function
        self.__check_relation_exists_and_correct_arity(fact)

    @unravel_lark_node
    def rule(self, rule: Rule):
        """
        a rule is a definition of the relation in the rule head. Therefore the rule head reference does not
        need to be checked.
        The rule body references relations that should already exist. Those will be checked in this method.
        """

        # check that each normal relation in the rule body exists and that the correct arity was used
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            if relation_type == "relation":
                self.__check_relation_exists_and_correct_arity(relation)


class CheckReferencedIERelationsExistenceAndArity(Visitor_Recursive):
    """
    A lark tree semantic check.
    Checks whether each ie relation reference refers to a defined ie function.
    Also checks if the correct input arity and output arity for the ie function were used.

    currently, an ie relation can only be found in a rule's body, so this is the only place where this
    check will be performed
    """

    def __init__(self, **kw):
        super().__init__()

    @unravel_lark_node
    def rule(self, rule: Rule):

        # for each ie relation in the rule body, check its existence and arity
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            if relation_type == "ie_relation":

                # get the name of the ie function, it is the same as the name of the ie relation
                ie_func_name = relation.relation_name
                try:
                    # get the data of the ie function
                    ie_function_data = getattr(ie_functions, ie_func_name)
                except Exception:
                    # couldn't find the ie function, raise an exception
                    raise Exception(f'the information extraction function "{ie_func_name}" does not exist')

                # the ie function exists, check if the correct input arity was used
                used_input_arity = len(relation.input_term_list)
                correct_input_arity = len(ie_function_data.get_input_types())
                if used_input_arity != correct_input_arity:
                    raise Exception(f'used incorrect input arity for ie function "{ie_func_name}":'
                                    f' {used_input_arity} (should be {correct_input_arity})')

                # check if the correct output arity was used
                used_output_arity = len(relation.output_term_list)
                correct_output_arity = len(ie_function_data.get_output_types(used_output_arity))
                if used_output_arity != correct_output_arity:
                    raise Exception(f'used incorrect output arity for ie function {ie_func_name}:'
                                    f' {used_output_arity} (should be {correct_output_arity})')


class CheckRuleSafety(Visitor_Recursive):
    """
    A lark tree semantic check.
    checks whether the rules in the programs are safe.

    For a rule to be safe, two conditions must apply:

    1. Every free variable in the head occurs at least once in the body as an output term of a relation.

    examples:
    a. "parent(X,Y) <- son(X)" is not a safe rule because the free variable Y only appears in the rule head.
    b. "parent(X,Z) <- parent(X,Y), parent(Y,Z)" is a safe rule as both X,Z that appear in the rule head, also
        appear in the rule body.
    c. "happy(X) <- is_happy<X>(Y)" is not a safe rule as X does not appear as an output of a relation.

    2. Every free variable is bound.
    A bound free variable is a free variable that has a constraint that imposes a
    limit on the amount of values it can take.

    In order to check that every free variable is bound, we will check that every relation in the rule body
    is a safe relation, meaning:
    a. A safe relation is one where its input relation is safe, meaning all its input's free variables are bound.
    normal relations are always safe as they don't have an input relation.
    b. A bound variable is one that exists in the output of a safe relation.

    examples:
    a. "rel2(X,Y) <- rel1(X,Z),ie1<X>(Y)" is safe as the only input free variable, X, exists in the output of
    the safe relation rel1(X,Z).
    b. " rel2(Y) <- ie1<Z>(Y)" is not safe as the input free variable Z does not exist in the output of any
    safe relation.
    """

    def __init__(self, **kw):
        super().__init__()

    @unravel_lark_node
    def rule(self, rule: Rule):
        head_relation = rule.head_relation
        body_relation_list = rule.body_relation_list
        body_relation_type_list = rule.body_relation_type_list

        # check condition 1:
        # every free variable in the head occurs at least once in the body as an output term of a relation.

        # get the free variables in the rule head
        rule_head_free_vars = get_set_of_free_var_names(head_relation.term_list, head_relation.type_list)

        # get the free variables in the rule body that serve as output terms.
        rule_body_output_free_var_sets = [get_set_of_output_free_var_names(relation, relation_type)
                                          for relation, relation_type in
                                          zip(body_relation_list, body_relation_type_list)]
        rule_body_output_free_vars = set().union(*rule_body_output_free_var_sets)

        # make sure that every free variable in the rule head appears at least once as an output term
        # in the rule body
        bad_rule_head_free_vars = rule_head_free_vars.difference(rule_body_output_free_vars)
        if bad_rule_head_free_vars:
            raise Exception(f'The rule "{rule}" \n'
                            f'is not safe because the following free variables appear in the '
                            'rule head but not as output terms in the rule body:\n'
                            f'{bad_rule_head_free_vars}')

        # check condition 2:
        # every free variable is bound.
        # we will do this by checking that all of the rule body relations are safe.

        # use a fix point iteration algorithm to find if all the relations are safe:
        # a. iterate over all of the rule body relations and check if they are safe, meaning all their input
        # free variable terms are bound.
        # b. if a new safe relation was found, mark its output free variables as bound, and the relation as safe.
        # c. repeat step 'a' until all relations were found to be safe relations (success condition),
        # or no new safe relations were found (failure condition).

        # initialize assuming every relation is unsafe and every free variable is unbound
        safe_relations = set()
        bound_free_vars = set()
        found_new_safe_relation = False
        all_relations_are_safe = False
        first_pass = True

        while first_pass or (found_new_safe_relation and not all_relations_are_safe):
            first_pass = False
            found_new_safe_relation = False

            # try to find new safe relations
            for relation, relation_type in zip(body_relation_list, body_relation_type_list):
                if relation not in safe_relations:
                    # this relation was not marked as safe yet.
                    # check if all of its input free variable terms are bound
                    input_free_vars = get_set_of_input_free_var_names(relation, relation_type)
                    unbound_input_free_vars = input_free_vars.difference(bound_free_vars)
                    if not unbound_input_free_vars:
                        # all input free variables are bound, mark the relation as safe
                        safe_relations.add(relation)
                        # mark the relation's output free variables as bound
                        output_free_vars = get_set_of_output_free_var_names(relation, relation_type)
                        bound_free_vars = bound_free_vars.union(output_free_vars)
                        # make sure we iterate over the relations again if not all of them were found
                        # to be safe
                        found_new_safe_relation = True
            # the pass was completed, check if all of the relations were found to be safe
            all_relations_are_safe = len(safe_relations) == len(body_relation_list)

        if not all_relations_are_safe:
            # condition 2 check failed, get all of the unbound free variables and pass them in an exception
            rule_body_input_free_var_sets = [get_set_of_input_free_var_names(relation, relation_type)
                                             for relation, relation_type in
                                             zip(body_relation_list, body_relation_type_list)]
            rule_body_input_free_vars = set().union(*rule_body_input_free_var_sets)
            unbound_free_vars = rule_body_input_free_vars.difference(bound_free_vars)
            raise Exception(f'The rule "{rule}" \n'
                            f'is not safe because the following free variables are not bound:\n'
                            f'{unbound_free_vars}')


class ReorderRuleBodyVisitor(Visitor_Recursive):
    """
    A lark tree optimization pass.
    Reorders each rule body relations list so that each relation in the list has its input free variables bound by
    previous relations in the list, or it has no input free variables terms.
    for example: the rule "B(Z) <- RGX(X,Y)->(Z), A(X), A(Y)"
           will change to "B(Z) <- A(X), A(Y), RGX(X,Y)->(Z)"
    This way it is possible to easily compute the rule body relations from the start of the list to its end.
    for more details on the execution of rules see execution.NetworkxExecution
    """

    def __init__(self, **kw):
        super().__init__()

    @unravel_lark_node
    def rule(self, rule: Rule):

        # in order to reorder the relations, we will use the same algorithm from the CheckRuleSafety pass.
        # when a safe relation is found, it will be inserted into a list. This way, an order in which each
        # relation's input free variables are bound by previous relations in the list is found.

        # use a fix point iteration algorithm to find a correct order:
        # a. iterate over all of the rule body relations and check if they are safe, meaning all their input
        # free variable terms are bound by the current relations in the reordered list
        # (or they have no input free variables).
        # b. if a new safe relation was found, mark its output free variables as bound, and add the relation
        # to the list
        # c. repeat step 'a' until all relations were found to be safe relations,
        # or no new safe relations were found.
        # d. replace the original rule body relations list with the reordered list

        # initialize assuming every relation is unsafe and every free variable is unbound
        reordered_relations_list = []
        reordered_relations_type_list = []  # note that this we also need to update the type list of the relations
        bound_free_vars = set()
        found_new_safe_relation = False
        all_relations_were_reordered = False
        first_pass = True

        while first_pass or (found_new_safe_relation and not all_relations_were_reordered):
            first_pass = False
            found_new_safe_relation = False

            # try to find new safe relations
            for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
                if relation not in reordered_relations_list:
                    # this relation was not marked as safe yet.
                    # check if all of its input free variable terms are bound
                    input_free_vars = get_set_of_input_free_var_names(relation, relation_type)
                    unbound_input_free_vars = input_free_vars.difference(bound_free_vars)
                    if not unbound_input_free_vars:
                        # all input free variables are bound, mark the relation as safe by adding it to the reordered
                        # list. also save its type.
                        reordered_relations_list.append(relation)
                        reordered_relations_type_list.append(relation_type)
                        # mark the relation's output free variables as bound
                        output_free_vars = get_set_of_output_free_var_names(relation, relation_type)
                        bound_free_vars = bound_free_vars.union(output_free_vars)
                        # make sure we iterate over the relations again if not all of them were found
                        # to be safe
                        found_new_safe_relation = True
            # the pass was completed, check if all of the relations were found to be safe (and thus were reordered)
            all_relations_were_reordered = len(reordered_relations_list) == len(rule.body_relation_list)

        if not all_relations_were_reordered:
            raise Exception(f'The rule "{rule}"\n'
                            f'is not safe. This pass assumes its input rule is safe, '
                            f'so make sure to check for rule safety before using it')

        # replace the current relation list with the reordered relation list
        rule.body_relation_list = reordered_relations_list
        rule.body_relation_type_list = reordered_relations_type_list


class TypeCheckAssignments(Interpreter):
    """
    a lark semantic check
    performs type checking for assignments
    in the current version of lark, this type checking is only required for read assignments
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    @unravel_lark_node
    def read_assignment(self, assignment: ReadAssignment):

        # get the type of the argument for the read() function
        if assignment.read_arg_type is DataTypes.var_name:
            read_arg_var_name = assignment.read_arg
            read_arg_type = self.symbol_table.get_variable_type(read_arg_var_name)
        else:
            read_arg_type = assignment.read_arg_type

        # if the argument is not of type string, raise and exception
        if read_arg_type is not DataTypes.string:
            raise Exception(f'type checking failed for the read assignment {assignment}\n'
                            f'because the argument type for read() was {read_arg_type} (must be a string)')


class TypeCheckRelationsAndSaveSchemas(Interpreter):
    """
    A lark tree semantic check.
    This pass makes the following assumptions and might not work correctly if they are not met
    1. that relations and ie relations references and correct arity were checked.
    2. variable references were checked.
    3. it only gets a single statement as an input.

    this pass performs the following checks:
    1. checks if relation references are properly typed.
    2. checks if ie relations are properly typed.
    3. checks if free variables in rules do have conflicting types.

    example for the semantic check failing on check no. 3:
    new A(str)
    new B(int)
    C(X) <- A(X), B(X) # error since X is expected to be both an int and a string

    this pass also writes the relation schemas that it finds in relation declarations and rule heads to the
    symbol table
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def __type_check_term_list(self, term_list: list, type_list: list, correct_type_list: list):
        """
        check if the term list is properly typed.
        the term list could include free variables, this method will assume their actual type is correct.
        Args:
            term_list: the term list to be type checked
            type_list: the types of the terms in term_list
            correct_type_list: a list of the types that the terms must have to pass the type check

        Returns: True if the type check passed, else False
        """
        if len(term_list) != len(type_list) or len(term_list) != len(correct_type_list):
            raise Exception("the length of term_list, type_list and correct_type_list should be the same")

        # perform the type check
        for term, term_type, correct_type in zip(term_list, type_list, correct_type_list):
            if term_type is DataTypes.var_name:
                # current term is a variable, get its type from the symbol table and check if it is correct
                var_type = self.symbol_table.get_variable_type(term)
                if var_type != correct_type:
                    # the variable is not properly typed, the type check failed
                    return False
            elif term_type is not DataTypes.free_var_name and term_type != correct_type:
                # the term is a literal that is not properly typed, the type check failed
                return False
        # all variables are properly typed, the type check succeeded
        return True

    @unravel_lark_node
    def relation_declaration(self, relation_decl: RelationDeclaration):
        self.symbol_table.add_relation_schema(relation_decl.relation_name, relation_decl.type_list)

    @unravel_lark_node
    def add_fact(self, fact: AddFact):
        # get the schema of the referenced relation from the symbol table and perform a type check
        relation_schema = self.symbol_table.get_relation_schema(fact.relation_name)
        type_check_passed = self.__type_check_term_list(fact.term_list, fact.type_list, relation_schema)
        if not type_check_passed:
            raise Exception(f'type check failed for fact: "{fact}"')

    @unravel_lark_node
    def remove_fact(self, fact: RemoveFact):
        # get the schema of the referenced relation from the symbol table and perform a type check
        relation_schema = self.symbol_table.get_relation_schema(fact.relation_name)
        type_check_passed = self.__type_check_term_list(fact.term_list, fact.type_list, relation_schema)
        if not type_check_passed:
            raise Exception(f'type check failed for fact: "{fact}"')

    @unravel_lark_node
    def query(self, query: Query):
        # get the schema of the referenced relation from the symbol table and perform a type check
        relation_schema = self.symbol_table.get_relation_schema(query.relation_name)
        type_check_passed = self.__type_check_term_list(query.term_list, query.type_list, relation_schema)
        if not type_check_passed:
            raise Exception(f'type check failed for query: "{query}"')

    @staticmethod
    def __rule_free_vars_type_check_aux(term_list: list, type_list: list, correct_type_list: list,
                                        free_var_to_type: dict, conflicted_free_vars: set):
        """
        free variables in rules get their type from the relations in the rule body.
        it is possible for a free variable to be expected to be more than one type.
        for each free variable in term_list, this method will check for it's type, save it in
        free_var_to_type (for future calls), and check if it is expected to be more than one type.

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

    @unravel_lark_node
    def rule(self, rule: Rule):
        free_var_to_type = dict()
        conflicted_free_vars = set()

        # Look for conflicting free variables and improperly typed relations
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):

            if relation_type == "relation":
                # perform the type check
                relation_schema = self.symbol_table.get_relation_schema(relation.relation_name)
                type_check_passed = self.__type_check_term_list(
                    relation.term_list, relation.type_list, relation_schema)
                # check for conflicted free variables
                self.__rule_free_vars_type_check_aux(
                    relation.term_list, relation.type_list, relation_schema, free_var_to_type, conflicted_free_vars)

            elif relation_type == "ie_relation":
                # get the input and output schema of the ie function
                ie_func_name = relation.relation_name
                ie_func_data = getattr(ie_functions, ie_func_name)
                input_schema = ie_func_data.get_input_types()
                output_arity = len(relation.output_term_list)
                output_schema = ie_func_data.get_output_types(output_arity)
                # perform the type check
                input_type_check_passed = self.__type_check_term_list(
                    relation.input_term_list, relation.input_type_list, input_schema)
                output_type_check_passed = self.__type_check_term_list(
                    relation.output_term_list, relation.output_type_list, output_schema)
                type_check_passed = input_type_check_passed and output_type_check_passed
                # check for conflicting free variables
                self.__rule_free_vars_type_check_aux(relation.input_term_list, relation.input_type_list,
                                                     input_schema, free_var_to_type, conflicted_free_vars)
                self.__rule_free_vars_type_check_aux(relation.output_term_list, relation.output_type_list,
                                                     output_schema, free_var_to_type, conflicted_free_vars)

            else:
                raise Exception(f'unexpected relation type: {relation_type}')

            # raise an exception if the type check failed
            if not type_check_passed:
                raise Exception(f'type check failed for rule "{rule}"\n'
                                f'because the relation "{relation}"\n'
                                f'is not properly typed')

        # raise an exception if there are any free variables with conflicting types
        if conflicted_free_vars:
            raise Exception(f'type check failed for rule "{rule}"\n'
                            f'because the following free variables have conflicting types:\n'
                            f'{conflicted_free_vars}')

        # no issues were found, get the relation's head schema using the free variable to type mapping
        # and add it to the symbol table
        head_relation = rule.head_relation
        rule_head_schema = [free_var_to_type[term] for term in head_relation.term_list]
        self.symbol_table.add_relation_schema(head_relation.relation_name, rule_head_schema)


class ResolveVariablesReferences(Interpreter):
    """
    a lark execution pass
    this pass replaces variable references with their literal values.
    also replaces DataTypes.var_name types with the real type of the variable
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    @unravel_lark_node
    def assignment(self, assignment: Assignment):
        # if the assigned value is a variable, replace it with its literal value
        if assignment.value_type is DataTypes.var_name:
            assigned_var_name = assignment.value
            assignment.value = self.symbol_table.get_variable_value(assigned_var_name)
            assignment.value_type = self.symbol_table.get_variable_type(assigned_var_name)

    @unravel_lark_node
    def read_assignment(self, assignment: ReadAssignment):
        # if the read() argument is a variable, replace it with its literal value
        if assignment.read_arg_type is DataTypes.var_name:
            read_arg_var_name = assignment.read_arg
            assignment.read_arg = self.symbol_table.get_variable_value(read_arg_var_name)
            assignment.read_arg_type = self.symbol_table.get_variable_type(read_arg_var_name)

    def __resolve_variables_in_term_and_type_lists(self, term_list, type_list):
        """
        an utility function for resolving variables in term lists
        for each variable term in term_list, replace its value in term_list with its literal value, and
        its DataTypes.var_name type in type_list with its real type
        the changes to the lists are done in-place

        Args:
            term_list: a list of terms
            type_list: the type of terms in term_list
        """

        # get the list of terms with resolved variable values
        resolved_var_values_term_list = [
            self.symbol_table.get_variable_value(term) if term_type is DataTypes.var_name
            else term
            for term, term_type in zip(term_list, type_list)]

        # get the list of types with resolved variable types
        resolved_var_types_type_list = [
            self.symbol_table.get_variable_type(term) if term_type is DataTypes.var_name
            else term_type
            for term, term_type in zip(term_list, type_list)]

        # replace the lists with the resolved lists. use slicing to do it in-place.
        term_list[:] = resolved_var_values_term_list
        type_list[:] = resolved_var_types_type_list

    @unravel_lark_node
    def query(self, query: Query):
        self.__resolve_variables_in_term_and_type_lists(query.term_list, query.type_list)

    @unravel_lark_node
    def add_fact(self, fact: AddFact):
        self.__resolve_variables_in_term_and_type_lists(fact.term_list, fact.type_list)

    @unravel_lark_node
    def remove_fact(self, fact: RemoveFact):
        self.__resolve_variables_in_term_and_type_lists(fact.term_list, fact.type_list)

    @unravel_lark_node
    def rule(self, rule: Rule):
        # resolve the variables of each relation in the rule body relation list
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            if relation_type == "relation":
                self.__resolve_variables_in_term_and_type_lists(relation.term_list, relation.type_list)
            elif relation_type == "ie_relation":
                # ie relations have two term lists (input and output), resolve them both
                self.__resolve_variables_in_term_and_type_lists(relation.input_term_list, relation.input_type_list)
                self.__resolve_variables_in_term_and_type_lists(relation.output_term_list, relation.output_type_list)
            else:
                raise Exception(f'unexpected relation type: {relation_type}')


class ExecuteAssignments(Interpreter):
    """
    a lark execution pass
    executes assignments by saving variables' values and types in the symbol table
    should be used only after variable references are resolved, meaning the assigned values and read() arguments
    are guaranteed to be literals
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    @unravel_lark_node
    def assignment(self, assignment: Assignment):
        # perform the assignment by saving the variable attributes in the symbol table
        self.symbol_table.set_variable_value_and_type(assignment.var_name, assignment.value, assignment.value_type)

    @unravel_lark_node
    def read_assignment(self, assignment: ReadAssignment):

        # try to read the file and get its content as a single string. this string is the assigned value.
        try:
            file = open(assignment.read_arg, 'r')
            assigned_value = file.read()
            file.close()
        except Exception:
            raise Exception(f'could not open file "{assignment.read_arg}"')

        # perform the assignment by saving the variable attributes in the symbol table
        # note that since this is a read assignment, the type of the variable will always be a string
        self.symbol_table.set_variable_value_and_type(assignment.var_name, assigned_value, DataTypes.string)


class AddStatementsToNetxTermGraph(Interpreter):
    """
    a lark execution pass.
    This pass adds each statement in the input parse tree to the term graph.
    This pass is made to work with execution.NetworkxExecution as the execution engine and
    term_graph.NetxTermGraph as the term graph.

    Each statement in the term graph will be a child of the term graph's root.

    each statement in the term graph will have a type attribute that contains the statement's name in the
    rgxlog grammar.

    some nodes in the term graph will contain a value attribute that would contain a relation that describes
    that statement.
    e.g. a add_fact node would have a value which is a structured_nodes.AddFact instance
    (which inherits from structured_nodes.Relation) that describes the fact that will be added.

    Some statements are more complex and will be described by more than a single node, e.g. a rule node.
    The reason for this is that we want a single netx node to not contain more than one Relation
    (or IERelation) instance. This will make the term graph a "graph of relation nodes", allowing
     for flexibility for optimization in the future.
    """

    def __init__(self, **kw):
        super().__init__()
        self.term_graph = kw['term_graph']

    def __add_statement_to_term_graph(self, statement_type, statement_value):
        """
        An utility function that adds a statement to the term graph, meaning it adds a node that
        represents the statement to the term graph, then attach the node to the term graph's root.
        Should only be used for simple statements (i.e. can be described by a single node)

        Args:
            statement_type: the type of the statement, (e.g. add_fact). should be the same as the statement's
            name in the grammar. Will be set as the node's type attribute.
            statement_value: will be set as the value attribute of the node.
        """
        new_statement_node = self.term_graph.add_term(type=statement_type, value=statement_value)
        self.term_graph.add_dependency_edge(self.term_graph.get_root_id(), new_statement_node)

    @unravel_lark_node
    def add_fact(self, fact: AddFact):
        self.__add_statement_to_term_graph("add_fact", fact)

    @unravel_lark_node
    def remove_fact(self, fact: RemoveFact):
        self.__add_statement_to_term_graph("remove_fact", fact)

    @unravel_lark_node
    def query(self, query: Query):
        self.__add_statement_to_term_graph("query", query)

    @unravel_lark_node
    def relation_declaration(self, relation_decl: RelationDeclaration):
        self.__add_statement_to_term_graph("relation_declaration", relation_decl)

    @unravel_lark_node
    def rule(self, rule: Rule):
        # create the root of the rule statement in the term graph. Note that this is an "empty" node (it does
        # not contain a value). This is because the rule statement will be defined by the children of this node.
        tg_rule_node = self.term_graph.add_term(type="rule")
        # attach the rule node to the term graph root
        self.term_graph.add_dependency_edge(self.term_graph.get_root_id(), tg_rule_node)

        # create the rule head node for the term graph.
        # since a rule head is defined by a single relation, this node will contain a value which is that relation.
        tg_head_relation_node = self.term_graph.add_term(type="rule_head", value=rule.head_relation)
        # attach the rule head node to the rule statement node
        self.term_graph.add_dependency_edge(tg_rule_node, tg_head_relation_node)

        # create the rule body node. Unlike the rule head node, we can't define the rule body node
        # with a single value since a rule body can be defined by multiple relations.
        # Instead, each of the rule body relations will be represented by a term graph node
        # that is a child of the rule body node.
        tg_rule_body_node = self.term_graph.add_term(type="rule_body")
        # attach the rule body node to the rule statement node
        self.term_graph.add_dependency_edge(tg_rule_node, tg_rule_body_node)

        # add each rule body relation to the graph as a child node of the rule body node.
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            # add the relation to the term graph
            tg_body_relation_node = self.term_graph.add_term(type=relation_type, value=relation)
            # attach the relation to the rule body
            self.term_graph.add_dependency_edge(tg_rule_body_node, tg_body_relation_node)
