"""
this modules contains implementations of 'RgxlogEngineBase' which is an abstraction for the rgxlog engine
and also implementations of 'ExecutionBase' which serves as an abstraction for an interface between a term graph
and an rgxlog engine.
"""

# TODO change all imports to relative imports (after installing rgxlog, we run from site-packages instead of this code)
import re
from abc import ABC, abstractmethod
from itertools import count
from typing import List, Tuple

from pyDatalog import pyDatalog
from rgxlog.engine.datatypes.ast_node_types import *
from rgxlog.engine.datatypes.primitive_types import Span
from rgxlog.engine.ie_functions.ie_function_base import IEFunction
from rgxlog.engine.state.symbol_table import SymbolTableBase
from rgxlog.engine.state.term_graph import EvalState, TermGraphBase
from rgxlog.engine.utils.general_utils import get_output_free_var_names


class RgxlogEngineBase(ABC):
    """
    An abstraction for a rgxlog execution engine
    """

    def __init__(self):
        super().__init__()
        self.prints_buffer = []

    def flush_prints_buffer(self) -> str:
        """
        some of the methods in this class should print their results, but since this project uses jupyter notebook's
        magic system, printing inside the methods may cause the project to behave incorrectly (for example, the prints
        may appear in the wrong cell).

        so instead of printing, the methods of this class should append the strings they want to print to
        self.prints_buffer, and the user of this class can get the string that he should print using this method

        this method also clears the prints buffer

        Returns: a single string that represents all of the prints buffer content. this string should be printed
        by the caller
        """
        ret_string = '\n'.join(self.prints_buffer)
        self.prints_buffer.clear()
        return ret_string

    @abstractmethod
    def declare_relation(self, relation_decl):
        """
        declares a relation in the rgxlog engine

        Args:
            relation_decl: a relation declaration
        """
        pass

    @abstractmethod
    def add_fact(self, fact):
        """
        add a fact to the rgxlog engine

        Args:
            fact: the fact to be added
        """
        pass

    @abstractmethod
    def remove_fact(self, fact):
        """
        remove a fact from the rgxlog engine

        Args:
            fact: the fact to be removed
        """
        pass

    @abstractmethod
    def remove_rule(self, rule: str):
        """
        remove a rule from the rgxlog engine

        Args:
            rule: the rule to be removed
        """

    @abstractmethod
    def query(self, query):
        """
        queries the rgxlog engine

        Args:
            query: a query for the rgxlog engine

        Returns: a list of tuples that are the query's results
        """
        pass

    @abstractmethod
    def add_rule(self, rule_head, rule_body_relation_list):
        """
        add a rule to the rgxlog engine.
        this method assumes that all the relations in the rule body are normal relations (non ie relations)
        this means that the rule will be added as it is, without any micro operations (e.g. computing an ie relation)

        Args:
            rule_head: a relation that defines the rule head
            rule_body_relation_list: a list of relations that defines the rule body
        """
        pass

    @abstractmethod
    def compute_ie_relation(self, ie_relation, ie_func_data, bounding_relation):
        """
        computes an information extraction relation, returning the result as a normal relation.

        since ie relations may have input free variables, we need to use another relation to determine the inputs
        for ie_relation.
        Each free variable that appears as an ie_relation input term must appear at least once in the
        bounding_relation terms.
        Should the ie relation not have any input free variables, bounding_relation can (but not must) be None

        note the an ie relation is effectively two relations: a relation that defines the inputs to an ie function
        and a relation that filters the output of the ie functions.
        seeing that, we can define a general algorithm for this function:

        1. using the input relation to the ie function, filter "bounding_relation" into a relation who's
        tuples are all of the inputs to the ie function. if the input relation has no free variable terms,
        it is basically a fact, i.e., a single tuple, meaning we could skip this step and just use that tuple
        as an input instead.

        2. run the ie function on each one of the tuples of the relation we created in step 1, and save the
        results to a new relation (the output relation)

        3. use the output relation of the ie function, filter the results we got in step 2 to a new relation

        example:
        let's follow the steps for the ie relation "RGX<X,Y>->(Z,[1,2))" with the bounding relation "bind(X,Y,W)":

        1. input_relation(X,Y) <- bind(X,Y,W)  # filter the bounding relation tuples into the input relation

        2. for each tuple in input_relation(X,Y), use it as an input for RGX(x,y) and save the result to a new
        relation called output_relation

        3. filter the outputs of the ie function into a relation like this
        final_ie_result(X,Y,Z) <- input_relation(X,Y), output_relation(Z,[1,2))
        for details on this join operation see "RgxlogEngineBase.join_relations"

        note that "final_ie_result" is defined using only free variables, as an ie relation in rgxlog is merely
        a part of a rule body, which serves to define the rule head relation. the rule head only "cares" about
        free variables, so we can throw away all of the columns defined by constant terms.

        Args:
            ie_relation: an ie relation that determines the input and output terms of the ie function
            ie_func_data: the data for the ie function that will be used to compute the ie relation
            bounding_relation: a relation that contains the inputs for ie_funcs. the actual input needs to be
            queried from it

        Returns: a normal relation that contains all of the resulting tuples in the rgxlog engine
        """
        pass

    @abstractmethod
    def join_relations(self, relation_list, name=""):
        """
        perform a join between all of the relations in the relation list and saves the result to a new relation.
        the results of the join are filtered so they only include columns in the relations that were defined by
        a free variable term.
        all of the relation in relation_list must be normal (not ie relations)

        for example, if the relations are [A(X,Y,3), B(X,Z,W,"some_str")], this function should return a relation
        that is defined like this:
        new_relation(X,Y,Z,W) <- A(X,Y,3), B(X,Z,W,"some_str")

        note that "new_relation" is defined only by free variable terms and all of the free variable terms
        that appear in the rule body, also appear in the rule head

        this method is helpful for saving intermediate results while computing a rule body and also
        for filtering the results of an ie function

        Args:
            relation_list: a list of normal relations
            name: the name for the joined relation (to be used as a part of a temporary relation name)

        Returns: a new relation as described above
        """
        pass


