import os

import rgxlog
from lark.lark import Lark
from lark.visitors import Visitor_Recursive, Interpreter, Visitor, Transformer
from rgxlog.engine import execution
from rgxlog.engine.execution import GenericExecution, ExecutionBase
from rgxlog.engine.passes.lark_passes import RemoveTokens, FixStrings, CheckReservedRelationNames, \
    ConvertSpanNodesToSpanInstances, ConvertStatementsToStructuredNodes, CheckDefinedReferencedVariables, \
    CheckForRelationRedefinitions, CheckReferencedRelationsExistenceAndArity, \
    CheckReferencedIERelationsExistenceAndArity, CheckRuleSafety, TypeCheckAssignments, TypeCheckRelations, \
    SaveDeclaredRelationsSchemas, ReorderRuleBody, ResolveVariablesReferences, ExecuteAssignments, \
    AddStatementsToNetxTermGraph
from rgxlog.engine.message_definitions import Request, Response
from rgxlog.engine.state.symbol_table import SymbolTable
from rgxlog.engine.state.term_graph import NetxTermGraph


class Session:
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

        self._parser = Lark(self._grammar, parser='lalr', debug=True)

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
        return [repr(self._symbol_table), repr(self._term_graph)]

    def __str__(self):
        return f'Symbol Table:\n{str(self._symbol_table)}\n\nTerm Graph:\n{str(self._term_graph)}'

    def execute(self, task):
        """
        executes the task received from the client
        """
        msg_type = task['msg_type']
        data = task['data']
        if msg_type == Request.QUERY:
            return self._run_query(data)
        elif msg_type == Request.IE_REGISTRATION:
            return self.register_ie_function(data)
        elif msg_type == Request.CURRENT_STACK:
            return self._get_pass_stack()
        elif msg_type == Request.SET_STACK:
            return self._set_user_stack_as_pass_stack(data)
        return self._unknown_task_type()

    def _run_query(self, query):
        """
        generates an AST and passes it through the pass stack
        Args:
            query: the query

        Returns: the query result or an error if the query failed
        """

        try:
            parse_tree = self._parser.parse(query)
        except Exception as e:
            return {'msg_type': Response.FAILURE, 'data': f'exception during parsing {e}'}

        try:
            statements = [statement for statement in parse_tree.children]
            for statement in statements:
                self._run_passes(statement, self._pass_stack)
        except Exception as e:
            self._execution.flush_prints_buffer()  # clear the prints buffer as the execution failed
            return {'msg_type': Response.FAILURE, 'data': f'exception during semantic checks or execution:\n {e}'}

        result = self._execution.flush_prints_buffer()
        return {'msg_type': Response.SUCCESS, 'data': result}

    def register(self, ie_function, ie_function_name, in_rel, out_rel, is_super_user):
        self._symbol_table.register_ie_function(ie_function, ie_function_name, in_rel, out_rel, is_super_user)
        # TODO: return value

    def old_register_ie_function(self, ie_function_name):
        """
        registers an ie function for future usage
        Args:
            ie_function_name: the function's name

        Returns: success message if succeeded or an error if the ie function is not on the server
        """
        success = self._symbol_table.register_ie_function(ie_function_name)
        if not success:
            response = {'msg_type': Response.FAILURE, 'data': 'the ie function is not on the server'}
        else:
            response = {'msg_type': Response.SUCCESS, 'data': f'registered {ie_function_name}'}
        return response

    def _get_pass_stack(self):
        """
        Returns: the current pass stack
        """
        pass_stack = [pass_.__name__ for pass_ in self._pass_stack]
        return {'msg_type': Response.SUCCESS, 'data': pass_stack}

    def _set_user_stack_as_pass_stack(self, new_pass_stack):
        """
        sets a new pass stack instead of the current one
        Args:
            new_pass_stack: a user supplied pass stack

        Returns: success message with the new pass stack
        """
        self._pass_stack = []
        for pass_ in new_pass_stack:
            self._pass_stack.append(eval(pass_))
        return {'msg_type': Response.SUCCESS, 'data': self._get_pass_stack()}

    @staticmethod
    def _unknown_task_type():
        return {'msg_type': Response.FAILURE, 'data': 'unknown task type'}
