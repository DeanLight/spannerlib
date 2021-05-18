"""
this module contains the implementations of symbol tables
"""

from abc import ABC, abstractmethod

from rgxlog.engine.ie_functions.ie_function_base import IEFunction
from typing import Iterable, Dict


class SymbolTableBase(ABC):
    """
    An abstraction for a symbol table.
    the symbol table keeps track of:
    1. the variables that were defined in the program, their types and their values
    2. the relations that were defined in the program and their schemas
    3. the information extraction functions that were registered in the program and their data
    """

    @abstractmethod
    def set_var_value_and_type(self, var_name, var_value, var_type):
        """
        set the type and value of a variable in the symbol table

        Args:
            var_name: the name of the variable
            var_value: the value of the variable
            var_type: the type of the variable
        """
        pass

    @abstractmethod
    def get_variable_type(self, var_name):
        """
        Args:
            var_name: a variable name

        Returns: the variable's type
        """
        pass

    @abstractmethod
    def get_variable_value(self, var_name):
        """
        Args:
            var_name: a variable name

        Returns: the variable's value
        """
        pass

    @abstractmethod
    def get_all_variables(self):
        """
        Returns: an iterable that contains tuples of the format (variable name, variable type, variable value)
        for each variable in the symbol table
        """
        pass

    @abstractmethod
    def contains_variable(self, var_name):
        """
        Args:
            var_name: a variable name

        Returns: true if the variable is in the symbol table, else false
        """
        pass

    @abstractmethod
    def add_relation_schema(self, relation_name, schema, is_rule: bool):
        """
        add a new relation schema to the symbol table
        trying to add two schemas for the same relation will result in an exception as relation redefinitions
        are not allowed

        Args:
            relation_name: the relation's name
            schema: the relation's schema
            is_rule: true if rule false if relation
        """
        pass

    @abstractmethod
    def get_relation_schema(self, relation_name):
        """
        Args:
            relation_name: a relation name

        Returns: the relation's schema
        """
        pass

    @abstractmethod
    def get_all_relations(self):
        """
        Returns: an iterable that contains tuples of the format (relation name, relation schema)
        for each relation in the symbol table
        """
        pass

    @abstractmethod
    def contains_relation(self, relation_name):
        """
        Args:
            relation_name: a relation name

        Returns: true if the relation exists in the symbol table, else false
        """
        pass

    @abstractmethod
    def register_ie_function(self, ie_function, ie_function_name, in_rel, out_rel):
        """
        add a new ie function to the symbol table

        Args:
            explained in IEFunction class.
        """
        pass

    @abstractmethod
    def contains_ie_function(self, ie_func_name):
        """
        Args:
            ie_func_name: a name of an information extraction function

        Returns: true if the ie function exists in the symbol table, else false
        """
        pass

    @abstractmethod
    def get_ie_func_data(self, ie_func_name):
        """
        Args:
            ie_func_name: a name of an information extraction function

        Returns: the ie function's data (see ie_function_base.IEFunctionData for more information on
        ie function data instances)
        """
        pass

    @abstractmethod
    def get_all_registered_ie_funcs(self):
        """
        Returns: an iterable containing the names of all of the ie functions that are registered in the symbol table
        """
        pass

    def register_predefined_ie_functions(self, ie_funcs: Iterable[Dict]):
        """
        Adds to symbol table all the predefined ie functions.

        Args:
            ie_funcs: iterable of the predined ie functions in dict format
        """
        for ie_func in ie_funcs:
            self.register_ie_function(**ie_func)

    @abstractmethod
    def print_registered_ie_functions(self):
        """
            Prints information about the registered ie functions.
        """
        pass

    @abstractmethod
    def remove_ie_function(self, name: str):
        """
        removes a function from the symbol table

        Args:
            name: the name of the ie function to remove
        """

    def remove_all_ie_functions(self):
        """
        removes all the ie functions from the symbol table
        """

    def __str__(self):
        """
        Returns: a string representation of the symbol table for debugging purposes
        """

        # we will build the string incrementally using the string buffer
        string_buffer = list()

        # add the header of the variables table
        string_buffer.append('Variable\tType\tValue\n')
        # add the tuples of the variables table
        for name, var_type, var_value in self.get_all_variables():
            string_buffer.append(f'{name}\t{var_type}\t{var_value}\n')

        # add the header of the relation schemas table
        string_buffer.append('\nRelation\tSchema\n')
        # add the tuples of the relations schemas table
        for relation_name, type_list in self.get_all_relations():
            type_strings = [str(term_type) for term_type in type_list]
            type_list_string = ", ".join(type_strings)
            string_buffer.append(f"{relation_name}\t({type_list_string})\n")

        # add the header of the ie functions list
        string_buffer.append('\nregistered information extraction functions:\n')
        # add the ie functions
        for ie_func_name in self.get_all_registered_ie_funcs():
            string_buffer.append(f'{ie_func_name}\n')

        # combine the resulting tables to one string and return them
        symbol_table_string = ''.join(string_buffer)
        return symbol_table_string


