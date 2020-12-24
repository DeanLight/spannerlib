from abc import ABC, abstractmethod
from typing import List, Tuple
from rgxlog.engine.term_graph import EvalState, TermGraphBase
from pyDatalog import pyDatalog
from rgxlog.engine.datatypes import Span
from rgxlog.engine.symbol_table import SymbolTableBase
import rgxlog.engine.ie_functions as ie_functions
from rgxlog.engine.ie_functions import IEFunctionData
from rgxlog.engine.structured_nodes import *
from rgxlog.engine.general_utils import get_output_free_var_names, get_input_free_var_names
from itertools import chain


class DatalogEngineBase(ABC):
    """
    An abstraction for a datalog execution engine
    """

    def __init__(self):
        super().__init__()

    @abstractmethod
    def declare_relation(self, relation_decl):
        """
        declares a relation in the datalog engine

        Args:
            relation_decl: a relation declaration
        """
        pass

    @abstractmethod
    def add_fact(self, fact):
        """
        add a fact to the datalog engine

        Args:
            fact: the fact to be added
        """
        pass

    @abstractmethod
    def remove_fact(self, fact):
        """
        remove a fact from the datalog engine

        Args:
            fact: the fact to be removed
        """
        pass

    @abstractmethod
    def print_query(self, query):
        """
        queries the datalog engine and prints the results

        Args:
            query: a query who's results will be printed
        """
        pass

    @abstractmethod
    def query(self, query):
        """
        queries the datalog engine

        Args:
            query: a query for the datalog engine

        Returns: a list of tuples that are the query's results
        """
        pass

    @abstractmethod
    def add_rule(self, rule_head, rule_body):
        pass

    @abstractmethod
    def compute_rule_body_relation(self, relation):
        pass

    @abstractmethod
    def compute_rule_body_ie_relation(self, ie_relation, ie_func_data, bounding_relation):
        """
        computes a rule body ie relation
        since ie relations may have input free variables, we need to use another relation to determine the inputs
        for ie_relation. Each free variable that appears as an ie_relation input term must appear at least once in the
        bounding_relation terms.
        Should the ie relation not have any input free variables, bounding_relation can be None
        Args:
            ie_relation: a relation that determines the input and output terms of the ie function
            ie_func_data: the data for the ie function
            bounding_relation: a relation that contains the inputs for ie_funcs. the actual input needs to be
            extracted from it

        Returns: resulting relation
        """
        pass

    @abstractmethod
    def aggregate_relations_to_temp_relation(self, relations):
        """
        perform an inner join between all of the relations in "relations" and saves the result to a relation
        that its schema is defined by all the free variables that appear in the relations in "relations".

        for example, if relations is [A(X,Y,3), B(X,Z,W)], this function should return a relation that is defined
        like this:
        some_temp(X,Y,Z,W) <- A(X,Y,3), B(X,Z,W)
        """
        pass


