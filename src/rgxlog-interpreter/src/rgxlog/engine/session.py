import csv
import os
import re
from pathlib import Path
from typing import Tuple, List

import rgxlog
from lark.lark import Lark
from lark.visitors import Visitor_Recursive, Interpreter, Visitor, Transformer
from pandas import DataFrame
from rgxlog.engine import execution
from rgxlog.engine.datatypes.primitive_types import Span
from rgxlog.engine.execution import GenericExecution, ExecutionBase, AddFact, DataTypes, RelationDeclaration, Query
from rgxlog.engine.passes.lark_passes import (RemoveTokens, FixStrings, CheckReservedRelationNames,
                                              ConvertSpanNodesToSpanInstances, ConvertStatementsToStructuredNodes,
                                              CheckDefinedReferencedVariables,
                                              CheckReferencedRelationsExistenceAndArity,
                                              CheckReferencedIERelationsExistenceAndArity, CheckRuleSafety,
                                              TypeCheckAssignments, TypeCheckRelations,
                                              SaveDeclaredRelationsSchemas, ReorderRuleBody, ResolveVariablesReferences,
                                              ExecuteAssignments, AddStatementsToNetxTermGraph)
from rgxlog.engine.state.symbol_table import SymbolTable
from rgxlog.engine.state.term_graph import NetxTermGraph
from tabulate import tabulate

SPAN_PATTERN = re.compile(r"^\[(\d+), ?(\d+)\)$")
STRING_PATTERN = re.compile(r"^[^\r\n]+$")

TITLE_LINE_NUM = 0
VAR_LINE_NUM = 1
VALUES_LINE_NUM = 3

FUNC_DICT_NAME = "ie_function_name"
FUNC_DICT_OBJ = "ie_function_object"


# TODO: @niv add rust_rgx_*_from_file (ask dean)

def _infer_relation_type(row: iter):
    # TODO: does not support tuples
    relation_types = []
    for cell in row:
        if cell.isdigit():
            relation_types.append(DataTypes.integer)
        elif re.match(SPAN_PATTERN, cell):
            relation_types.append(DataTypes.span)
        elif re.match(STRING_PATTERN, cell):
            # TODO: is this pattern correct?
            relation_types.append(DataTypes.string)
        else:
            raise Exception(f"illegal type in csv: {cell}")

    return relation_types


def _verify_relation_types(row, expected_types):
    if _infer_relation_type(row) != expected_types:
        raise Exception(f"row:\n{str(row)}\ndoes not match the relation's types:\n{str(expected_types)}")


def _extract_query_results(query_results):
    """
    extract vars and values from tabulated query
    :param query_results:
    :return:
    """
    values = []
    split_results = query_results.splitlines()
    if not split_results[TITLE_LINE_NUM].startswith("printing results"):
        raise Exception("cannot extract results from query. Is debug mode activated?")

    var_line = split_results[VAR_LINE_NUM]
    free_vars = [var.strip() for var in var_line.split("|")]
    for line in split_results[VALUES_LINE_NUM:]:
        values.append([val.strip() for val in line.split("|")])
    return values, free_vars


def _add_types_to_data(line, relation_types):
    # TODO find a better name for this function, like "typify" or something
    transformed_line = []
    for value, rel_type in zip(line, relation_types):
        if rel_type == DataTypes.span:
            start, end = [int(num) for num in re.findall(SPAN_PATTERN, value)[0]]
            transformed_line.append(Span(span_start=start, span_end=end))
        elif rel_type == DataTypes.integer:
            transformed_line.append(int(value))
        else:
            assert rel_type == DataTypes.string, f"illegal type given: {rel_type}"
            transformed_line.append(value)

    return transformed_line


