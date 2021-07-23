"""
for each statement node in the rgxlog grammar, this module contains a matching class that can represent
that statement in the abstract syntax tree. classes representations for relations are also included.

these classes are useful as they represent a statement with a single instance, instead of a lark tree,
thus simplifying the code required for semantic checks and manipulations of the statement.
"""
from typing import List

from rgxlog.engine.datatypes.primitive_types import DataTypes


def get_term_list_string(term_list, type_list):
    """
    returns a string representation of the term list.
    quotes are added to string terms so they will not be confused with variables.

    @param term_list: the term list to be turned into a string
    @param type_list: the types of the terms in term_list

    @return: a string representation of the term list
    """
    terms_with_quoted_strings = [f'"{term}"' if term_type is DataTypes.string
                                 else str(term)
                                 for term, term_type in zip(term_list, type_list)]
    term_list_string = ', '.join(terms_with_quoted_strings)
    return term_list_string


# TODO: understand why this causes a bug (rule safety something)
# @dataclasses.dataclass(init=False)
class Relation:
    """a representation of a normal relation"""

    def __init__(self, relation_name, term_list, type_list):
        """
        @param relation_name: the name of the relation
        @param term_list: a list of the relation terms.
        @param type_list: a list of the relation term types.
        @raise Exception: if length of term list doesn't match the length of type list.
        """
        if len(term_list) != len(type_list):
            raise Exception(f"received different lengths of term_list ({len(term_list)}) "
                            f"and type_list ({len(type_list)})")
        self.relation_name = relation_name
        self.term_list = term_list
        self.type_list = type_list

    def __str__(self):
        term_list_string = get_term_list_string(self.term_list, self.type_list)
        relation_string = f"{self.relation_name}({term_list_string})"
        return relation_string


class IERelation:
    """
    a representation of an information extraction (ie) relation.
    An information extraction relation is different than a normal relation as it is constructed from
    the results of a call to an information extraction function.

    The ie relation instructs us on how to construct it:
    * its name is the ie function we need to call
    * its input term list represents a relation where each tuple is an argument list to call the ie function with.
    * its output term list represents a relation that filters the tuples that are returned from the ie function
    calls, and matches the values inside the tuples to free variables.
    """

    def __init__(self, relation_name, input_term_list, input_type_list, output_term_list, output_type_list):
        """
        @param relation_name: the name of the information extraction relation
        @param input_term_list: a list of the input terms for the ie function.
                                must be either literal values or free variables
        @param input_type_list: a list of the term types in input_term_list
        @param output_term_list: a list of the output terms for the ie function.
                                 must be either literal values or free variables
        @param output_type_list: a list of the term types in output_term_list
        @raise Exception: if lenght of in/out term list doesn't match length of in/out type_list.
        """
        if len(input_term_list) != len(input_type_list):
            raise Exception(f"received different lengths of input_term_list ({len(input_term_list)}) "
                            f"and input_type_list ({len(input_type_list)})")
        if len(output_term_list) != len(output_type_list):
            raise Exception(f"received different lengths of output_term_list ({len(output_term_list)}) "
                            f"and output_type_list ({len(output_type_list)})")
        self.relation_name = relation_name
        self.input_term_list = input_term_list
        self.output_term_list = output_term_list
        self.input_type_list = input_type_list
        self.output_type_list = output_type_list

    def __str__(self):
        input_term_list_string = get_term_list_string(self.input_term_list, self.input_type_list)
        output_term_list_string = get_term_list_string(self.output_term_list, self.output_type_list)
        ie_relation_string = f"{self.relation_name}({input_term_list_string}) -> ({output_term_list_string})"
        return ie_relation_string


class RelationDeclaration:
    """a representation of a relation_declaration statement"""

    def __init__(self, relation_name, type_list):
        """
        @param relation_name: the name of the relation
        @param type_list: a list of the types of the terms in the relation's tuples
        @raise Exception: if there is invalid term type in term list.
        """
        self.relation_name: str = relation_name
        self.type_list: List[DataTypes] = type_list

    def __str__(self):
        type_strings = []
        for term_type in self.type_list:
            if term_type is DataTypes.string:
                type_strings.append('str')
            elif term_type is DataTypes.span:
                type_strings.append('span')
            elif term_type is DataTypes.integer:
                type_strings.append('int')
            else:
                raise Exception(f"invalid term type ({term_type})")
        type_list_string = ', '.join(type_strings)
        relation_declaration_string = f"{self.relation_name}({type_list_string})"
        return relation_declaration_string


class AddFact(Relation):
    """
    a representation of an add_fact statement
    inherits from relation as a fact can be defined by a relation
    """

    def __init__(self, relation_name, term_list, type_list):
        """
        see documentation of Relation's __init__.
        """
        super().__init__(relation_name, term_list, type_list)


class RemoveFact(Relation):
    """
    a representation of a remove_fact statement
    inherits from relation as a fact can be defined by a relation
    """

    def __init__(self, relation_name, term_list, type_list):
        """
        see documentation of Relation's __init__.
        """
        super().__init__(relation_name, term_list, type_list)


class Query(Relation):
    """
    a representation of a query statement
    inherits from relation as a query can be defined by a relation
    """

    def __init__(self, relation_name, term_list, type_list):
        """
        see documentation of Relation's __init__.
        """
        super().__init__(relation_name, term_list, type_list)


class Rule:
    """
    a representation of a rule statement
    """

    def __init__(self, head_relation: Relation, body_relation_list, body_relation_type_list):
        """
        @param head_relation: the rule head, which is represented by a single relation
        @param body_relation_list: a list of the rule body relations
        @param body_relation_type_list: a list of the rule body relations types (e.g. "relation", "ie_relation")
        """
        self.head_relation = head_relation
        self.body_relation_list = body_relation_list
        self.body_relation_type_list = body_relation_type_list

    def __str__(self):
        # get the string of the head relation
        head_relation_string = str(self.head_relation)
        # get the string of the rule body
        body_relation_strings_list = [str(relation) for relation in self.body_relation_list]
        rule_body_string = ', '.join(body_relation_strings_list)
        # create the string of the rule and return it
        rule_string = f'{head_relation_string} <- {rule_body_string}'
        return rule_string


class Assignment:
    """
    a representation of an assignment statement
    """

    def __init__(self, var_name, value, value_type):
        """
        @param var_name: the variable name to be assigned a value
        @param value: the assigned value
        @param value_type: the assigned value's type
        """
        self.var_name = var_name
        self.value = value
        self.value_type = value_type

    def __str__(self):
        if self.value_type is DataTypes.string:
            # add quotes to a literal string value
            value_string = f'"{self.value}"'
        else:
            value_string = str(self.value)
        return f'{self.var_name} = {value_string}'


class ReadAssignment:
    """
    a representation of a read_assignment statement
    """

    def __init__(self, var_name, read_arg, read_arg_type):
        """
        @param var_name: the variable name to be assigned a value
        @param read_arg: the argument that is passed to the read() function (e.g. "some_file" in 's = read("some_file")')
        @param read_arg_type: the type of the argument that is passed to the read function
        """
        if read_arg_type not in [DataTypes.string, DataTypes.var_name]:
            raise Exception(
                f'the argument that was passed to the read() function has an unexpected type: {read_arg_type}')

        self.var_name = var_name
        self.read_arg = read_arg
        self.read_arg_type = read_arg_type

    def __str__(self):
        if self.read_arg_type is DataTypes.string:
            # add quotes to a literal string argument
            read_arg_string = f'"{self.read_arg}"'
        else:
            read_arg_string = str(self.read_arg)
        return f'{self.var_name} = read({read_arg_string})'
