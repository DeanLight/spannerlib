import os
from abc import ABC

import rgxlog
from lark.lark import Lark
from lark.visitors import Visitor_Recursive, Interpreter, Visitor, Transformer
from rgxlog.engine.graph_converters import Converter, LarkTreeToNetxTree
from rgxlog.engine.lark_passes import RemoveTokens, String, CheckReferencedVariables, \
    CheckReferencedRelations, CheckRuleSafety, TypeChecking
from rgxlog.engine.message_definitions import Request, Response
from rgxlog.engine.symbol_table import SymbolTable
from rgxlog.engine.term_graph import NetxTermGraph as TermGraph


class SessionBase(ABC):
    def __init__(self):
        self._st = SymbolTable()
        self._tg = TermGraph()
        # TODO: self._ex = Execution()

        self._pass_stack = []

        grammar_file_path = os.path.dirname(rgxlog.grammar.__file__)
        grammar_file_name = 'grammar.lark'
        with open(f'{grammar_file_path}/{grammar_file_name}', 'r') as grammar_file:
            self._grammar = grammar_file.read()

        self._parser = Lark(self._grammar, parser='lalr', debug=True, propagate_positions=True)

    @staticmethod
    def _run_passes(tree, pass_list):
        for cur_pass in pass_list:
            if issubclass(cur_pass, Visitor) or issubclass(cur_pass, Visitor_Recursive) \
                    or issubclass(cur_pass, Interpreter):
                cur_pass().visit(tree)
            elif issubclass(cur_pass, Transformer):
                tree = cur_pass().transform(tree)
            elif issubclass(cur_pass, Converter):
                tree = cur_pass().convert(tree)
            else:
                assert 0
        return tree

    def __repr__(self):
        print(repr(self._st))
        print(repr(self._tg))

    def __str__(self):
        print('Symbol Table:')
        print(str(self._st))
        print('Term Graph:')
        print(str(self._tg))


class Session(SessionBase):
    def __init__(self):
        super().__init__()

        self._pass_stack = [
            RemoveTokens,
            String,
            CheckReferencedVariables,
            CheckReferencedRelations,
            CheckRuleSafety,
            TypeChecking,
            LarkTreeToNetxTree
        ]

    def execute(self, task):
        msg_type = task['msg_type']
        data = task['data']
        if msg_type == Request.QUERY:
            return self._run_query(data)
        elif msg_type == Request.IE_REGISTRATION:
            return self._register_ie_function(data)
        elif msg_type == Request.CURRENT_STACK:
            return self._get_pass_stack()
        elif msg_type == Request.SET_STACK:
            return self._set_user_stack_as_pass_stack(data)
        elif msg_type == Request.GRAMMAR:
            return self._handle_grammar_change_request(data)
        else:
            return self._unknown_task_type()

    def _run_query(self, query):
        try:
            parse_tree = self._parser.parse(query)
        except Exception:
            return {'msg_type': Response.FAILURE, 'data': 'exception during parsing'}

        try:
            parse_tree = Session._run_passes(parse_tree, self._pass_stack)
        except Exception:
            return {'msg_type': Response.FAILURE, 'data': 'exception during semantic checks'}

        return {'msg_type': Response.SUCCESS, 'data': parse_tree.pretty()}

    def _register_ie_function(self, data):
        raise NotImplementedError

    def _get_pass_stack(self):
        return {'msg_type': Response.SUCCESS, 'data': self._pass_stack}

    def _set_user_stack_as_pass_stack(self, data):
        self._pass_stack = data
        return {'msg_type': Response.SUCCESS, 'data': self._get_pass_stack()}

    def _handle_grammar_change_request(self, data):
        self._grammar = data
        self._parser = Lark(self._grammar, parser='lalr', debug=True, propagate_positions=True)
        return {'msg_type': Response.SUCCESS, 'data': None}

    @staticmethod
    def _unknown_task_type():
        return {'msg_type': Response.FAILURE, 'data': 'unknown task type'}
