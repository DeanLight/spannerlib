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
    def __init__(self, debug=False):
        self._symbol_table = SymbolTable()
        self._term_graph = NetxTermGraph()
        self._execution = execution.PydatalogEngine(debug)

        self._pass_stack = [
            RemoveTokens,
            FixStrings,
            CheckReservedRelationNames,
            ConvertSpanNodesToSpanInstances,
            ConvertStatementsToStructuredNodes,
            CheckDefinedReferencedVariables,
            # CheckForRelationRedefinitions,
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

    def run_query(self, query):
        """
        generates an AST and passes it through the pass stack
        Args:
            query: the query

        Returns: the query result or an error if the query failed
        """

        try:
            parse_tree = self._parser.parse(query)
        except Exception as e:
            return f'exception during parsing {e}'

        try:
            statements = [statement for statement in parse_tree.children]
            for statement in statements:
                self._run_passes(statement, self._pass_stack)
        except Exception as e:
            self._execution.flush_prints_buffer()  # clear the prints buffer as the execution failed
            raise

        return self._execution.flush_prints_buffer()

    def register(self, ie_function, ie_function_name, in_rel, out_rel, is_output_const=True):
        # if ie_function_name.startswith("__"):
        #     raise Exception(f'{ie_function_name} is a reserved name.')
        self._symbol_table.register_ie_function(ie_function, ie_function_name, in_rel, out_rel, is_output_const)

    def delete_rule(self, rule_head: str):
        pass

    def get_pass_stack(self):
        """
        Returns: the current pass stack
        """
        return [pass_.__name__ for pass_ in self._pass_stack]

    def set_pass_stack(self, user_stack):
        """
        sets a new pass stack instead of the current one
        Args:
            user_stack: a user supplied pass stack

        Returns: success message with the new pass stack
        """

        if type(user_stack) is not list:
            raise TypeError('user stack should be a list of pass names (strings)')
        for pass_ in user_stack:
            if type(pass_) is not str:
                raise TypeError('user stack should be a list of pass names (strings)')

        self._pass_stack = []
        for pass_ in user_stack:
            self._pass_stack.append(eval(pass_))
        return self.get_pass_stack()

    # Note that PyDatalog doesn't support retraction of recursive rule!
    # e.g, we can't delete a rule such as: ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y)
    def remove_rule(self, rule: str):
        """
        remove a rule from the rgxlog engine

        Args:
            rule: the rule to be removed
        """
        self._execution.remove_rule(rule)

    @staticmethod
    def _unknown_task_type():
        return 'unknown task type'


if __name__ == '__main__':
    pass
