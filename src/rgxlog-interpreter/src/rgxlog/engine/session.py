import csv
import os
import re
from pathlib import Path
from typing import Tuple, List, Union

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

from rgxlog.stdlib.python_regex import PYRGX, PYRGX_STRING
from rgxlog.stdlib.rust_spanner_regex import RGX, RGX_STRING
from rgxlog.stdlib.json_path import JsonPath
from rgxlog.stdlib.nlp import (Tokenize, SSplit, POS, Lemma, NER, EntityMentions, CleanXML, Parse, DepParse, Coref,
                               OpenIE, KBP, Quote, Sentiment, TrueCase, Entities)

PREDINED_IE_FUNCS = [PYRGX, PYRGX_STRING, RGX, RGX_STRING, JsonPath, Tokenize, SSplit, POS, Lemma, NER, EntityMentions,
                     CleanXML, Parse, DepParse, Coref, OpenIE, KBP, Quote, Sentiment, TrueCase, Entities]

SPAN_GROUP1 = "start"
SPAN_GROUP2 = "end"
# TODO@niv: do we support negative numbers and floating point numbers? might have to add a pattern

SPAN_PATTERN = re.compile(r"^\[(?P<start>\d+), ?(?P<end>\d+)\)$")
STRING_PATTERN = re.compile(r"^[^\r\n]+$")

# rgx constants
FALSE_VALUE = []
TRUE_VALUE = [tuple()]


# TODO@niv: add rust_rgx_*_from_file (ask dean)

def _infer_relation_type(row: iter):
    """
    guess the relation type based on the data.
    we support both the actual types (e.g. 'Span'), and their string representation ( e.g. `"[0,8)"`)
    :param row:
    :return:
    """
    relation_types = []
    for cell in row:
        if isinstance(cell, int) or cell.isdigit():
            relation_types.append(DataTypes.integer)
        elif isinstance(cell, Span) or re.match(SPAN_PATTERN, cell):
            relation_types.append(DataTypes.span)
        elif re.match(STRING_PATTERN, cell):
            relation_types.append(DataTypes.string)
        else:
            raise Exception(f"illegal type in csv: {cell}")

    return relation_types


def _verify_relation_types(row, expected_types):
    if _infer_relation_type(row) != expected_types:
        raise Exception(f"row:\n{str(row)}\ndoes not match the relation's types:\n{str(expected_types)}")


def _text_to_typed_data(line, relation_types):
    transformed_line = []
    for str_or_object, rel_type in zip(line, relation_types):
        if rel_type == DataTypes.span:
            if isinstance(str_or_object, Span):
                transformed_line.append(str_or_object)
            else:
                span_match = re.match(SPAN_PATTERN, str_or_object)
                start, end = span_match.group(SPAN_GROUP1), span_match.group(SPAN_GROUP2)
                transformed_line.append(Span(span_start=start, span_end=end))
        elif rel_type == DataTypes.integer:
            transformed_line.append(int(str_or_object))
        else:
            assert rel_type == DataTypes.string, f"illegal type given: {rel_type}"
            transformed_line.append(str_or_object)

    return transformed_line


def format_query_results(query: Query, query_results: List) -> Union[DataFrame, List]:
    """
    formats a single result from the engine into a usable format
    :param query:
    :param query_results:
    :return:
    """
    assert isinstance(query_results, list), "illegal results format"

    # check for the special conditions for which we can't print a table: no results were returned or a single
    # empty tuple was returned

    if query_results == FALSE_VALUE:  # empty list := false
        return FALSE_VALUE
    elif query_results == TRUE_VALUE:  # single tuple := true
        return TRUE_VALUE
    else:
        # convert the resulting tuples to a more organized format
        results_matrix = []
        for result in query_results:
            # we saved spans as tuples of length 2 in pyDatalog, convert them back to spans so when printed,
            # they will be printed as a span instead of a tuple
            converted_span_result = [Span(term[0], term[1]) if (isinstance(term, tuple) and len(term) == 2)
                                     else term
                                     for term in result]

            results_matrix.append(converted_span_result)

        # get the free variables of the query, they will be used as headers
        query_free_vars = [term for term, term_type in zip(query.term_list, query.type_list)
                           if term_type is DataTypes.free_var_name]

        return DataFrame(data=results_matrix, columns=query_free_vars)


def tabulate_result(result: Union[DataFrame, List]):
    if isinstance(result, DataFrame):
        # query results can be printed as a table
        result_string = tabulate(result, headers="keys", tablefmt="presto", stralign="center", showindex=False)
    else:
        assert isinstance(result, list), "illegal result format"
        if len(result) == 0:
            result_string = "[]"
        else:
            assert len(result) == 1, "illegal result format"
            result_string = "[()]"

    return result_string


def queries_to_string(query_results: List[Tuple[Query, List]]):
    # TODO@niv: maybe we should remove the "printing results" thing?
    """
    takes in a list of results from PyDatalog and converts them into a single string, which contains
    either a table, a false value (=`[]`), or a true value (=`[tuple()]`), for each result.

    for example:

    printing results for query 'lecturer_of(X, "abigail")':
      X
    --------
    linus
    walter


    :param query_results: List[the Query object used in execution, the execution's results (from PyDatalog)]
    """

    all_result_strings = []
    query_results = list(filter(None, query_results))  # remove Nones
    for query, results in query_results:
        query_result_string = tabulate_result(format_query_results(query, results))
        query_title = f"printing results for query '{query}':"

        # combine the title and table to a single string and save it to the prints buffer
        titled_result_string = f'{query_title}\n{query_result_string}\n'
        all_result_strings.append(titled_result_string)
    return "\n".join(all_result_strings)