class PydatalogEngine(RgxlogEngineBase):
    """
    implementation of a rgxlog engine using pyDatalog
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
        self.temp_relation_id_counter = count()
        self.debug = debug

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
        relation_decl_statement = f'+{temp_fact_string}\n' + \
                                  f'-{temp_fact_string}'

        # declare the relation in pyDatalog
        pyDatalog.load(relation_decl_statement)

    def add_fact(self, fact: AddFact):
        """
        add a fact in the pyDatalog engine

        Args:
            fact: the fact to be added
        """
        relation_string = self._get_relation_string(fact)
        # the syntax for a 'add fact' statement in pyDatalog is '+some_relation(term_list)' create that statement
        add_fact_statement = f'+{relation_string}'
        if self.debug:
            self.prints_buffer.append(add_fact_statement)
        # add the fact in pyDatalog
        pyDatalog.load(add_fact_statement)

    def remove_fact(self, fact: RemoveFact):
        relation_string = self._get_relation_string(fact)
        # the syntax for a 'remove fact' statement in pyDatalog is '-some_relation(term_list)' create that statement
        remove_fact_statement = f'-{relation_string}'
        if self.debug:
            self.prints_buffer.append(remove_fact_statement)
        # remove the fact in pyDatalog
        pyDatalog.load(remove_fact_statement)

    def remove_rule(self, rule: str):
        # the syntax for a 'remove rule' statement in pyDatalog is '-(rule_definition)'
        # transform rule in RGXLog's syntax into PyDatalog's syntax
        # i.e, ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y) will be transformed to:
        # ancestor(X,Y) <= parent(X,Z)& ancestor(Z,Y)
        replace_commas = re.compile(r'(?:[^,(]|\([^)]*\))+')
        remove_rule_statement = "&".join(replace_commas.findall(rule))
        remove_rule_statement = f'-({remove_rule_statement.replace("-", "=")})'
        if self.debug:
            self.prints_buffer.append(remove_rule_statement)
        # remove the rule in pyDatalog
        pyDatalog.load(remove_rule_statement)

    # TODO: remove this, put the docstring in run_query somehow
    def print_query(self, query: Query):
        """
        queries pyDatalog and saves the resulting string to the prints buffer (to get it use flush_prints_buffer())
        the resulting string is a table that contains all of the resulting tuples of the query.
        the headers of the table are the free variables used in the query.
        above the table there will be a title that contains the query as it was written by the user

        for example:

        printing results for query 'lecturer_of(X, "abigail")':
          X