class PydatalogEngine(DatalogEngineBase):
    """
    implementation of a datalog engine using pyDatalog
    pyDatalog is an implementation of datalog in python

    the official documentation can be found at: https://sites.google.com/site/pydatalog/home
    note that you do not have to read too deep into pyDatalog as we only use a small part of it that is relatively
    simple to the rest of the language

    in our implementation, we load statements into the pyDatalog engine using python
    you can read more about it in https://sites.google.com/site/pydatalog/advanced-topics
    under section 'Dynamic datalog statements'

    more details on how we execute each pyDatalog statement can be found under the relevant method in this class.
    """

    def __init__(self, debug=False):
        """
        Args:
            debug: print the commands that are loaded into pyDatalog
        """
        super().__init__()
        self.next_temp_relation_idx = 0
        self.debug = debug

    @staticmethod
    def __get_span_string(span: Span):
        """
        the pyDatalog execution engine receives instructions via strings.
        return a string representation of a span term in pyDatalog.
        since there's no built in representation of a span in pyDatalog, and custom classes do not seem to work
        as intended , so we represent a span using a tuple of length 2.
        Args:
            span: a span

        Returns: a pyDatalog string representation of the span
        """
        span_string = f'({span.span_start}, {span.span_end})'
        return span_string

    def __get_relation_string(self, relation: Relation):
        """
        the pyDatalog execution engine receives instructions via strings.
        return a relation string representation of a relation in pyDatalog.
        quotes are added to string terms so pyDatalog will not be confused between strings and variables.
        spans are represented as tuples of length 2 (see PydatalogEngine.__get_span_string())

        Args:
            relation: a relation

        Returns: a pydatalog string representation of the relation
        """

        # create a string representation of the relation's term list in pyDatalog
        pydatalog_string_terms = \
            [f"\"{term}\"" if term_type is DataTypes.string
             else self.__get_span_string(term) if term_type is DataTypes.span
            else str(term)
             for term, term_type in zip(relation.term_list, relation.type_list)]
        pydatalog_string_term_list = ', '.join(pydatalog_string_terms)

        # create a string representation of the relation in pydatalog and return it
        pydatalog_string_relation = f"{relation.relation_name}({pydatalog_string_term_list})"
        return pydatalog_string_relation

    def __get_all_relation_tuples(self, relation: Relation) -> List[Tuple]:
        """
        Args:
            relation: a relation to be queried

        Returns: all the tuples of 'relation' as a list of tuples
        """
        relation_name = relation.relation_name
        relation_arity = len(relation.term_list)

        # in order to get all of the tuples of the relation, we'll query the relation with a query that only has
        # free variable terms, where each one of the free variables has a different name
        # for example for the relation 'Parent(str, str)', we'll construct the query '?Parent(X0, X1)'
        query_relation_name = relation_name
        query_terms = [f'X{i}' for i in range(relation_arity)]
        query_term_types = [DataTypes.free_var_name] * relation_arity
        query = Query(query_relation_name, query_terms, query_term_types)

        # query the relation using the query we've constructed, and return the result
        all_relation_tuples = self.query(query)
        return all_relation_tuples

    def __create_new_temp_relation(self, arity):
        """
        declares a new temporary relation with the requested arity in pyDatalog
        note that the relation's schema is not needed as there's no typechecking in pyDatalog

        Args:
            arity: the temporary relation's arity (needed for declaring the new relation inside pyDatalog)

        Returns: the new temporary relation's name
        """

        # create the name of the new temporary relation
        temp_relation_name = f'__rgxlog__{self.next_temp_relation_idx}'
        self.next_temp_relation_idx += 1

        # in pyDatalog there's no typechecking so we just need to make sure that the schema has the correct arity
        temp_relation_schema = [DataTypes.free_var_name] * arity

        # create the declaration.
        temp_relation_decl = RelationDeclaration(temp_relation_name, temp_relation_schema)

        # declare the relation in pyDatalog, and return its name
        self.declare_relation(temp_relation_decl)
        return temp_relation_name

    def __extract_temp_relation(self, relation_list: List[Relation]) -> Relation:
        """
        TODO
        creates a new temp relation where each free variable that appears in relations, appears once in the new
        relation.
        for example: for input relation A(X,Y,X), B("b",3,W) we'll get some_temp(X,Y,W)

        Args:
            relation_list:

        Returns:

        """
        free_var_sets = [get_output_free_var_names(relation, 'relation') for relation in relation_list]
        free_vars = set().union(*free_var_sets)
        temp_relation_terms = free_vars

        temp_relation_arity = len(temp_relation_terms)
        temp_relation_types = [DataTypes.free_var_name] * temp_relation_arity
        temp_relation_name = self.__create_new_temp_relation(temp_relation_arity)

        temp_relation = Relation(temp_relation_name, temp_relation_terms, temp_relation_types)
        return temp_relation

    @staticmethod
    def __assert_ie_output_properly_typed(ie_output, ie_output_schema, ie_relation):
        """
        even though rgxlog performs typechecking during the semantic checks phase, information extraction functions
        are written by the users and could yield results that are not properly typed.
        this method asserts an information extraction function's output is properly typed

        Args:
            ie_output: an output of an ie function
            ie_output_schema: the expected schema for ie_output
            ie_relation: the ie relation for which the output was computed (will be used to print an exception
            in case the output is not properly typed)
        """

        # get a list of the ie output's term types
        ie_output_term_types = []
        for output_term in ie_output:
            if isinstance(output_term, int):
                output_type = DataTypes.integer
            elif isinstance(output_term, str):
                output_type = DataTypes.string
            elif (isinstance(output_term, tuple) and len(output_term) == 2) or isinstance(output_term, Span):
                # allow the user to return a span as either a tuple of length 2 or a datatypes.Span instance
                output_type = DataTypes.span
            else:
                # encountered an output term of an unsupported type
                raise Exception(f'executing ie relation {ie_relation}\n'
                                f'failed because one of the outputs had an unsupported term type\n'
                                f'the output: {ie_output}\n'
                                f'the invalid term: {output_term}\n'
                                f'the invalid term type: {type(output_term)}\n'
                                f'note that only strings, spans and integers are supported\n'
                                f'spans can be represented as a tuple of length 2 or as a datatypes.span instance')
            ie_output_term_types.append(output_type)

        # assert that the ie output is properly typed
        ie_output_is_properly_typed = ie_output_term_types == list(ie_output_schema)
        if not ie_output_is_properly_typed:
            raise Exception(f'executing ie relation {ie_relation}\n'
                            f'failed because one of the outputs had unexpected term types\n'
                            f'the output: {ie_output}\n'
                            f'the output term types: {ie_output_term_types}\n'
                            f'the expected types: {ie_output_schema}')

    def declare_relation(self, relation_decl: RelationDeclaration):
        """
        declares a relation in the pyDatalog engine

        Args:
            relation_decl: a relation declaration
        """

        # unlike rgxlog, pyDatalog does not have a relation declaration statement and typechecking, but pyDatalog
        # will always act as if a relation reference is valid if a fact was ever added to said relation.
        # we will exploit this by adding a fact in which all terms are 'None', then remove said fact, thus effectively
        # declaring an empty relation
        relation_name = relation_decl.relation_name

        # get a 'None' term only terms list as a string in pyDatalog
        # note that while there's no typechecking in pyDatalog, the arity is checked, that's why we use the arity
        # of the original relation declaration
        relation_arity = len(relation_decl.type_list)
        decl_terms = ['None'] * relation_arity
        decl_terms_string = ', '.join(decl_terms)

        # create the fact string that we'll use
        temp_fact_string = f'{relation_name}({decl_terms_string})'

        # create the string that we will use to declare the relation (add and remove the same fact)
        relation_decl_statement = f'+{temp_fact_string}\n' \
                                  f'-{temp_fact_string}'

        # declare the relation in pyDatalog
        pyDatalog.load(relation_decl_statement)

    def add_fact(self, fact: AddFact):
        """
        add a fact in the pyDatalog engine

        Args:
            fact: the fact to be added
        """
        relation_string = self.__get_relation_string(fact)
        # the syntax for a 'add fact' statement in pyDatalog is '+some_relation(term_list)' create that statement
        add_fact_statement = f'+{relation_string}'
        if self.debug:
            print(add_fact_statement)
        # add the fact in pyDatalog
        pyDatalog.load(add_fact_statement)

    def remove_fact(self, fact: RemoveFact):
        relation_string = self.__get_relation_string(fact)
        # the syntax for a 'remove fact' statement in pyDatalog is '-some_relation(term_list)' create that statement
        remove_fact_statement = f'-{relation_string}'
        if self.debug:
            print(remove_fact_statement)
        # remove the fact in pyDatalog
        pyDatalog.load(remove_fact_statement)

    def print_query(self, query: Query):
        """
        queries pyDatalog and prints the results

        Args:
            query: a query who's results will be printed
        """
        relation_string = self.__get_relation_string(query)
        # the syntax for printing a query in pyDatalog is 'print(some_relation(term_list))', create a query statement
        query_statement = f'print({relation_string})'
        if self.debug:
            print(query_statement)
        # loading the query into pyDatalog this way prints a table of the results
        pyDatalog.load(query_statement)

    def query(self, query: Query):
        """
        Args:
            query: a query for pyDatalog

        Returns: a list of tuples that are the query's results
        """

        # create the query. note that we don't use a question mark when we expect pyDatalog to return the query's
        # results instead of printing them. the syntax is 'some_relation(term_list)' (a normal relation representation)
        query_statement = self.__get_relation_string(query)

        if self.debug:
            print(f'non-print query: {query_statement}')

        # loading the query into pyDatalog this way returns an object that contains a list of the resulting tuples
        py_datalog_answer_object = pyDatalog.ask(query_statement)

        # get the actual results out of the object and return them
        if py_datalog_answer_object is None:
            # special case when the query yields no results. return an empty list
            query_results = []
        else:
            # there's at least one resulting tuple, get the list of resulting tuples by accessing the 'answers' field
            query_results = py_datalog_answer_object.answers
        return query_results

    def add_rule(self, rule_head: Relation, rule_body: List[Relation]):
        rule_head_string = self.__get_relation_string(rule_head)
        rule_body_relation_strings = [self.__get_relation_string(relation) for relation in rule_body]
        rule_body_string = " & ".join(rule_body_relation_strings)
        rule_string = f'{rule_head_string} <= {rule_body_string}'
        if self.debug:
            print(rule_string)
        pyDatalog.load(rule_string)

    def compute_rule_body_relation(self, relation: Relation):
        temp_relation = self.__extract_temp_relation([relation])

        if self.debug:
            print(self.__get_relation_string(temp_relation) + " <= " + self.__get_relation_string(relation))
        pyDatalog.load(self.__get_relation_string(temp_relation) + " <= " + self.__get_relation_string(relation))
        return temp_relation

    def compute_rule_body_ie_relation(self, ie_relation: IERelation, ie_func_data: IEFunctionData,
                                      bounding_relation: Relation):

        input_relation_name = self.__create_new_temp_relation(len(ie_relation.input_term_list))
        input_relation = Relation(input_relation_name, ie_relation.input_term_list, ie_relation.input_type_list)

        output_relation_name = self.__create_new_temp_relation(len(ie_relation.output_term_list))
        output_relation = Relation(output_relation_name, ie_relation.output_term_list, ie_relation.output_type_list)

        if bounding_relation is None:
            # special case where the ie relation is the first rule body relation
            # assert that the relation is bound. in this case it is bound if and only if it has no free variable terms
            input_free_vars = get_input_free_var_names(ie_relation, "ie_relation")
            if input_free_vars:
                raise Exception(f'encountered unbounded free variables:{input_free_vars}')

            self.add_fact(
                AddFact(input_relation.relation_name, ie_relation.input_term_list, ie_relation.input_type_list))

        else:
            # extract the input into an input relation.
            self.add_rule(input_relation, [bounding_relation])

        # get a list of input tuples. to get them we query pyDatalog using the input relation name, and all
        # of the terms will be free variables (so we get whole tuples)
        ie_inputs = self.__get_all_relation_tuples(input_relation)

        # get all the outputs
        ie_output_lists = [ie_func_data.ie_function(*ie_input) for ie_input in ie_inputs]
        ie_outputs = list(chain(*ie_output_lists))

        ie_output_schema = tuple(ie_func_data.get_output_types(len(ie_relation.output_term_list)))

        for ie_output in ie_outputs:
            ie_output = list(ie_output)

            self.__assert_ie_output_properly_typed(ie_output, ie_output_schema, ie_relation)

            # the user is allowed to represent a span in an ie output as a tuple of length 2
            # convert said tuples to spans
            ie_output = [Span(term[0], term[1]) if (isinstance(term, tuple) and len(term) == 2)
                         else term
                         for term in ie_output]

            output_fact = AddFact(output_relation.relation_name, ie_output, ie_output_schema)
            self.add_fact(output_fact)

        # return the result relation. it's a temp relation that is the inner join of the input and output relations
        return self.aggregate_relations_to_temp_relation([input_relation, output_relation])

    def aggregate_relations_to_temp_relation(self, relations):
        result = self.__extract_temp_relation(relations)
        self.add_rule(result, relations)
        return result