def _format_query_results(query: Query, query_results: list):
    # check for the special conditions for which we can't print a table: no results were returned or a single
    # empty tuple was returned
    no_results = len(query_results) == 0
    result_is_single_empty_tuple = len(query_results) == 1 and len(query_results[0]) == 0
    formatted_results = []
    query_free_vars = []

    if no_results:
        tabulated_result_string = '[]'
    elif result_is_single_empty_tuple:
        tabulated_result_string = '[()]'
        formatted_results.append(tuple())
    else:
        # query results can be printed as a table
        # convert the resulting tuples to a more organized format
        for result in query_results:
            # we saved spans as tuples of length 2 in pyDatalog, convert them back to spans so when printed,
            # they will be printed as a span instead of a tuple
            converted_span_result = [Span(term[0], term[1]) if (isinstance(term, tuple) and len(term) == 2)
                                     else term
                                     for term in result]

            formatted_results.append(converted_span_result)

        # get the free variables of the query, they will be used as headers
        query_free_vars = [term for term, term_type in zip(query.term_list, query.type_list)
                           if term_type is DataTypes.free_var_name]

        # get the query result as a table
        tabulated_result_string = tabulate(formatted_results, headers=query_free_vars, tablefmt='presto',
                                           stralign='center')

    return tabulated_result_string, formatted_results, query_free_vars


