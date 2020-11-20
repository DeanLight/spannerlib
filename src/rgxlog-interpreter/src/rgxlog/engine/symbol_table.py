from abc import ABC, abstractmethod


class SymbolTableBase(ABC):

    @abstractmethod
    def set_variable_type(self, var_name, var_type):
        pass

    @abstractmethod
    def get_variable_type(self, name):
        pass

    @abstractmethod
    def set_variable_value(self, var_name, var_value):
        pass

    @abstractmethod
    def get_variable_value(self, name):
        pass

    @abstractmethod
    def remove_variable(self, name):
        pass

    @abstractmethod
    def get_all_variables(self):
        pass

    @abstractmethod
    def contains_variable(self, var_name):
        pass

    @abstractmethod
    def set_relation_schema(self, name, schema):
        pass

    @abstractmethod
    def get_relation_schema(self, name):
        pass

    @abstractmethod
    def get_all_relations(self):
        pass

    @abstractmethod
    def contains_relation(self, relation_name):
        pass

    @abstractmethod
    def remove_relation(self, relation_name):
        pass

    def __str__(self):
        ret = 'Variable\tType\tValue'
        for name, var_type, var_value in self.get_all_variables():
            ret += f'\n{name}\t{var_type.to_string()}\t{var_value}'
        ret += '\nRelation\tSchema'
        for relation, schema in self.get_all_relations():
            ret += f'\n{relation}\t('
            for idx, term_type in enumerate(schema):
                ret += term_type.to_string()
                if idx < len(schema) - 1:
                    ret += ", "
            ret += ")"
        return ret


class SymbolTable(SymbolTableBase):
    def __init__(self):
        self._var_to_value = {}
        self._var_to_type = {}
        self._relation_to_schema = {}

    def set_variable_type(self, var_name, var_type):
        self._var_to_type[var_name] = var_type

    def get_variable_type(self, name):
        return self._var_to_type[name]

    def set_variable_value(self, var_name, var_value):
        self._var_to_value[var_name] = var_value

    def get_variable_value(self, name):
        return self._var_to_value[name]

    def remove_variable(self, name):
        del self._var_to_type[name]
        del self._var_to_value[name]

    def get_all_variables(self):
        ret = []
        for var_name in self._var_to_type.keys():
            var_type = self._var_to_type[var_name]
            var_value = self._var_to_value[var_name]
            ret.append((var_name, var_type, var_value))
        return ret

    def contains_variable(self, var_name):
        return var_name in self._var_to_value or var_name in self._var_to_type

    def set_relation_schema(self, name, schema):
        self._relation_to_schema[name] = schema

    def get_relation_schema(self, name):
        return self._relation_to_schema[name]

    def get_all_relations(self):
        return ((relation, schema) for relation, schema in self._relation_to_schema.items())

    def contains_relation(self, relation_name):
        return relation_name in self._relation_to_schema

    def remove_relation(self, relation_name):
        del self._relation_to_schema[relation_name]