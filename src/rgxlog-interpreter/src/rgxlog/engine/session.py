from abc import ABC, abstractmethod

from rgxlog.engine.symbol_table import SymbolTable
from rgxlog.engine.term_graph import TermGraph


class SessionBase(ABC):
    def __init__(self):
        self._st = SymbolTable()
        self._tg = TermGraph()

    @abstractmethod
    def read_state(self):
        pass

    @abstractmethod
    def update_state(self):  # TODO: probably split to several smaller functions
        pass

    def __repr__(self):
        print(repr(self._st))
        print(repr(self._tg))

    def __str__(self):
        print('Symbol Table:')
        print(str(self._st))
        print('Term Graph:')
        print(str(self._tg))


# TODO add save/load
class Session(SessionBase):
    pass