-       -------
        linus
        walter

        there are two cases where a table cannot be printed:
        1. the query returned no results. in this case '[]' will be printed
        2. the query returned a single empty tuple, in this case '[()]' will be printed

        Args:
            query: a query for pyDatalog
        """
        raise NotImplementedError
        # # TODO `get_query_results` starts here
        # # get the results of the query
        # query_results = self.query(query)
        #
        # # check for the special conditions for which we can't print a table: no results were returned or a single
        # # empty tuple was returned
        # no_results = len(query_results) == 0
        # result_is_single_empty_tuple = len(query_results) == 1 and len(query_results[0]) == 0
        # if no_results:
        #     query_result_string = '[]'
        # elif result_is_single_empty_tuple:
        #     query_result_string = '[()]'
        #
        # else:
        #     # query results can be printed as a table
        #     # convert the resulting tuples to a more organized format
        #     formatted_results = []
        #     for result in query_results:
        #         # we saved spans as tuples of length 2 in pyDatalog, convert them back to spans so when printed,
        #         # they will be printed as a span instead of a tuple
        #         converted_span_result = [Span(term[0], term[1]) if (isinstance(term, tuple) and len(term) == 2)
        #                                  else term
        #                                  for term in result]
        #
        #         formatted_results.append(converted_span_result)
        #
        #     # get the free variables of the query, they will be used as headers
        #     query_free_vars = [term for term, term_type in zip(query.term_list, query.type_list)
        #                        if term_type is DataTypes.free_var_name]
        #
        #     # TODO `get_query_results` ends here
        #
        #     # get the query result as a table
        #     query_result_string = tabulate(formatted_results, headers=query_free_vars, tablefmt='presto',
        #                                    stralign='center')
        #
        # query_title = f"printing results for query '{query}':"
        #
        # # combine the title and table to a single string and save it to the prints buffer
        # final_result_string = f'{query_title}\n{query_result_string}\n'
        # self.prints_buffer.append(final_result_string)

    def query(self, query: Query):
        """
        Args:
            query: a query for pyDatalog

        Returns: a list of tuples that are the query's results
        """

        # create the query. note that we don't use a question mark when we expect pyDatalog to return the query's
        # results instead of printing them. the syntax is 'some_relation(term_list)' (a normal relation representation)
        query_statement = self._get_relation_string(query)

        if self.debug:
            self.prints_buffer.append(f'query: {query_statement}')

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

    def add_rule(self, rule_head: Relation, rule_body_relation_list: List[Relation]):
        """
        add a rule to the pydatalog engine.
        only normal relations are allowed in the rule body

        Args:
            rule_head: a relation that defines the rule head
            rule_body_relation_list: a list of relations that defines the rule body
        """

        # get a string that represents the rule in pyDatalog
        rule_head_string = self._get_relation_string(rule_head)
        rule_body_relation_strings = [self._get_relation_string(relation) for relation in rule_body_relation_list]
        rule_body_string = " & ".join(rule_body_relation_strings)
        rule_string = f'{rule_head_string} <= {rule_body_string}'

        if self.debug:
            self.prints_buffer.append(rule_string)

        # add the rule to pyDatalog
        pyDatalog.load(rule_string)

    def compute_ie_relation(self, ie_relation: IERelation, ie_func: IEFunction,
                            bounding_relation: Relation):
        """
        computes an information extraction relation, returning the result as a normal relation.
        for more details see RgxlogEngineBase.compute_ie_relation

        Args:
            ie_relation: an ie relation that determines the input and output terms of the ie function
            ie_func: the ie function that will be used to compute the ie relation
            bounding_relation: a relation that contains the inputs for ie_funcs. the actual input needs to be
            queried from it

        Returns: a normal relation that contains all of the resulting tuples in the rgxlog engine
        """
        ie_relation_name = ie_relation.relation_name

        # create the input relation for the ie function, and also declare it inside pyDatalog
        input_relation_arity = len(ie_relation.input_term_list)
        input_relation_name = self._create_new_temp_relation(input_relation_arity, name=f'{ie_relation_name}_input')
        input_relation = Relation(input_relation_name, ie_relation.input_term_list, ie_relation.input_type_list)

        # create the output relation for the ie function, and also declare it inside pyDatalog
        output_relation_arity = len(ie_relation.output_term_list)
        output_relation_name = self._create_new_temp_relation(output_relation_arity, name=f'{ie_relation_name}_output')
        output_relation = Relation(output_relation_name, ie_relation.output_term_list, ie_relation.output_type_list)

        # define the ie input relation
        if bounding_relation is None:
            # special case where the ie relation is the first rule body relation
            # in this case, the ie input relation is defined exclusively by constant terms, i.e, by a single tuple
            # add that tuple as a fact to the input relation
            self.add_fact(
                AddFact(input_relation.relation_name, ie_relation.input_term_list, ie_relation.input_type_list))
        else:
            # filter the bounding relation into the input relation using a rule.
            self.add_rule(input_relation, [bounding_relation])

        # get a list of inputs to the ie function.
        ie_inputs = self._get_all_relation_tuples(input_relation)

        # get the schema for the ie outputs
        ie_output_schema = ie_func.get_output_types(output_relation_arity)

        # run the ie function on each input and process the outputs
        for ie_input in ie_inputs:

            # run the ie function on the input, resulting in a list of tuples
            ie_outputs = ie_func.ie_function(*ie_input)
            # process each ie output and add it to the output relation
            for ie_output in ie_outputs:
                # TODO@niv: i don't like this, imo we should check if it's iterable, and if not, put a list around it
                ie_output = list(ie_output)

                # assert the ie output is properly typed
                self._assert_ie_output_properly_typed(ie_input, ie_output, ie_output_schema, ie_relation)

                # the user is allowed to represent a span in an ie output as a tuple of length 2
                # convert said tuples to spans
                ie_output = [Span(term[0], term[1]) if (isinstance(term, tuple) and len(term) == 2)
                             else term
                             for term in ie_output]

                # add the output as a fact to the output relation
                # TODO@niv: dean, this acts a set (ignores repetitions, e.g. 'a','a', 'aa' becomes 'a','aa').
                #  is that ok?
                if len(ie_output) != 0:
                    output_fact = AddFact(output_relation.relation_name, ie_output, ie_output_schema)
                    self.add_fact(output_fact)

        # create and return the result relation. it's a relation that is the join of the input and output relations
        result_relation = self.join_relations([input_relation, output_relation], name=ie_relation_name)
        return result_relation

    def join_relations(self, relation_list: List[Relation], name=""):
        """
        perform a join between all of the relations in the relation list and saves the result to a new relation.
        the results of the join are filtered so they only include columns in the relations that were defined by
        a free variable term.
        all of the relation in relation_list must be normal (not ie relations)

        for an example and more details see RgxlogEngineBase.join_relations

        Args:
            relation_list: a list of normal relations
            name: a name for the joined relation (will be used as a part of a temporary relation name)

        Returns: a new relation as described above
        """

        # get all of the free variables in all of the relations, they'll serve as the terms of the joined relation
        free_var_sets = [get_output_free_var_names(relation, 'relation') for relation in relation_list]
        free_vars = set().union(*free_var_sets)
        joined_relation_terms = list(free_vars)

        # get the type list of the joined relation (all of the terms are free variables)
        joined_relation_arity = len(joined_relation_terms)
        joined_relation_types = [DataTypes.free_var_name] * joined_relation_arity

        # declare the joined relation in pyDatalog and get its name
        joined_relation_name = self._create_new_temp_relation(joined_relation_arity, name=name)

        # created a structured node of the joined relation
        joined_relation = Relation(joined_relation_name, joined_relation_terms, joined_relation_types)

        # use a rule to filter the tuples of the relations in relation_list into the joined relation
        self.add_rule(joined_relation, relation_list)

        return joined_relation

    def _get_term_string(self, term, term_type):
        """
        the pyDatalog execution engine receives instructions via strings.
        return a string representation of a term in pyDatalog.
        Args:
            term: a term of any type
            term_type: the type of the term

        Returns: a string representation of the term in pyDatalog
        """
        if term_type is DataTypes.string:
            # add quotes to strings to avoid pyDatalog thinking a string is a variable
            return f"\"{term}\""
        elif term_type is DataTypes.span:
            return self._get_span_string(term)
        else:
            return str(term)

    @staticmethod
    def _get_span_string(span: Span):
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

    def _get_relation_string(self, relation: Relation):
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
        pydatalog_string_terms = [self._get_term_string(term, term_type)
                                  for term, term_type in zip(relation.term_list, relation.type_list)]
        pydatalog_string_term_list = ', '.join(pydatalog_string_terms)

        # create a string representation of the relation in pydatalog and return it
        pydatalog_string_relation = f"{relation.relation_name}({pydatalog_string_term_list})"
        return pydatalog_string_relation

    def _get_all_relation_tuples(self, relation: Relation) -> List[Tuple]:
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

    def _create_new_temp_relation(self, arity, name=""):
        """
        declares a new temporary relation with the requested arity in pyDatalog
        note that the relation's schema is not needed as there's no typechecking in pyDatalog

        Args:
            arity: the temporary relation's arity (needed for declaring the new relation inside pyDatalog)
            name: will be used as a part of the temporary relation's name. for example for the name 'RGX',
            the temporary relation's name could be __rgxlog__RGX_0

        Returns: the new temporary relation's name
        """

        if len(name) != 0:
            # if the temporary relation should have a name, add an underscore to separate the name from the id
            name = f'{name}_'

        # create the name of the new temporary relation
        temp_relation_id = next(self.temp_relation_id_counter)
        temp_relation_name = f'__rgxlog__{name}{temp_relation_id}'

        # in pyDatalog there's no typechecking so we just need to make sure that the schema has the correct arity
        temp_relation_schema = [DataTypes.free_var_name] * arity

        # create the declaration.
        temp_relation_decl = RelationDeclaration(temp_relation_name, temp_relation_schema)

        # declare the relation in pyDatalog, and return its name
        self.declare_relation(temp_relation_decl)
        return temp_relation_name

    @staticmethod
    def _assert_ie_output_properly_typed(ie_input, ie_output, ie_output_schema, ie_relation):
        """
        even though rgxlog performs typechecking during the semantic checks phase, information extraction functions
        are written by the users and could yield results that are not properly typed.
        this method asserts an information extraction function's output is properly typed

        Args:
            ie_input: the input of the ie function (used in the exception when the type check fails)
            ie_output: an output of the ie function
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
                                f'with the input {ie_input}\n'
                                f'failed because one of the outputs had an unsupported term type\n'
                                f'the output: {ie_output}\n'
                                f'the invalid term: {output_term}\n'
                                f'the invalid term type: {type(output_term)}\n'
                                f'note that only strings, spans and integers are supported\n'
                                f'spans can be represented as a tuple of length 2 or as a datatypes.span instance')
            ie_output_term_types.append(output_type)

        # assert that the ie output is properly typed
        ie_output_is_properly_typed = ie_output_term_types == list(ie_output_schema)
        if not ie_output_is_properly_typed and len(ie_output_term_types) != 0:
            raise Exception(f'executing ie relation {ie_relation}\n'
                            f'with the input {ie_input}\n'
                            f'failed because one of the outputs had unexpected term types\n'
                            f'the output: {ie_output}\n'
                            f'the output term types: {ie_output_term_types}\n'
                            f'the expected types: {ie_output_schema}')