class SymbolTable(SymbolTableBase):
    def __init__(self):
        self._var_to_value = {}
        self._var_to_type = {}
        self._relation_to_schema = {}
        self._registered_ie_functions = {}
        self.rule_relations = set()

    def set_var_value_and_type(self, var_name, var_value, var_type):
        self._var_to_value[var_name] = var_value
        self._var_to_type[var_name] = var_type

    def get_variable_type(self, var_name):
        return self._var_to_type[var_name]

    def get_variable_value(self, var_name):
        return self._var_to_value[var_name]

    def get_all_variables(self):
        all_vars = []
        for var_name in self._var_to_type.keys():
            var_type = self._var_to_type[var_name]
            var_value = self._var_to_value[var_name]
            all_vars.append((var_name, var_type, var_value))
        return all_vars

    def contains_variable(self, var_name):
        return var_name in self._var_to_type

    def add_relation_schema(self, relation_name, schema, is_rule: bool):

        # rule can be defined multiple times with same head (unlike relation)
        if is_rule:
            err_msg = f'relation "{relation_name}" already has a different schema'
            # if the rule is already defined the current schema must be equal to the rule's schema
            if relation_name in self._relation_to_schema:
                # check that relation name was actually defines as a rule and not as a relation
                if relation_name not in self.rule_relations:
                    raise Exception(err_msg)
                if not self._relation_to_schema[relation_name] == schema:
                    raise Exception(err_msg)
                return

        else:  # relation definition
            # if the relation is already defined we can't redefine her
            if relation_name in self._relation_to_schema:
                raise Exception(f'relation "{relation_name}" already has a schema')

        self._relation_to_schema[relation_name] = schema
        if is_rule:
            self.rule_relations.add(relation_name)

    def get_relation_schema(self, relation_name):
        # TODO@niv: maybe add error checking here?
        return self._relation_to_schema[relation_name]

    def get_all_relations(self):
        return ((relation, schema) for relation, schema in self._relation_to_schema.items())

    def contains_relation(self, relation_name):
        return relation_name in self._relation_to_schema

    def register_ie_function(self, ie_function, ie_function_name, in_rel, out_rel):
        # check if ie_function_name is available.
        # if self.contains_ie_function(ie_function_name):
        #     raise Exception(f"""Already exists ie function named {ie_function_name}.\n
        #     {self._registered_ie_functions[ie_function_name].get_meta_data}""" )

        # initialize ie_function_data instance.
        # add a mapping between ie_function_name and ie_function_data instance.
        self._registered_ie_functions[ie_function_name] = IEFunction(ie_function, in_rel, out_rel)

    def register_ie_function_object(self, ie_function_object: IEFunction, ie_function_name):
        # check if ie_function_name is available.
        # if self.contains_ie_function(ie_function_name):
        #     raise Exception(f"""Already exists ie function named {ie_function_name}.\n
        #     {self._registered_ie_functions[ie_function_name].get_meta_data}""")

        # initialize ie_function_data instance.
        # add a mapping between ie_function_name and ie_function_data instance.
        self._registered_ie_functions[ie_function_name] = ie_function_object

    def contains_ie_function(self, ie_func_name):
        return ie_func_name in self._registered_ie_functions

    def get_ie_func_data(self, ie_func_name):
        if self.contains_ie_function(ie_func_name):
            return self._registered_ie_functions[ie_func_name]
        else:
            raise AttributeError(f"'{ie_func_name}' is not a registered function.")

    def get_all_registered_ie_funcs(self):
        return self._registered_ie_functions.copy()


    def remove_ie_function(self, name: str):
        if not self._registered_ie_functions.pop(name, None):
            raise Exception(f"IE function named {name} doesn't exist")

    def remove_all_ie_functions(self):
        self._registered_ie_functions = dict()

    def print_registered_ie_functions(self):
        for ie_function_name, ie_function_obj in self._registered_ie_functions.items():
            print(f'{ie_function_name}\n{ie_function_obj.get_meta_data}\n{ie_function_obj}\n{ie_function_obj.__doc__}\n\n')
