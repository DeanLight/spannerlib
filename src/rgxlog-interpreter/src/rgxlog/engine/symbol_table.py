from abc import ABC, abstractmethod

"""TODO currently the rewrite is incomplete. we should decide first on whether we keep sending whole cells to 
the pipeline or instead interpret cell by cell"""


class SymbolTableBase(ABC):
    """
    An abstraction for a symbol table.
    The symbol table keeps track of the variables in the program, their types and their values.
    It also keeps track of the relation names that were defined in the program and their schemas.
    """

    @abstractmethod
    def set_variable_type(self, var_name, var_type):
        """set the type of a variable in the symbol table"""
        pass

    @abstractmethod
    def get_variable_type(self, var_name):
        """get the type of a variable in the symbol table"""
        pass

    @abstractmethod
    def set_variable_value(self, var_name, var_value):
        """set the value of a variable in the symbol table"""
        pass

    @abstractmethod
    def get_variable_value(self, var_name):
        """get the value of a variable in the symbol table"""
        pass

    @abstractmethod
    def remove_variable(self, var_name):
        """
        remove a variable from the symbol table. both its type and value will be removed
        silently ignore calls with variable
        """
        pass

    @abstractmethod
    def get_all_variables(self):
        # TODO
        pass

    @abstractmethod
    def contains_variable(self, var_name):
        # TODO
        """returns true if a variable exists in the symbol table"""
        pass

    @abstractmethod
    def set_relation_schema(self, relation_name, schema):
        """set the schema of a relation in the symbol table"""
        pass

    @abstractmethod
    def get_relation_schema(self, relation_name):
        """get the schema of a relation in the symbol table"""
        pass

    @abstractmethod
    def get_all_relations(self):
        # TODO
        pass

    @abstractmethod
    def contains_relation(self, relation_name):
        pass

    @abstractmethod
    def remove_relation(self, relation_name):
        pass

    def __str__(self):
        """
        returns a string representation of the symbol table for debugging purposes
        """

        # create a string that represents the variable table
        var_table_headers = 'Variable\tType\tValue'
        var_table_tuple_strings = [f'{name}\t{var_type.to_string()}\t{var_value}'
                                   for name, var_type, var_value in self.get_all_variables()]
        var_table_content = "\n".join(var_table_tuple_strings)
        var_table_string = f"{var_table_headers}\n{var_table_content}"

        # create a string that represents the relation table
        relation_table_headers = 'Relation\tSchema'
        relation_table_tuple_strings = []
        for relation_name, type_list in self.get_all_relations():
            type_strings = [term_type.to_string() for term_type in type_list]
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

    def set_variable_type(self, var_name, var_type):
        self._var_to_type[var_name] = var_type

    def get_variable_type(self, var_name):
        return self._var_to_type[var_name]

    def set_variable_value(self, var_name, var_value):
        self._var_to_value[var_name] = var_value

    def get_variable_value(self, var_name):
        return self._var_to_value[var_name]

    def remove_variable(self, var_name):
        # using pop allows us to silently ignore the case where var_name is not in one of the dictionaries
        self._var_to_type.pop(var_name, None)
        self._var_to_value.pop(var_name, None)

    def get_all_variables(self):
        ret = []
        for var_name in self._var_to_type.keys():
            var_type = self._var_to_type[var_name]
            var_value = self._var_to_value[var_name]
            ret.append((var_name, var_type, var_value))
        return ret

    def contains_variable(self, var_name):
        return var_name in self._var_to_value or var_name in self._var_to_type

    def set_relation_schema(self, relation_name, schema):
        self._relation_to_schema[relation_name] = schema

    def get_relation_schema(self, relation_name):
        return self._relation_to_schema[relation_name]

    def get_all_relations(self):
        return ((relation, schema) for relation, schema in self._relation_to_schema.items())

    def contains_relation(self, relation_name):
        return relation_name in self._relation_to_schema

    def remove_relation(self, relation_name):
        del self._relation_to_schema[relation_name]