class ExecutionBase(ABC):
    """
    Abstraction for a class that gets a term graph and executes it
    """

    def __init__(self, term_graph, symbol_table, rgxlog_engine):
        """
        Args:
            term_graph: a term graph to execute
            symbol_table: a symbol table
            rgxlog_engine: a rgxlog engine that will be used to execute the term graph
        """
        super().__init__()
        self.term_graph = term_graph
        self.symbol_table = symbol_table
        self.rgxlog_engine = rgxlog_engine

    @abstractmethod
    def execute(self) -> Tuple[Query, List]:
        """
        executes the term graph
        """
        pass


class GenericExecution(ExecutionBase):
    """
    Executes a term graph
    this execution is generic, meaning it does not require any specific kind of term graph, symbol table or
    rgxlog engine in order to work.
    this execution performs no special optimization and merely serves as an interface between the term graph
    and the rgxlog engine.
    The only exception for this is the 'rule' execution, you can read more about it in the utility method:
    GenericExecution.__execute_rule_aux()
    """

    def __init__(self, term_graph: TermGraphBase, symbol_table: SymbolTableBase, rgxlog_engine: RgxlogEngineBase):
        super().__init__(term_graph, symbol_table, rgxlog_engine)

    def execute(self) -> Tuple[Query, List]:
        term_graph = self.term_graph
        rgxlog_engine = self.rgxlog_engine
        exec_result = None

        # get the term ids. note that the order of the ids does not actually matter as long as the statements
        # are ordered the same way as they were in the original program
        term_ids = term_graph.post_order_dfs()

        # execute each non computed statement in the term graph
        for term_id in term_ids:

            term_attrs = term_graph.get_term_attributes(term_id)

            if term_attrs['state'] is EvalState.COMPUTED:
                continue

            # the term is not computed, get its type and compute it accordingly
            term_type = term_attrs['type']

            if term_type == "relation_declaration":
                relation_decl = term_attrs['value']
                rgxlog_engine.declare_relation(relation_decl)

            elif term_type == "add_fact":
                fact = term_attrs['value']
                rgxlog_engine.add_fact(fact)

            elif term_type == "remove_fact":
                fact = term_attrs['value']
                rgxlog_engine.remove_fact(fact)

            elif term_type == "query":
                query = term_attrs['value']
                # TODO: change this - enable returning the pre-formatted query
                # currently only print queries are supported
                exec_result = (query, rgxlog_engine.query(query))

            elif term_type == "rule":
                self._execute_rule_aux(term_id)

            # statement was executed, mark it as "computed"
            term_graph.set_term_attribute(term_id, 'state', EvalState.COMPUTED)

        return exec_result

    def _execute_rule_aux(self, rule_term_id):
        """
        rule_term_id is expected to be a root of a subtree in the term graph that represents a single rule
        the children of rule_term_id node should be:
        1. a rule head relation node
        2. a rule body relation list, who's children are all the body relations of the rule

        This rule execution assumes that a previous pass reordered the rule body relations in a way that
        each relation's input free variables (should they exist) are bounded by relations to the relation's
        left. lark_passes.ReorderRuleBody is an example for such a pass.

        the following algorithm is used:

        1. for each rule body relation (from left to right):

        a. compute the relation.

        b. if it is the leftmost relation in the rule body, save the relation from step 1 as an intermediate relation,
        else join the relation from step 1 with the intermediate relation, and save the result as the new intermediate
        relation.

        2. define the rule head relation by filtering the resulting intermediate relation from step 1 into it

        example:

        A(X) <- B(Z), C(X), D(X)->(X,Y)  # original input

        these are the steps that will be taken to compute A(X):
        temp1(Z) <- B(Z)
        temp2(X) <- C(X)
        temp3(Z,X) <- temp1(Z), temp2(X)  # join the results
        input_d(X) <- temp3(Z,X)  # temp3 is used as a bounding relation for input_d
        output_d(X,Y) <- results from running 'D' ie func on all of the tuples in input_d
        temp4(X,Y) <- input_d(X), output_d(X,Y) # the final result from computing the 'D' ie relation
        temp5(X,Y,Z) <- temp3(Z,X), temp4(X,Y)  # join the results
        A(X) <- temp5(X,Y,Z)  # filter the results into the head relation

        note that in this implementation we don't actually compute normal relations, we will just use them
        as they are defined. (for example the step 'temp1(Z) <- B(Z)' is skipped and we just use B(Z) as the
        intermediate relation)
        """
        """
        TODO possible optimizations:
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
        b. using the dependency graph, compute relations in a way that you only join results to a 
        temporary relation when you have to.

        for example for the rule A(Z) <- C(X),D(X,Y),B(Z),G(Z)->(Z),F(Y,Z)->(Y,Z):
        a. the bounding graph is:
            C -> D
            B -> G
            G -> F
            D -> F
        b. we could for example compute this rule in the following way:
        * compute C, use it to compute D, join the results to temp1
        * compute B, use it to compute G, join the results to temp2
        * join temp1 and temp2 to temp3
        * use temp3 to compute F, join the result and temp3 to temp4
        * filter temp4 into the rule head relation A(Z)
        """
        term_graph = self.term_graph
        rgxlog_engine = self.rgxlog_engine
        symbol_table = self.symbol_table

        rule_head_id, rule_body_id = term_graph.get_children(rule_term_id)
        body_relation_id_list = term_graph.get_children(rule_body_id)

        # compute the rule body relations from left to right and save the intermediate results in
        # 'intermediate_relation'
        intermediate_relation = None
        for relation_id in body_relation_id_list:

            relation_term_attrs = term_graph.get_term_attributes(relation_id)

            relation = relation_term_attrs['value']
            relation_type = relation_term_attrs['type']

            # compute the relation in the engine if needed
            if relation_type == 'relation':
                # no special computation is required, take the relation as is
                result_relation = relation
            elif relation_type == 'ie_relation':
                # compute the ie relation
                ie_func_data = symbol_table.get_ie_func_data(relation.relation_name)
                result_relation = rgxlog_engine.compute_ie_relation(relation, ie_func_data,
                                                                    intermediate_relation)
            else:
                raise Exception(f'unexpected relation type: {relation_type}')

            # save the resulting relation in the term graph
            term_graph.set_term_attribute(relation_id, 'value', result_relation)

            # join the resulting relation with the intermediate relation
            if intermediate_relation is None:
                intermediate_relation = result_relation
            else:
                intermediate_relation = rgxlog_engine.join_relations(
                    [intermediate_relation, result_relation], name="temp_join")

        # declare the rule head in the rgxlog engine
        rule_head_attrs = term_graph.get_term_attributes(rule_head_id)
        rule_head_relation = rule_head_attrs['value']
        rule_head_declaration = RelationDeclaration(
            rule_head_relation.relation_name, symbol_table.get_relation_schema(rule_head_relation.relation_name))
        rgxlog_engine.declare_relation(rule_head_declaration)

        # define the rule head in the rgxlog engine by filtering the tuples of the intermediate relation into it
        rgxlog_engine.add_rule(rule_head_relation, [intermediate_relation])