class Session:
    def __init__(self, debug=False):
        self._symbol_table = SymbolTable()
        self._symbol_table.register_predefined_ie_functions(PREDINED_IE_FUNCS)
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
                # the execution is always the last pass, and there is always only one per statement, so there's
                # no need to have a list of results here
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

    def run_query(self, query: str, print_results: bool = True, format_results=False) -> (
            Union[List[Union[List, List[Tuple], DataFrame]], List[Tuple[Query, List]]]):
        """
        generates an AST and passes it through the pass stack

        :param format_results: if this is true, return the formatted result instead of the `[Query, List]` pair
        :param query: the user's input
        :param print_results: whether to print the results to stdout or not
        :return the results of every query, in a list
        """
        exec_results = []
        parse_tree = self._parser.parse(query)

        for statement in parse_tree.children:
            exec_result = self._run_passes(statement, self._pass_stack)
            exec_results.append(exec_result)
            if print_results and exec_result:
                print(queries_to_string([exec_result]))

        if format_results:
            return [format_query_results(*exec_result) for exec_result in exec_results]
        else:
            return exec_results

    def register(self, ie_function, ie_function_name, in_rel, out_rel):
        self._symbol_table.register_ie_function(ie_function, ie_function_name, in_rel, out_rel)

    def get_pass_stack(self):
        """
        Returns: the current pass stack
        """
        return [pass_.__name__ for pass_ in self._pass_stack]

    # TODO@tom: it's their implementation. (@niv: can you be more explicit here? i'm not sure what this means)
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

    def _add_imported_relation_to_engine(self, relation_table, relation_name, relation_types):
        symbol_table = self._symbol_table
        engine = self._execution
        # first make sure the types are legal, then we add them to the engine (to make sure
        #  we don't add them in case of an error)
        facts = []

        # TODO@niv: this needs to support both strings and objects
        for row in relation_table:
            _verify_relation_types(row, relation_types)
            typed_line = _text_to_typed_data(row, relation_types)
            facts.append(AddFact(relation_name, typed_line, relation_types))

        # declare relation if it does not exist
        if not symbol_table.contains_relation(relation_name):
            engine.declare_relation(RelationDeclaration(relation_name, relation_types))
            symbol_table.add_relation_schema(relation_name, relation_types, False)

        for fact in facts:
            engine.add_fact(fact)

    def import_relation_from_csv(self, csv_file_name, relation_name=None, delimiter=";"):
        if not os.path.isfile(csv_file_name):
            raise IOError("csv file does not exist")

        if os.stat(csv_file_name).st_size == 0:
            raise IOError("csv file is empty")

        # the relation_name is either an argument or the file's name
        if relation_name is None:
            relation_name = Path(csv_file_name).stem

        with open(csv_file_name) as fh:
            reader = csv.reader(fh, delimiter=delimiter)

            # read first line and go back to start of file - make sure there is no empty line!
            relation_types = _infer_relation_type(next(reader))
            fh.seek(0)

            self._add_imported_relation_to_engine(reader, relation_name, relation_types)

    def import_relation_from_df(self, relation_df: DataFrame, relation_name):

        data = relation_df.values.tolist()

        if not isinstance(data, list):
            raise Exception("dataframe could not be converted to list")

        if len(data) < 1:
            raise Exception("dataframe is empty")

        relation_types = _infer_relation_type(data[0])

        self._add_imported_relation_to_engine(data, relation_name, relation_types)

    def query_into_csv(self, query: str, csv_file_name: str, delimiter=";"):
        # run a query normally and get formatted results:
        query_results = self.run_query(query, print_results=False)
        if len(query_results) != 1:
            raise Exception("a query into csv must have exactly one output")

        formatted_result = format_query_results(*query_results[0])

        if isinstance(formatted_result, DataFrame):
            formatted_result.to_csv(csv_file_name, index=False, sep=delimiter)
        else:
            # true or false
            with open(csv_file_name, "w", newline="") as f:
                writer = csv.writer(f, delimiter=delimiter)
                writer.writerows(formatted_result)

    def query_into_df(self, query: str) -> Union[DataFrame, List]:
        # run a query normally and get formatted results:
        query_results = self.run_query(query, print_results=False)
        if len(query_results) != 1:
            raise Exception("the query must have exactly one output")

        return format_query_results(*query_results[0])

    def _relation_name_to_query(self, relation_name: str):
        symbol_table = self._symbol_table
        relation_schema = symbol_table.get_relation_schema(relation_name)
        relation_arity = len(relation_schema)
        query = "?" + relation_name + "(" + ", ".join(f"T{i}" for i in range(relation_arity)) + ")"
        return query

    def export_relation_into_df(self, relation_name: str):
        query = self._relation_name_to_query(relation_name)
        return self.query_into_df(query)

    def export_relation_into_csv(self, csv_file_name, relation_name, delimiter=";"):
        query = self._relation_name_to_query(relation_name)
        return self.query_into_csv(query, csv_file_name, delimiter)

    def print_registered_ie_functions(self):
        """
            Prints information about the registered ie functions
        """
        self._symbol_table.print_registered_ie_functions()

    def remove_ie_function(self, name: str):
        """
        removes a function from the symbol table

        Args:
            name: the name of the ie function to remove
        """
        self._symbol_table.remove_ie_function(name)

    def remove_all_ie_functions(self):
        """
        removes all the ie functions from the symbol table
        """
        self._symbol_table.remove_all_ie_functions()