def query_to_string(query_results: List[Tuple[Query, List]]):
    # TODO: this doesn't execute a query anymore, edit this docstring
    # TODO: if we combined Query+List into a `Result` object, we could turn it into a __str__ method
    """
    queries pyDatalog and saves the resulting string to the prints buffer (to get it use flush_prints_buffer())
    the resulting string is a table that contains all of the resulting tuples of the query.
    the headers of the table are the free variables used in the query.
    above the table there will be a title that contains the query as it was written by the user

    for example:

    printing results for query 'lecturer_of(X, "abigail")':
      X
    --------
    linus
    walter

    there are two cases where a table cannot be printed:
    1. the query returned no results. in this case '[]' will be printed
    2. the query returned a single empty tuple, in this case '[()]' will be printed


    :param query: the Query object used in execution
    :param results: the execution's results (from PyDatalog)
    """

    all_result_strings = []
    query_results = list(filter(None, query_results))  # remove Nones
    for query, results in query_results:
        query_result_string, _, _ = _format_query_results(query, results)
        query_title = f"printing results for query '{query}':"

        # combine the title and table to a single string and save it to the prints buffer
        titled_result_string = f'{query_title}\n{query_result_string}\n'
        all_result_strings.append(titled_result_string)
    return "\n".join(all_result_strings)


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
        # self._register_default_functions()

    def _run_passes(self, tree, pass_list) -> Tuple[Query, List]:
        """
        Runs the passes in pass_list on tree, one after another.
        """
        exec_result = None

        for cur_pass in pass_list:
            if issubclass(cur_pass, Visitor) or issubclass(cur_pass, Visitor_Recursive) or \
                    issubclass(cur_pass, Interpreter):
                cur_pass(symbol_table=self._symbol_table, term_graph=self._term_graph).visit(tree)
            elif issubclass(cur_pass, Transformer):
                tree = cur_pass(symbol_table=self._symbol_table, term_graph=self._term_graph).transform(tree)
            elif issubclass(cur_pass, ExecutionBase):
                # TODO: @dean, is the execution always the last pass? is there always only one execution per statement?
                exec_result = cur_pass(
                    term_graph=self._term_graph,
                    symbol_table=self._symbol_table,
                    rgxlog_engine=self._execution
                ).execute()
            else:
                raise Exception(f'invalid pass: {cur_pass}')
        return exec_result

    def __repr__(self):
        return [repr(self._symbol_table), repr(self._term_graph)]

    def __str__(self):
        return f'Symbol Table:\n{str(self._symbol_table)}\n\nTerm Graph:\n{str(self._term_graph)}'

    def run_query(self, query: str, print_results: bool = True) -> List[Tuple[Query, List]]:
        """
        generates an AST and passes it through the pass stack

        :param query: the user's input
        :param print_results: whether to print the results to stdout or not
        :return the last query's results
        """
        # TODO: @dean is it necessary to return all results (multiple statements)?
        #   right now i'm returning the last one only - yes
        exec_results = []
        parse_tree = self._parser.parse(query)

        for statement in parse_tree.children:
            exec_result = self._run_passes(statement, self._pass_stack)
            exec_results.append(exec_result)
            if print_results and exec_result:
                # TODO: @dean maybe we should create a Results object to handle this more easily?
                print(query_to_string([exec_result]))

        # TODO: make sure prints work fine without flushing (test in jupyter)
        return exec_results

    def register(self, ie_function, ie_function_name, in_rel, out_rel):
        self._symbol_table.register_ie_function(ie_function, ie_function_name, in_rel, out_rel)

    # def register_class(self, ie_function_object, ie_function_name):
    #     self._symbol_table.register_ie_function_object(ie_function_object, ie_function_name)

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

    def import_relation_from_csv(self, csv_file_name, relation_name=None, delimiter=";"):
        if not os.path.isfile(csv_file_name):
            raise IOError("csv file does not exist")

        if os.stat(csv_file_name).st_size == 0:
            raise IOError("csv file is empty")

        # the relation_name is either an argument or the file's name
        if relation_name is None:
            relation_name = Path(csv_file_name).stem

        symbol_table = self._symbol_table
        engine = self._execution

        with open(csv_file_name) as fh:
            reader = csv.reader(fh, delimiter=delimiter)

            # read first line and go back to start of file
            relation_types = _infer_relation_type(next(reader))
            fh.seek(0)

            # first make sure the types are legal, then add them to the engine (to make sure
            #  we don't add them in case of error)
            facts = []
            for line in reader:
                _verify_relation_types(line, relation_types)
                typed_line = _add_types_to_data(line, relation_types)
                facts.append(AddFact(relation_name, typed_line, relation_types))

            # declare relation if it does not exist
            if not symbol_table.contains_relation(relation_name):
                engine.declare_relation(RelationDeclaration(relation_name, relation_types))
                symbol_table.add_relation_schema(relation_name, relation_types, False)

            for fact in facts:
                engine.add_fact(fact)

    def import_relation_from_df(self, relation_df: DataFrame, relation_name):
        symbol_table = self._symbol_table
        engine = self._execution

        data = relation_df.values.tolist()

        if not isinstance(data, list):
            raise Exception("dataframe could not be converted to list")

        if len(data) < 1:
            raise Exception("dataframe is empty")

        relation_types = _infer_relation_type(data[0])

        # first make sure the types are legal, then add them to the engine (to make sure
        #  we don't add them in case of error)
        facts = []
        for line in data:
            _verify_relation_types(line, relation_types)
            facts.append(AddFact(relation_name, line, relation_types))

        # declare relation if it does not exist
        if not symbol_table.contains_relation(relation_name):
            engine.declare_relation(RelationDeclaration(relation_name, relation_types))
            symbol_table.add_relation_schema(relation_name, relation_types, False)

        for fact in facts:
            engine.add_fact(fact)

    def export_relation_to_csv(self, csv_file_name, relation_name, delimiter=";"):
        # TODO
        """
        this will be implemented in a future version
        """
        raise NotImplementedError

    def export_relation_to_df(self, df, relation_name):
        # TODO
        """
        this will be implemented in a future version
        """
        raise NotImplementedError

    def query_into_csv(self, query: str, csv_file_name, delimiter=";"):
        # run a query normally and get formatted results:
        query_results = self.run_query(query, print_results=False)
        if len(query_results) != 1:
            raise Exception("the query must have exactly one output")

        _, rows, free_vars = _format_query_results(*query_results[0])

        # add free_vars at start of csv
        rows.insert(0, free_vars)

        with open(csv_file_name, "w", newline="") as f:
            writer = csv.writer(f, delimiter=delimiter)
            writer.writerows(rows)

    def query_into_df(self, query: str) -> DataFrame:
        # run a query normally and get formatted results:
        query_results = self.run_query(query, print_results=False)
        if len(query_results) != 1:
            raise Exception("the query must have exactly one output")

        _, rows, free_vars = _format_query_results(*query_results[0])
        # TODO: how do i store spans inside a df? use `Span` object?
        query_df = DataFrame(rows, columns=free_vars)
        return query_df

    # def _register_default_functions(self):
    #     for func_dict in DEFAULT_FUNCTIONS:
    #         self.register_class(**func_dict)


if __name__ == '__main__':
    pass