class ExecutionBase(ABC):
    """
    Abstraction for a class that gets a term graph and execute it
    """

    def __init__(self):
        super().__init__()

    @abstractmethod
    def execute(self, term_graph, symbol_table, datalog_engine):
        pass


class NetworkxExecution(ExecutionBase):
    """
    Executes a networkx based term graph
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    def __execute_rule_aux(rule_term_id, term_graph: TermGraphBase,
                           symbol_table: SymbolTableBase, datalog_engine: DatalogEngineBase):
        """
        This rule execution assumes that a previous pass reordered the rule body relations in a way that
        each relation's input free variables (should they exist) are bounded by relations to the relation's
        left. lark_passes.ReorderRuleBodyVisitor is an example for such a pass.

        this implementation computes each rule body relation from left to right, each time aggregating
        all of the free variables (and their values) seen so far.
        Once all of the rule body relations are computed, the aggregated relation is filtered into the
        rule head relation.
        See example at https://github.com/DeanLight/spanner_workbench/issues/23#issuecomment-721704745
        """
        """
        TODO:
        1. in a different pass, reorder the terms in a way that relations that contain free variables
        that are not used in other relations are on the right side of the rule (so they are computed
        at the very end of the rule)

        For example for the rule
        A(X,Y) <- B(K), C(X), D(X)->(Y)
        we notice that B's free variable K is not used by the other relations, so we could optimize the
        rule computations by reordering the rule like this:
        A(X,Y) <- C(X), D(X)->(Y), B(K)

        2. An improvement of optimization 1: 
        a. create a dependency graph of rule body relations 
        (where an edge from relation e1 to relation e2 means that e2 depends on the results of e1)
        b. using the dependency graph, compute relations in a way that you only aggregate results to a 
        temporary relation when you have to.

        for example for the rule A(Z) <- C(X),D(X,Y),B(Z),G(Z)->(Z),F(Y,Z)->(Y,Z):
        a. the bounding graph is:
            C -> D
            B -> G
            G -> F
            D -> F
        b. we could for example compute this rule in the following way:
        * compute C, use it to compute D, aggregate the results to temp1
        * compute B, use it to compute G, aggregate the results to temp2
        * aggregate temp1 and temp2 to temp3
        * use temp3 to compute F, aggregate the result and temp3 to temp4
        * filter temp4 into the rule head relation A(Z)
        """
        rule_head_id, rule_body_id = term_graph.get_term_first_order_dependencies(rule_term_id)

        body_relation_ids = term_graph.get_term_first_order_dependencies(rule_body_id)
        temp_result = None
        for relation_id in body_relation_ids:
            relation = term_graph.get_term_value(relation_id)
            relation_type = term_graph.get_term_type(relation_id)

            if relation_type == 'relation':
                result_relation = datalog_engine.compute_rule_body_relation(relation)
            elif relation_type == 'ie_relation':
                ie_func_data = symbol_table.get_ie_func_data(relation.relation_name)
                result_relation = datalog_engine.compute_rule_body_ie_relation(relation, ie_func_data, temp_result)
            else:
                raise Exception(f'unexpected relation type: {relation_type}')

            term_graph.set_term_value(relation_id, result_relation)
            term_graph.set_term_state(relation_id, EvalState.COMPUTED)
            if temp_result is None:
                temp_result = result_relation
            else:
                temp_result = datalog_engine.aggregate_relations_to_temp_relation([temp_result, result_relation])

        rule_head_relation = term_graph.get_term_value(rule_head_id)
        rule_head_declaration = RelationDeclaration(
            rule_head_relation.relation_name, symbol_table.get_relation_schema(rule_head_relation.relation_name))
        datalog_engine.declare_relation(rule_head_declaration)
        datalog_engine.add_rule(rule_head_relation, [temp_result])

    def execute(self, term_graph: TermGraphBase, symbol_table: SymbolTableBase, datalog_engine: DatalogEngineBase):
        for term_id in term_graph.get_dfs_post_ordered_term_id_list():
            if term_graph.get_term_state(term_id) != EvalState.COMPUTED:
                term_type = term_graph.get_term_type(term_id)

                if term_type == "relation_declaration":
                    relation_decl = term_graph.get_term_value(term_id)
                    datalog_engine.declare_relation(relation_decl)

                elif term_type == "add_fact":
                    fact = term_graph.get_term_value(term_id)
                    datalog_engine.add_fact(fact)

                elif term_type == "remove_fact":
                    fact = term_graph.get_term_value(term_id)
                    datalog_engine.remove_fact(fact)

                elif term_type == "query":
                    query = term_graph.get_term_value(term_id)
                    datalog_engine.print_query(query)

                elif term_type == "rule":
                    self.__execute_rule_aux(term_id, term_graph, symbol_table, datalog_engine)

                term_graph.set_term_state(term_id, EvalState.COMPUTED)
