"""
this module contains the implementations of symbol tables
"""

from abc import ABC, abstractmethod
import rgxlog.engine.ie_functions as global_ie_functions


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
    def register_ie_function(self, ie_function_name):
        """
        add a new ie function to the symbol table

        Args:
            ie_function_name: the function's name

        Returns: true if the function exists on the server, false otherwise
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

        Returns: the ie function's data (see ie_functions.IEFunctionData for more information on
        ie function data instances)
        """
        pass

    def __str__(self):
        """
        Returns: a string representation of the symbol table for debugging purposes
        """

        # create a string that represents the variable table
        var_table_headers = 'Variable\tType\tValue'
        var_table_tuple_strings = [f'{name}\t{var_type}\t{var_value}'
                                   for name, var_type, var_value in self.get_all_variables()]
        var_table_content = "\n".join(var_table_tuple_strings)
        var_table_string = f"{var_table_headers}\n{var_table_content}"

        # create a string that represents the relation table
        relation_table_headers = 'Relation\tSchema'
        relation_table_tuple_strings = []
        for relation_name, type_list in self.get_all_relations():
            type_strings = [str(term_type) for term_type in type_list]
            type_list_string = ", ".join(type_strings)
            cur_tuple_string = f"{relation_name}\t({type_list_string})"
            relation_table_tuple_strings.append(cur_tuple_string)
        relation_table_content = '\n'.join(relation_table_tuple_strings)
        relation_table_string = f"{relation_table_headers}\n{relation_table_content}"

        # combine the resulting tables to one string and return them
        symbol_table_string = f"\n{var_table_string}\n\n{relation_table_string}\n"
        return symbol_table_string


class SymbolTable(SymbolTableBase):
    def __init__(self):
        self._var_to_value = {}
        self._var_to_type = {}
        self._relation_to_schema = {}
        self._registered_ie_functions = set()

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

    def register_ie_function(self, ie_function_name):
        try:
            self.get_ie_func_data(ie_function_name)
        except AttributeError:  # ie function does not exist on the server
            return False

        self._registered_ie_functions.add(ie_function_name)
        return True

    def contains_ie_function(self, ie_func_name):
        return ie_func_name in self._registered_ie_functions

    def get_ie_func_data(self, ie_func_name):
        ie_func_data = getattr(global_ie_functions, ie_func_name)
        return ie_func_data
