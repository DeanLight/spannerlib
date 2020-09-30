from abc import ABC, abstractmethod


class SymbolTableBase(ABC):
    @abstractmethod
    def add_variable(self, name, data):
        pass

    @abstractmethod
    def remove_variable(self, name):
        pass

    @abstractmethod
    def get_all_variables(self):
        pass

    def __repr__(self):
        print(self.get_all_variables())

    def __str__(self):
        print('Variable\tData')
        for name, data in self.get_all_variables():
            print(f'{name}\t{data}')


class SymbolTable(SymbolTableBase):
    def __init__(self):
        self._var_to_node = {}

    def add_variable(self, name, data):
        self._var_to_node[name] = data

    def remove_variable(self, name):
        del self._var_to_node[name]

    def get_all_variables(self):
        return ((var, data) for var, data in self._var_to_node.items())
