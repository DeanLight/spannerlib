"""
this module contains the implementations of symbol tables
"""

from abc import ABC, abstractmethod
import rgxlog.engine.ie_functions.python_regexes as global_ie_functions
import rgxlog.user_ie_functions as user_ie_module
from rgxlog.engine.ie_functions.ie_function_base import IEFunction
import rgxlog.engine.ie_functions as predefined_ie_funcs

import os
import inspect


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
    def add_relation_schema(self, relation_name, schema):
        """
        add a new relation schema to the symbol table
        trying to add two schemas for the same relation will result in an exception as relation redefinitions
        are not allowed

        Args:
            relation_name: the relation's name
            schema: the relation's schema
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
    def register_ie_function(self, ie_function, ie_function_name, in_rel, out_rel, is_super_user):
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

    @abstractmethod
    def register_predefined_ie_functions(self):
        """
        Adds to symbol table all the predefined ie functions.
        """
        pass

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
        self.register_predefined_ie_functions()

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

    def add_relation_schema(self, relation_name, schema):
        if relation_name in self._relation_to_schema:
            raise Exception(f'relation "{relation_name}" already has a schema')
        self._relation_to_schema[relation_name] = schema

    def get_relation_schema(self, relation_name):
        return self._relation_to_schema[relation_name]

    def get_all_relations(self):
        return ((relation, schema) for relation, schema in self._relation_to_schema.items())

    def contains_relation(self, relation_name):
        return relation_name in self._relation_to_schema

    def register_ie_function(self, ie_function, ie_function_name, in_rel, out_rel, is_super_user):
        # check if ie_function_name is available.
        if self.contains_ie_function(ie_function_name):
            raise Exception(f"Already exists ie function named {ie_function_name}.")

        # initialize ie_function_data instance.
        # add a mapping between ie_function_name and ie_function_data instance.
        self._registered_ie_functions[ie_function_name] = IEFunction(ie_function, in_rel, out_rel, is_super_user)
        return True

    def contains_ie_function(self, ie_func_name):
        return ie_func_name in self._registered_ie_functions

    def get_ie_func_data(self, ie_func_name):
        if self.contains_ie_function(ie_func_name):
            return self._registered_ie_functions[ie_func_name]
        else:
            raise AttributeError(f"'{ie_func_name}' is not a registered function.")

    def get_all_registered_ie_funcs(self):
        return self._registered_ie_functions.copy()

    def register_predefined_ie_functions(self):
        # ie_directory = os.path.dirname(predefined_ie_funcs.__file__)
        #
        # for filename in os.listdir(ie_directory):
        #     if filename.endswith('.py') and filename not in ['__init__.py', 'ie_function_base']:
        #         for name, obj in inspect.getmembers(f'{ie_directory}/{filename}'):
        #             if inspect.isclass(obj):
        #                 self._registered_ie_functions[name] = obj.__init__()  # is it possible?
        from rgxlog.engine.datatypes.primitive_types import DataTypes

        def rgx_string(text, regex_formula):
            import re
            """
            Args:
                text: The input text for the regex operation
                regex_formula: the formula of the regex operation

            Returns: tuples of strings that represents the results
            """
            compiled_rgx = re.compile(regex_formula)
            num_groups = compiled_rgx.groups
            for match in re.finditer(compiled_rgx, text):
                if num_groups == 0:
                    matched_strings = [match.group()]
                else:
                    matched_strings = [group for group in match.groups()]
                yield matched_strings

        def rgx_string_out_types(output_arity):
            return tuple([DataTypes.string] * output_arity)

        rgx_string_in_type = [DataTypes.string, DataTypes.string]
        self._registered_ie_functions['RGXString'] = IEFunction(rgx_string, rgx_string_in_type, rgx_string_out_types, False)
