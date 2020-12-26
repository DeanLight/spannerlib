import os
import sys
import io
from abc import ABC

import rgxlog
from lark.lark import Lark
from lark.visitors import Visitor_Recursive, Interpreter, Visitor, Transformer
from rgxlog.engine import execution
from rgxlog.engine.execution import GenericExecution, ExecutionBase
from rgxlog.engine.lark_passes import RemoveTokens, FixStrings, CheckReservedRelationNames, \
    ConvertSpanNodesToSpanInstances, ConvertStatementsToStructuredNodes, CheckDefinedReferencedVariables, \
    CheckForRelationRedefinitions, CheckReferencedRelationsExistenceAndArity, \
    CheckReferencedIERelationsExistenceAndArity, CheckRuleSafety, TypeCheckAssignments, TypeCheckRelations, \
    SaveDeclaredRelationsSchemas, ReorderRuleBody, ResolveVariablesReferences, ExecuteAssignments, \
    AddStatementsToNetxTermGraph
from rgxlog.engine.message_definitions import Request, Response
from rgxlog.engine.symbol_table import SymbolTable
from rgxlog.engine.term_graph import NetxTermGraph


class SessionBase(ABC):
    pass  # TODO


class Session(SessionBase):
    def __init__(self):
        self._symbol_table = SymbolTable()
        self._term_graph = NetxTermGraph()
        self._execution = execution.PydatalogEngine()

        self._pass_stack = [
            RemoveTokens,
            FixStrings,
            CheckReservedRelationNames,
            ConvertSpanNodesToSpanInstances,
            ConvertStatementsToStructuredNodes,
            CheckDefinedReferencedVariables,
            CheckForRelationRedefinitions,
            CheckReferencedRelationsExistenceAndArity,
            CheckReferencedIERelationsExistenceAndArity,
            CheckRuleSafety,
            TypeCheckAssignments,
            TypeCheckRelations,
            SaveDeclaredRelationsSchemas,
            ReorderRuleBody,
            ResolveVariablesReferences,
            ExecuteAssignments,
            AddStatementsToNetxTermGraph,
            GenericExecution
        ]

        grammar_file_path = os.path.dirname(rgxlog.grammar.__file__)
        grammar_file_name = 'grammar.lark'
        with open(f'{grammar_file_path}/{grammar_file_name}', 'r') as grammar_file:
            self._grammar = grammar_file.read()

        self._parser = Lark(self._grammar, parser='lalr', debug=True, propagate_positions=True)

    def _run_passes(self, tree, pass_list):
        """
        Runs the passes in pass_list on tree, one after another.
        """
        for cur_pass in pass_list:
            if issubclass(cur_pass, Visitor) or issubclass(cur_pass, Visitor_Recursive) or \
                    issubclass(cur_pass, Interpreter):
                cur_pass(symbol_table=self._symbol_table, term_graph=self._term_graph).visit(tree)
            elif issubclass(cur_pass, Transformer):
                tree = cur_pass(symbol_table=self._symbol_table, term_graph=self._term_graph).transform(tree)
            elif issubclass(cur_pass, ExecutionBase):
                cur_pass(
                    term_graph=self._term_graph,
                    symbol_table=self._symbol_table,
                    rgxlog_engine=self._execution
                ).execute()
            else:
                raise Exception(f'invalid pass: {cur_pass}')
        return tree

    def __repr__(self):
        print(repr(self._symbol_table))
        print(repr(self._term_graph))

    def __str__(self):
        print('Symbol Table:')
        print(str(self._symbol_table))
        print('Term Graph:')
        print(str(self._term_graph))

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
        except Exception as e:
            return {'msg_type': Response.FAILURE, 'data': f'exception during parsing {e}'}

        # pydatalog printing workaround
        orig_stdout = sys.stdout
        temp_stdout = io.StringIO()
        sys.stdout = temp_stdout
        try:
            statements = [statement for statement in parse_tree.children]
            for statement in statements:
                self._run_passes(statement, self._pass_stack)
        except Exception as e:
            sys.stdout = orig_stdout
            return {'msg_type': Response.FAILURE, 'data': f'exception during semantic checks: {e}'}

        sys.stdout = orig_stdout
        return {'msg_type': Response.SUCCESS, 'data': temp_stdout.getvalue()}

    def _register_ie_function(self, data):
        raise NotImplementedError

    def _get_pass_stack(self):
        return {'msg_type': Response.SUCCESS, 'data': self._pass_stack}

    def _set_user_stack_as_pass_stack(self, data):
        self._pass_stack = data  # TODO use eval
        return {'msg_type': Response.SUCCESS, 'data': self._get_pass_stack()}

    def _handle_grammar_change_request(self, data):
        self._grammar = data
        self._parser = Lark(self._grammar, parser='lalr', debug=True, propagate_positions=True)
        return {'msg_type': Response.SUCCESS, 'data': None}

    @staticmethod
    def _unknown_task_type():
        return {'msg_type': Response.FAILURE, 'data': 'unknown task type'}
