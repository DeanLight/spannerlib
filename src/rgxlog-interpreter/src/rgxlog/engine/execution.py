"""
this modules contains implementations of 'RgxlogEngineBase' which is an abstraction for the rgxlog engine
and also implementations of 'ExecutionBase' which serves as an abstraction for an interface between a term graph
and an rgxlog engine.
"""

# TODO@niv: convert all docstring to epytext (@param)
# TODO@niv remove import * where not needed
import os
import sqlite3 as sqlite
import tempfile
from abc import ABC, abstractmethod
from itertools import count
from typing import List, Tuple, Optional, Dict, Set, Union

from pyDatalog import pyDatalog

from rgxlog.engine.datatypes.ast_node_types import *
from rgxlog.engine.datatypes.primitive_types import Span
from rgxlog.engine.ie_functions.ie_function_base import IEFunction
from rgxlog.engine.state.symbol_table import SymbolTableBase
from rgxlog.engine.state.term_graph import EvalState, TermGraphBase, NetxTermGraph
from rgxlog.engine.utils.general_utils import get_output_free_var_names, get_free_var_to_relations_dict

VALUE_ATTRIBUTE = 'value'
OUT_REL_ATTRIBUTE = "output_rel"

JOIN_PREFIX = "join"
COPY_PREFIX = "copy"
RESERVED_RELATION_PREFIX = "__rgxlog__"

DATATYPE_TO_SQL_TYPE = {DataTypes.string: "TEXT", DataTypes.integer: "INTEGER", DataTypes.span: "TEXT"}
RELATION_COLUMN_PREFIX = "col"

# rgx constants
FALSE_VALUE = []
TRUE_VALUE = [tuple()]


class RgxlogEngineBase(ABC):
    """
    An abstraction for a rgxlog execution engine
    """

    def __init__(self, debug=False):
        super().__init__()
        self.debug = debug
        self.debug_buffer = []

        if self.debug:
            print("debug mode is on - a lot of extra info will be printed")

    def flush_debug_buffer(self) -> str:
        """
        clear and return the debug strings, only relevant when `debug=True`

        Returns: a single string that represents all of the `debug_buffer` content. this string should be printed
        by the caller
        """
        ret_string = '\n'.join(self.debug_buffer)
        self.debug_buffer.clear()
        return ret_string

    @abstractmethod
    def declare_relation(self, relation_decl):
        """
        declares a relation in the rgxlog engine

        @param relation_decl: a relation declaration
        """
        pass

    @abstractmethod
    def add_fact(self, fact):
        """
        add a fact to the rgxlog engine

        @param fact: the fact to be added
        """
        pass

    @abstractmethod
    def remove_fact(self, fact):
        """
        remove a fact from the rgxlog engine

        @param fact: the fact to be removed
        """
        pass

    @abstractmethod
    def remove_rule(self, rule: str):
        """
        remove a rule from the rgxlog engine

        @param rule: the rule to be removed
        """
        pass

    @abstractmethod
    def query(self, query):
        """
        queries the rgxlog engine

        @param query: a query for the rgxlog engine
        @return: a list of tuples that are the query's results
        """
        pass

    @abstractmethod
    def add_rule(self, rule_head, rule_body_relation_list):
        """
        add a rule to the rgxlog engine.
        this method assumes that all the relations in the rule body are normal relations (non ie relations)
        this means that the rule will be added as it is, without any micro operations (e.g. computing an ie relation)

        @param rule_head: a relation that defines the rule head
        @param rule_body_relation_list: a list of relations that defines the rule body
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

        @param ie_relation: an ie relation that determines the input and output terms of the ie function
        @param ie_func_data: the data for the ie function that will be used to compute the ie relation
        @param bounding_relation: a relation that contains the inputs for ie_funcs. the actual input needs to be
                                  queried from it
        @return: a normal relation that contains all of the resulting tuples in the rgxlog engine
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

        @param relation_list: a list of normal relations
        @param name: the name for the joined relation (to be used as a part of a temporary relation name)
        @return: a new relation as described above
        """
        pass

    @staticmethod
    def clear_all():
        """
        removes all facts and clauses from the engine
        """
        pass

    @staticmethod
    def _get_span_string(span: Span):
        """
        convert Span(start,end) to string("[start, end)")

        @param span: a span object
        @return: a string representation of the span
        """

        span_string = f'[{span.span_start}, {span.span_end})'
        return span_string

    @abstractmethod
    def _convert_relation_term_to_string(self, datatype: DataTypes, term):
        """
        return the string representation of a relation term, e.g. "[1,4)"

        :param datatype: the type of the term
        :param term: the term object itself
        :return: string representation
        """
        pass

    def _get_relation_string(self, relation: Relation):
        """
        return the string representation of a relation which has terms, e.g. REL(3, "hello")

        @param relation: a relation object
        @return: a string representation of the relation
        """
        terms_string = ', '.join([self._convert_relation_term_to_string(term, term_type)
                                  for term, term_type in zip(relation.term_list, relation.type_list)])

        final_string = f"{relation.relation_name}({terms_string})"
        return final_string

    @abstractmethod
    def remove_all_rules(self, rule_head):
        pass

    def operator_select(self, relation: Relation, select_info: Set[Tuple[int, int, DataTypes]]) -> Relation:
        """

        @param relation: the relation from which we select tuples
        @param select_info: set of tuples. each tuple contains the index of the column, the value to select
                            and the type of the column.

        @return: a filtered relation
        """
        # TODO@niv: i'm talking about the relational algebra operator, which is actually `WHERE`
        pass

    def operator_join(self, relations: List[Relation]) -> Relation:
        pass

    def operator_project(self, relation: Relation, project_vars: Set[str]) -> Relation:
        """

        @param relation: the relation on which we project.
        @param project_vars: a set of variables on which we project.
        @return: the projected relation
        """
        # TODO@niv: this is basically `SELECT`
        pass

    def operator_union(self, relations: List[Relation]) -> Relation:
        """

        @param relations: a list of relations to union.
        @note: you can assume that all the relation have the same set of free_vars,
               but not necessarily in the same order.
        @return: the unionised relation.
        """
        pass

    def operator_difference(self):
        pass

    def operator_product(self):
        pass

    def operator_copy(self, old_rel) -> Relation:
        """
        Copies computed_relation to rule_relation.
        """
        pass


class SqliteEngine(RgxlogEngineBase):
    # TODO@niv:
    """
    general idea (i took this from `execution.py:970` we need to create intermediate tables for everything we do.
    for example, let's see this rule:
    `very_cool_and_even(X) <- cool(X), awesome(X),  get_number(X) -> (Y), even(Y)`

    we need to create a few tables:
    very_cool(X) <- cool(X), awesome(X)  # SQL union
    input_get_number(X) <- very_cool(X)  # SQL select
    get_number_pairs(X,Y) = run `get_number` on every X, output (X,Y)  # SQL select and then for loop with IE func
    final_join_relations(X,Y) <- very_cool(X), get_number_pairs(X,Y), even(Y)  # SQL union and project/rename

    and finally:
    very_cool_and_even(X) <- final_join_relations(X,Y)  # SQL project/rename

    notice that all we need for those is a few SQL selects/unions, and running IE functions over an SQL table.
    """

    def __init__(self, debug=False, database_name=None):
        """
        @param debug: print stuff related to the inner workings of the engine
        @param database_name: open an existing database instead of a new one

        creates/opens an SQL database file + connection
        """
        super().__init__(debug=debug)
        self.temp_relation_id_counter = count()
        self.rules_history = dict()

        if database_name:
            if not os.path.isfile(database_name):
                raise IOError(f"database file: {database_name} was not found")
            self.db_filename = database_name
        else:
            temp_db_file = tempfile.NamedTemporaryFile(delete=False)
            temp_db_file.close()
            self.db_filename = temp_db_file.name

        if self.debug:
            print(f"using database file: {self.db_filename}")

        self.sql_conn = sqlite.connect(self.db_filename)
        self.sql_cursor = self.sql_conn.cursor()

    def add_fact(self, fact: AddFact):
        """
        add a row into an existing table
        :param fact:
        :return:
        """
        sql_command = f"INSERT INTO {fact.relation_name} ("
        num_types = len(fact.type_list)
        for i in range(num_types):
            if i > 0:
                sql_command += ", "
            sql_command += f"{RELATION_COLUMN_PREFIX}{i}"
        sql_command += ") VALUES ("
        sql_command += ", ".join(["?"] * num_types)
        sql_command += ")"

        sql_term_list = [self._convert_relation_term_to_string(datatype, term) for datatype, term in
                         zip(fact.type_list, fact.term_list)]
        self.sql_cursor.execute(sql_command, sql_term_list)

    def remove_fact(self, fact: RemoveFact):
        # use a `DELETE` statement
        sql_terms = fact.term_list  # add quotes here

        sql_command = (f"DELETE FROM {fact.relation_name} WHERE"
                       f"(t1='{sql_terms[0]}' AND t2='{sql_terms[1]}')")
        self.sql_cursor.execute(sql_command)

    def add_rule(self, rule_head, rule_body_relation_list):
        # we need to maintain the tables that resulted from a rule, right? this means that
        # we need to recalculate the rule table every time it is called. maybe we should store some
        # metadata, like the last change to the tables we depend on.
        pass

    def remove_rule(self, rule: str):
        # we just need to delete the table that the rule created
        pass

    def remove_all_rules(self, rule_head):
        pass

    def query(self, query: Query, allow_duplicates=False):
        """
        outputs a preformatted query result, e.g. [("a",5),("b",6)]
        :param allow_duplicates: if True, query result may contain duplicate values
        :param query: the query to be performed
        :return: a query results which is True, False, or a list of tuples
        """
        # note: this is an engine query (which asks a single question),
        # not a session query (which can do anything).
        # so we only need a `SELECT` statement here.
        query_relation = query.relation_name
        query_where_conditions = self._get_where_string(query.term_list, query.type_list)
        query_free_var_indexes = self._get_free_variable_indexes(query.type_list)
        has_free_vars = bool(query_free_var_indexes)
        unique_string = "" if allow_duplicates else "DISTINCT"

        if has_free_vars:
            # free variables exist - return list/False
            query_cols = [f"{RELATION_COLUMN_PREFIX}{free_var_index}" for free_var_index in query_free_var_indexes]
            query_select_string = f"{', '.join(query_cols)}"
            sql_command = f"SELECT {unique_string} {query_select_string} FROM {query_relation} {query_where_conditions}"
        else:
            # no free variables - only return True/False
            sql_command = f"SELECT * FROM {query_relation} {query_where_conditions}"

        if self.debug:
            self.debug_buffer.append(f'query: {sql_command}')

        self.sql_cursor.execute(sql_command)
        query_result = self.sql_cursor.fetchall()
        if (not has_free_vars) and query_result != FALSE_VALUE:
            # if there are no free variables, we should just return a true/false value
            query_result = TRUE_VALUE

        return query_result

    def get_base(self, parse_graph, base_id):
        """
        get an existing base (not IE) relation from the engine
        @param parse_graph:
        @param base_id:
        @return:
        """
        pass

    def _create_unique_relation(self, arity, prefix=""):
        """
        declares a new temporary relation with the requested arity in SQL

        @param arity: the temporary relation's arity
        @param prefix: will be used as a part of the temporary relation's name.
                for example: prefix='join' -> full name = __rgxlog__join{counter}
        @return: the new temporary relation's name
        """
        # create the name of the new temporary relation
        temp_relation_id = next(self.temp_relation_id_counter)
        temp_relation_name = f'{RESERVED_RELATION_PREFIX}{prefix}{temp_relation_id}'

        # in SQLite there's no typechecking so we just need to make sure that the schema has the correct arity
        temp_relation_schema = [DataTypes.free_var_name] * arity

        # create the declaration
        temp_relation_decl = RelationDeclaration(temp_relation_name, temp_relation_schema)

        # create the relation's SQL table, and return its name
        self.declare_relation(temp_relation_decl)
        return temp_relation_name

    def compute_ie_relation(self, ie_relation: IERelation, ie_func: IEFunction,
                            bounding_relation: Optional[Relation]) -> Relation:
        """
        computes an information extraction relation, returning the result as a normal relation.
        for more details see RgxlogEngineBase.compute_ie_relation.

        @param ie_relation: an ie relation that determines the input and output terms of the ie function
        @param ie_func: the ie function that will be used to compute the ie relation
        @param bounding_relation: a relation that contains the inputs for ie_funcs. the actual input needs to be
                                  queried from it
        @return: a normal relation that contains all of the resulting tuples in the rgxlog engine
        """

        ie_relation_name = ie_relation.relation_name

        # create the output relation for the ie function, and also declare it inside SQL
        output_relation_arity = len(ie_relation.output_term_list)
        output_relation_name = self._create_unique_relation(output_relation_arity,
                                                            prefix=f'{ie_relation_name}_output')
        output_relation = Relation(output_relation_name, ie_relation.output_term_list, ie_relation.output_type_list)

        # define the ie input relation
        if bounding_relation is None:
            # special case where the ie relation is the first rule body relation
            # in this case, the ie input relation is defined exclusively by constant terms, i.e, by a single tuple
            # add that tuple as a fact to the input relation
            # create the input relation for the ie function, and also declare it inside SQL
            input_relation_arity = len(ie_relation.input_term_list)
            input_relation_name = self._create_unique_relation(input_relation_arity,
                                                               prefix=f'{ie_relation_name}_input')
            input_relation = Relation(input_relation_name, ie_relation.input_term_list, ie_relation.input_type_list)
            self.add_fact(AddFact(input_relation.relation_name, ie_relation.input_term_list,
                                  ie_relation.input_type_list))
        else:
            # filter the bounding relation into the input relation using a rule.
            # TODO@niv: i think we don't need to add_rule here because we connect the nodes in the graph
            #  when we parse the whole rule (and not just the ie_relation).
            input_relation = bounding_relation
            # TODO@niv: might have to add constant columns here. we need a new operator for that

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
                # the output should be a tuple, but if a single value is returned, we accept it as well
                if isinstance(ie_output, str) or isinstance(ie_output, int) or isinstance(ie_output, Span):
                    ie_output = [ie_output]
                else:
                    ie_output = list(ie_output)

                # assert the ie output is properly typed
                self._assert_ie_output_properly_typed(ie_input, ie_output, ie_output_schema, ie_relation)

                # the user is allowed to represent a span in an ie output as a tuple of length 2
                # convert said tuples to spans
                ie_output = [Span(term[0], term[1]) if (isinstance(term, tuple) and len(term) == 2)
                             else term
                             for term in ie_output]

                # add the output as a fact to the output relation
                # notice - repetitions are ignored here (results are in a set)
                if len(ie_output) != 0:
                    output_fact = AddFact(output_relation.relation_name, ie_output, ie_output_schema)
                    self.add_fact(output_fact)

        # create and return the result relation. it's a relation that is the join of the input and output relations
        result_relation = self.operator_join([input_relation, output_relation], prefix=ie_relation_name)
        return result_relation

    def _get_all_relation_tuples(self, relation: Relation) -> List[Tuple]:
        """
        @param relation: a relation to be queried
        @return: all the tuples of 'relation' as a list of tuples
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

    @staticmethod
    def _assert_ie_output_properly_typed(ie_input, ie_output, ie_output_schema, ie_relation):
        """
        even though rgxlog performs typechecking during the semantic checks phase, information extraction functions
        are written by the users and could yield results that are not properly typed.
        this method asserts an information extraction function's output is properly typed

        @param ie_input: the input of the ie function (used in the exception when the type check fails)
        @param ie_output: an output of the ie function
        @param ie_output_schema: the expected schema for ie_output
        @param ie_relation: the ie relation for which the output was computed (will be used to print an exception
            in case the output is not properly typed)
        @raise Exception: if there is output term of an unsupported type or the output relation is not properly typed.
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

    def declare_relation(self, relation_decl: RelationDeclaration) -> None:
        """
        declares a relation as an SQL table, whose types are named t0, t1, ...

        @param relation_decl: the declaration info
        @return: None
        """
        # create the relation table. we don't use an id because it would allow inserting the same values twice
        # TODO@niv: to ignore duplicates, we can either use UNIQUE when creating the table, or DISTINCT when selecting.
        #  we should pick one.
        sql_command = f"CREATE TABLE {relation_decl.relation_name} ("

        # TODO@niv: sqlite can guess datatypes. if this causes bugs, use `{self._datatype_to_sql_type(relation_type)}`.
        for i, relation_type in enumerate(relation_decl.type_list):
            if i > 0:
                sql_command += ", "
            sql_command += f"{RELATION_COLUMN_PREFIX}{i}"
        sql_command += ")"

        self.sql_cursor.execute(sql_command)

        # save to file
        self.sql_conn.commit()

    def operator_select(self):
        # TODO@niv: i'm talking about the relational algebra operator, which is actually `WHERE`
        pass

    def operator_join(self, relations: List[Relation], prefix="") -> Relation:
        # sql_command = "SELECT ..."
        # for relation in relation_list:
        #     sql_command += "INNER JOIN ... ON ... X=X"
        # temp_relation = ... # execute sql command
        # return Relation(temp_relation, ...)
        """
        perform a join between all of the relations in the relation list and saves the result to a new relation.
        the results of the join are filtered so they only include columns in the relations that were defined by
        a free variable term.
        all of the relations in relation_list must be normal (not ie relations)

        for an example and more details see RgxlogEngineBase.join_relations

        @param relations: a list of normal relations
        @param prefix: a prefix for the name of the joined relation
        @return: a new relation as described above
        """

        assert len(relations) > 0, "can't join an empty list"
        if len(relations) == 1:
            return self.operator_copy(relations[0])

        # get all of the free variables in all of the relations, they'll serve as the terms of the joined relation
        free_var_sets = [get_output_free_var_names(relation) for relation in relations]
        free_vars = set().union(*free_var_sets)
        joined_relation_terms = list(free_vars)

        # get the type list of the joined relation (all of the terms are free variables)
        joined_relation_arity = len(joined_relation_terms)
        joined_relation_types = [DataTypes.free_var_name] * joined_relation_arity

        # declare the joined relation in sql and get its name
        joined_relation_name = self._create_unique_relation(joined_relation_arity, prefix=f"{JOIN_PREFIX}_{prefix}")

        # created a structured node of the joined relation
        joined_relation = Relation(joined_relation_name, joined_relation_terms, joined_relation_types)

        # perform sql join
        var_dict = get_free_var_to_relations_dict(set(relations))

        sql_command = f"INSERT INTO {joined_relation_name} SELECT "
        on_conditions = "ON "

        # iterate over the free_vars and do 2 things:
        for i, free_var in enumerate(joined_relation_terms):
            free_var_pairs: List[Tuple[str, int]] = var_dict[free_var]
            first_pair, other_pairs = free_var_pairs[0], free_var_pairs[1:]

            if i > 0:
                sql_command += ", "
            relation_that_contains_free_var_name, first_index = first_pair
            new_col_name = self._get_col_name(i)
            first_col_name = self._get_col_name(first_index)

            # 1. name the new columns. the columns should be named col0, col1, etc.
            sql_command += f"{relation_that_contains_free_var_name}.{first_col_name} AS {new_col_name}"
            # 2. create the comparison between all of them, using `ON`
            for j, (second_relation_name, second_index) in enumerate(other_pairs):
                if j > 0:
                    on_conditions += "AND "
                second_col_name = self._get_col_name(second_index)
                on_conditions += (f"{relation_that_contains_free_var_name}.{first_col_name}="
                                  f"{second_relation_name}.{second_col_name} ")

        # first relation - just `FROM`
        first_relation, other_relations = relations[0], relations[1:]
        sql_command += f" FROM {first_relation.relation_name} "

        # for every next relation: `INNER JOIN`
        for relation in other_relations:
            sql_command += f"INNER JOIN {relation.relation_name} "

        # add the join conditions (`ON`)
        sql_command += on_conditions

        return joined_relation

    def operator_select(self, relation: Relation, select_info: Set[Tuple[int, int, DataTypes]]) -> Relation:
        """

        @param relation: the relation from which we select tuples
        @param select_info: set of tuples. each tuple contains the index of the column, the value to select
                            and the type of the column.

        @return: a filtered relation
        """
        # TODO@niv: i'm talking about the relational algebra operator, which is actually `WHERE`
        pass

    def operator_project(self, relation: Relation, project_vars: Set[str]) -> Relation:
        """

        @param relation: the relation on which we project.
        @param project_vars: a set of variables on which we project.
        @return: the projected relation
        """
        # TODO@niv: this is basically `SELECT`
        pass

    def operator_union(self, relations: List[Relation]) -> Relation:
        """

        @param relations: a list of relations to union.
        @note: you can assume that all the relation have the same set of free_vars,
               but not necessarily in the same order.
        @return: the unionised relation.
        """

        # TODO@niv: sqlite `UNION`
        pass

    def operator_product(self) -> Relation:
        # TODO@niv: sqlite `CROSS JOIN`
        pass

    def operator_copy(self, src_rel: Relation) -> Relation:
        src_rel_name = src_rel.relation_name
        dest_rel_name = self._create_unique_relation(arity=len(src_rel.type_list),
                                                     prefix=f"{COPY_PREFIX}_{src_rel_name}")
        dest_rel = Relation(dest_rel_name, src_rel.term_list, src_rel.type_list)

        # sql part
        sql_command = f"INSERT INTO {dest_rel_name} SELECT * FROM {src_rel_name}"
        self.sql_cursor.execute(sql_command)

        return dest_rel

    @staticmethod
    def _datatype_to_sql_type(datatype: DataTypes):
        return DATATYPE_TO_SQL_TYPE[datatype]

    def _convert_relation_term_to_string(self, datatype: DataTypes, term):
        if datatype == DataTypes.span:
            return self._get_span_string(term)
        else:
            return term

    def __del__(self):
        self.sql_conn.close()

    @staticmethod
    def _get_col_name(col_id: int):
        return f'{RELATION_COLUMN_PREFIX}{col_id}'

    def _get_where_string(self, term_list: List, type_list: List[DataTypes]):
        """
        `where` is an sql operator which filters rows from a table.
        this method creates the string used to filter rows based on the `term_list`.
        :param term_list:
        :param type_list:
        :return:
        """
        where_string = "WHERE "
        where_conditions = []
        for col_num, term_and_term_type in enumerate(zip(term_list, type_list)):
            term, term_type = term_and_term_type
            if term_type is DataTypes.free_var_name:
                continue

            where_conditions.append(f'{self._get_col_name(col_num)} = "{term}"')

        if not where_conditions:
            return ""

        where_string += " AND ".join(where_conditions)
        return where_string

    @staticmethod
    def _get_free_variable_indexes(type_list):
        return [i for i, term_type in enumerate(type_list) if (term_type is DataTypes.free_var_name)]


class ExecutionBase(ABC):
    """
    Abstraction for a class that gets a term graph and executes it
    """

    def __init__(self, parse_graph: TermGraphBase, term_graph: NetxTermGraph,
                 symbol_table: SymbolTableBase, rgxlog_engine: RgxlogEngineBase):
        """
        @param parse_graph: a term graph to execute
        @param symbol_table: a symbol table
        @param rgxlog_engine: a rgxlog engine that will be used to execute the term graph
        """

        super().__init__()
        self.parse_graph = parse_graph
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

    def __init__(self, parse_graph: TermGraphBase, term_graph: NetxTermGraph,
                 symbol_table: SymbolTableBase, rgxlog_engine: RgxlogEngineBase):
        super().__init__(parse_graph, term_graph, symbol_table, rgxlog_engine)

    def execute(self) -> Tuple[Query, List]:
        parse_graph = self.parse_graph
        rgxlog_engine = self.rgxlog_engine
        exec_result = None

        # get the term ids. note that the order of the ids does not actually matter as long as the statements
        # are ordered the same way as they were in the original program
        term_ids = parse_graph.post_order_dfs()

        # execute each non computed statement in the term graph
        for term_id in term_ids:
            term_attrs = parse_graph[term_id]

            if term_attrs['state'] is EvalState.COMPUTED:
                continue

            # the term is not computed, get its type and compute it accordingly
            term_type = term_attrs['type']

            if term_type == "relation_declaration":
                relation_decl = term_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.declare_relation(relation_decl)

            elif term_type == "add_fact":
                fact = term_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.add_fact(fact)

            elif term_type == "remove_fact":
                fact = term_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.remove_fact(fact)

            elif term_type == "query":
                query = term_attrs[VALUE_ATTRIBUTE]
                # TODO@niv: change this - enable returning the pre-formatted query (should be possible with sql engine)
                exec_result = (query, rgxlog_engine.query(query))

            elif term_type == "rule_head":
                rule_head = term_attrs[VALUE_ATTRIBUTE]
                self.compute_rule(rule_head)
            else:
                raise TypeError("illegal engine type")

            # statement was executed, mark it as "computed"
            parse_graph.set_term_attribute(term_id, 'state', EvalState.COMPUTED)

        return exec_result

    def compute_rule(self, rule_head: Relation) -> None:
        """
        saves the rule to rules_history (used for rule deletion) and copies the table from the
        rule's child in the parse graph, which is the result of all the rule calculations
        :return:
        """
        term_graph = self.term_graph
        rgxlog_engine = self.rgxlog_engine
        rule_head_id = term_graph.get_relation_id(rule_head)
        term_ids = term_graph.post_order_dfs_from(rule_head_id)
        # TODO@niv: add var_dict here, or to term_graph
        # TODO@niv: convert output_rel to const

        for term_id in term_ids:
            term_attrs = term_graph[term_id]
            if term_attrs["state"] is EvalState.COMPUTED:
                continue

            term_type = term_attrs['type']
            existing_rel = term_attrs.get(OUT_REL_ATTRIBUTE, None)

            if term_type == "rel_base":
                # TODO@niv: get_operator?
                continue

            elif term_type == "rel_root":
                rel_in: Relation = self.get_children_relations(term_graph, term_id)[0]
                copy_rel = rgxlog_engine.operator_copy(rel_in)
                term_graph.set_term_attribute(term_id, OUT_REL_ATTRIBUTE, copy_rel)

            elif term_type == "union":
                union_rel = rgxlog_engine.operator_union(self.get_children_relations(term_graph, term_id))
                term_graph.set_term_attribute(term_id, OUT_REL_ATTRIBUTE, union_rel)

            elif term_type == "join":
                join_rel = rgxlog_engine.operator_join(self.get_children_relations(term_graph, term_id))
                term_graph.set_term_attribute(term_id, OUT_REL_ATTRIBUTE, join_rel)

            elif term_type == "project":
                output_rel: Relation = self.get_children_relations(term_graph, term_id)[0]
                project_rel = rgxlog_engine.operator_project(output_rel)
                term_graph.set_term_attribute(term_id, OUT_REL_ATTRIBUTE, project_rel)

            elif term_type == "calc":
                rel_in: Relation = self.get_children_relations(term_graph, term_id)[0]
                ie_rel_in: IERelation = term_attrs['value']
                ie_func_data = self.symbol_table.get_ie_func_data(ie_rel_in.relation_name)
                ie_rel_out = rgxlog_engine.compute_ie_relation(ie_rel_in, ie_func_data, rel_in)
                term_graph.set_term_attribute(term_id, OUT_REL_ATTRIBUTE, ie_rel_out)

            elif term_type == "select":
                output_rel = self.get_child_relation(term_id)
                select_info = term_attrs["value"]
                select_rel = rgxlog_engine.operator_select(output_rel, select_info)
                self.set_output_relation(term_id, select_rel)

            else:
                raise TypeError("illegal engine type")

            # statement was executed, mark it as "computed"
            term_graph.set_term_attribute(term_id, 'state', EvalState.COMPUTED)

        self.reset_visited_nodes(term_ids)

    def reset_visited_nodes(self, term_ids: List[int]) -> None:
        for term_id in term_ids:
            self.term_graph.set_term_attribute(term_id, "state", EvalState.NOT_COMPUTED)

    def set_output_relation(self, term_id: int, relation: Relation) -> None:
        self.term_graph.set_term_attribute(term_id, "output_rel", relation)

    def get_children_relations(self, node_id: int) -> List[Relation]:
        term_graph = self.term_graph
        relations_ids = term_graph.get_children(node_id)
        relations_nodes = [term_graph[rel_id] for rel_id in relations_ids]
        relations = [rel_node[OUT_REL_ATTRIBUTE] for rel_node in relations_nodes]
        return relations

    def get_child_relation(self, node_id: int) -> Relation:
        return self.get_children_relations(node_id)[0]


if __name__ == "__main__":
    my_engine = SqliteEngine()
    print("hello world")

    # add relation
    my_relation = RelationDeclaration("yoyo", [DataTypes.integer, DataTypes.string])
    my_engine.declare_relation(my_relation)

    # add fact
    my_fact = AddFact("yoyo", [8, "hihi"], [DataTypes.integer, DataTypes.string])
    my_engine.add_fact(my_fact)

    my_query = Query("yoyo", ["X", "Y"], [DataTypes.free_var_name, DataTypes.free_var_name])
    print(my_engine.query(my_query))


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
        @param debug: print the commands that are loaded into pyDatalog
        """
        super().__init__(debug=debug)
        self.temp_relation_id_counter = count()
        self.rules_history = dict()

    def declare_relation(self, relation_decl: RelationDeclaration):
        """
        declares a relation in the pyDatalog engine

        @param relation_decl: a relation declaration
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
        relation_decl_statement = (f'+{temp_fact_string}\n' +
                                   f'-{temp_fact_string}')

        # declare the relation in pyDatalog
        pyDatalog.load(relation_decl_statement)

    def add_fact(self, fact: AddFact):
        """
        add a fact in the pyDatalog engine

        @param fact: the fact to be added
        """
        relation_string = self._get_relation_string(fact)
        # the syntax for a 'add fact' statement in pyDatalog is '+some_relation(term_list)' create that statement
        add_fact_statement = f'+{relation_string}'
        if self.debug:
            self.debug_buffer.append(add_fact_statement)
        # add the fact in pyDatalog
        pyDatalog.load(add_fact_statement)

    def remove_fact(self, fact: RemoveFact):
        """
        remove a fact from the pyDatalog engine

        @param fact: the fact to be removed
        """
        relation_string = self._get_relation_string(fact)
        # the syntax for a 'remove fact' statement in pyDatalog is '-some_relation(term_list)' create that statement
        remove_fact_statement = f'-{relation_string}'
        if self.debug:
            self.debug_buffer.append(remove_fact_statement)
        # remove the fact in pyDatalog
        pyDatalog.load(remove_fact_statement)

    def remove_rule(self, rule: str):
        """
        remove a rule from the pyDatalog engine

        @param rule: the fact to be removed
        @raise Exception: if the rule is not inside rules_history.
        """
        # the syntax for a 'remove rule' statement in pyDatalog is '-(rule_definition)'
        # transform rule in RGXLog's syntax into PyDatalog's syntax
        # i.e, ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y) will be transformed to:
        # ancestor(X,Y) <= parent(X,Z)& ancestor(Z,Y)

        # The user must supply exact same rule as the one in print_all_rules

        rule_head = rule.split("(")[0]
        if rule_head not in self.rules_history:
            raise Exception(f"{rule} was never registered (you can run 'print_all_rules' to see all the registered "
                            f"rules)")
        else:
            for i, (rgxlog_rule, pydatalog_rule) in enumerate(self.rules_history[rule_head]):
                if rgxlog_rule == rule:
                    remove_rule_statement = f'-({pydatalog_rule})'
                    # remove the rule in pyDatalog
                    pyDatalog.load(remove_rule_statement)
                    # remove rule from history
                    del self.rules_history[rule_head][i]
                    if len(self.rules_history[rule_head]) == 0:
                        del self.rules_history[rule_head]
                    if self.debug:
                        self.debug_buffer.append(remove_rule_statement)
                    break
            else:
                # if we are here then the rule doesn't exist
                raise Exception(f"{rule} was never registered (you can run 'print_all_rules' to see all the registered "
                                f"rules)")

    def remove_all_rules(self, rule_head):
        """
        Removes all rules from PyDatalog's engine.
        @param rule_head: we print all rules with rule_head. if it None we remove all rules.
        """

        if rule_head is None:
            for head in self.rules_history:
                self.remove_all_rules_with_head(head)
            self.rules_history = dict()
        else:
            self.remove_all_rules_with_head(rule_head)
            del self.rules_history[rule_head]

    def remove_all_rules_with_head(self, rule_head):
        """
        Removes all rules with specific head from PyDatalog's engine.
        @param rule_head: we print all rules with rule_head.
        @raise Exception: if there is no rule with rule_head.
        """

        if rule_head not in self.rules_history:
            raise Exception(f"There is not rule with head {rule_head}")

        for (_, rule) in self.rules_history[rule_head]:
            remove_rule_statement = f'-({rule})'
            if self.debug:
                self.debug_buffer.append(remove_rule_statement)
            pyDatalog.load(remove_rule_statement)

    def query(self, query: Query):
        """
        @param query: a query for pyDatalog
        @return: a list of tuples that are the query's results
        """

        # create the query. note that we don't use a question mark when we expect pyDatalog to return the query's
        # results instead of printing them. the syntax is 'some_relation(term_list)' (a normal relation representation)
        query_statement = self._get_relation_string(query)

        if self.debug:
            self.debug_buffer.append(f'query: {query_statement}')

        # loading the query into pyDatalog this way returns an object that contains a list of the resulting tuples
        py_datalog_answer_object = pyDatalog.ask(query_statement)

        # get the actual results out of the object and return them
        if py_datalog_answer_object is None:
            # special case when the query yields no results. return an empty list
            query_results = []
        else:
            # there's at least one resulting tuple, get the list of resulting tuples by accessing the 'answers' field
            query_results = py_datalog_answer_object.answers

        if self.debug:
            print(" ~~~ flushing debug buffer ~~~")
            print(self.flush_debug_buffer())
            print(" ~~~ end of buffer ~~~")

        return query_results

    def rule_to_string(self, rule_head: Relation, rule_body_relation_list: List,
                       rule_format: str = "PyDatalog") -> str:
        """

        @param rule_head: a relation that defines the rule head.
        @param rule_body_relation_list: a list of relations that defines the rule body.
        @param rule_format: return format of the string.
        @return: a string that represents the rule in PyDatalog's/RGXlog's format.
        """

        assert rule_format in ["PyDatalog", "RGXlog"], "illegal rule format"
        arrow, delimiter = ("<=", " & ") if rule_format == "PyDatalog" else ("<-", ", ")
        rule_head_string = self._get_relation_string(rule_head)
        rule_body_relation_strings = [str(relation) for relation in rule_body_relation_list]
        rule_body_string = delimiter.join(rule_body_relation_strings)
        return f'{rule_head_string} {arrow} {rule_body_string}'

    def add_rule(self, rule_head: Relation, rule_body_relation_list: List[Relation]) -> str:
        """
        adds a rule to the pydatalog engine.

        @param rule_head: a relation that defines the rule head
        @param rule_body_relation_list: a list of relations that defines the rule body
        @return: the rule we registered to pydataog.
        """

        # get a string that represents the rule in pyDatalog
        rule_string = self.rule_to_string(rule_head, rule_body_relation_list)

        if self.debug:
            self.debug_buffer.append(rule_string)

        # add the rule to pyDatalog
        pyDatalog.load(rule_string)

        return rule_string

    def compute_rule(self, rule_head: Relation, rule_body_relation_list: List[Relation],
                     rule_body_original_list: List) -> None:
        """
        A wrapper to add_rule. It adds the rule to PyDatalogs engine and saves a binding between the original rule
        and the rule we actually passed to PyDatalog.

        @param rule_head: a relation that defines the rule head
        @param rule_body_relation_list: a list of relations that defines the rule body
        @param rule_body_original_list: a List of the original relations that defined
        @return:
        """

        pydatalog_rule_string = self.add_rule(rule_head, rule_body_relation_list)
        rgxlog_rule_string = self.rule_to_string(rule_head, rule_body_original_list, "RGXlog")

        rule_head_str = self._get_relation_string(rule_head)
        # get relation name (without schema)
        rule_head_name = rule_head_str.split("(")[0]

        # don't save temp rgxlog rules
        if not rule_head_name.startswith(RESERVED_RELATION_PREFIX):
            rule_binding = (rgxlog_rule_string, pydatalog_rule_string)
            if rule_head_name in self.rules_history:
                self.rules_history[rule_head_name].append(rule_binding)
            else:
                self.rules_history[rule_head_name] = [rule_binding]

    def print_all_rules(self, rule_head: str = None):
        """
        prints all the rules that are registered.

        @param rule_head: if rule head is not none we print all rules with rule_head
        """

        if rule_head is None:
            print("Printing all rules:")
            for head in self.rules_history:
                self.print_all_rules_with_head(head)
        else:
            print(f"Printing all rules with head {rule_head}:")
            self.print_all_rules_with_head(rule_head)

        # looks better with newline (\n)
        print()

    def print_all_rules_with_head(self, rule_head: str):
        """
        prints all the rules with rule_head that are registered.

        @param rule_head: we print all rules with rule_head
        @raise Exception: if rule head was specified but there is no rule with that rule head.
        """
        if rule_head not in self.rules_history:
            raise Exception(f"No rules with head {rule_head} were registered.")

        for rule, _ in self.rules_history[rule_head]:
            print(rule)

    def compute_ie_relation(self, ie_relation: IERelation, ie_func: IEFunction,
                            bounding_relation: Relation) -> Relation:
        """
        computes an information extraction relation, returning the result as a normal relation.
        for more details see RgxlogEngineBase.compute_ie_relation.

        @param ie_relation: an ie relation that determines the input and output terms of the ie function
        @param ie_func: the ie function that will be used to compute the ie relation
        @param bounding_relation: a relation that contains the inputs for ie_funcs. the actual input needs to be
                                  queried from it
        @return: a normal relation that contains all of the resulting tuples in the rgxlog engine
        """

        ie_relation_name = ie_relation.relation_name

        # create the input relation for the ie function, and also declare it inside pyDatalog
        input_relation_arity = len(ie_relation.input_term_list)
        input_relation_name = self._create_unique_relation(input_relation_arity, name=f'{ie_relation_name}_input')
        input_relation = Relation(input_relation_name, ie_relation.input_term_list, ie_relation.input_type_list)

        # create the output relation for the ie function, and also declare it inside pyDatalog
        output_relation_arity = len(ie_relation.output_term_list)
        output_relation_name = self._create_unique_relation(output_relation_arity, name=f'{ie_relation_name}_output')
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
                # the output should be a tuple, but if a single value is returned, we accept it as well
                if isinstance(ie_output, str) or isinstance(ie_output, int) or isinstance(ie_output, Span):
                    ie_output = [ie_output]
                else:
                    ie_output = list(ie_output)

                # assert the ie output is properly typed
                self._assert_ie_output_properly_typed(ie_input, ie_output, ie_output_schema, ie_relation)

                # the user is allowed to represent a span in an ie output as a tuple of length 2
                # convert said tuples to spans
                ie_output = [Span(term[0], term[1]) if (isinstance(term, tuple) and len(term) == 2)
                             else term
                             for term in ie_output]

                # add the output as a fact to the output relation
                # notice - repetitions are ignored here (results are in a set)
                if len(ie_output) != 0:
                    output_fact = AddFact(output_relation.relation_name, ie_output, ie_output_schema)
                    self.add_fact(output_fact)

        # create and return the result relation. it's a relation that is the join of the input and output relations
        result_relation = self.join_relations([input_relation, output_relation], name=ie_relation_name)
        return result_relation

    def join_relations(self, relation_list: List[Relation], name="") -> Relation:
        """
        perform a join between all of the relations in the relation list and saves the result to a new relation.
        the results of the join are filtered so they only include columns in the relations that were defined by
        a free variable term.
        all of the relation in relation_list must be normal (not ie relations)

        for an example and more details see RgxlogEngineBase.join_relations

        @param relation_list: a list of normal relations
        @param name: a name for the joined relation (will be used as a part of a temporary relation name)
        @return: a new relation as described above
        """

        # get all of the free variables in all of the relations, they'll serve as the terms of the joined relation
        free_var_sets = [get_output_free_var_names(relation) for relation in relation_list]
        free_vars = set().union(*free_var_sets)
        joined_relation_terms = list(free_vars)

        # get the type list of the joined relation (all of the terms are free variables)
        joined_relation_arity = len(joined_relation_terms)
        joined_relation_types = [DataTypes.free_var_name] * joined_relation_arity

        # declare the joined relation in pyDatalog and get its name
        joined_relation_name = self._create_unique_relation(joined_relation_arity, name=name)

        # created a structured node of the joined relation
        joined_relation = Relation(joined_relation_name, joined_relation_terms, joined_relation_types)

        # use a rule to filter the tuples of the relations in relation_list into the joined relation
        self.add_rule(joined_relation, relation_list)

        return joined_relation

    def _convert_relation_term_to_string(self, term, term_type):
        """
        the pyDatalog execution engine receives instructions via strings.
        return a string representation of a term in pyDatalog.

        @param term: a term of any type
        @param term_type: the type of the term
        @return: a string representation of the term in pyDatalog
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
        pydatalog version is without '['

        @param span: a span object
        @return: a string representation of the span
        """

        span_string = f'({span.span_start}, {span.span_end})'
        return span_string

    def _get_relation_string(self, relation: Relation):
        """
        the pyDatalog execution engine receives instructions via strings.
        return a relation string representation of a relation in pyDatalog.
        quotes are added to string terms so pyDatalog will not be confused between strings and variables.
        spans are represented as tuples of length 2 (see PydatalogEngine.__get_span_string())

        @param relation: a relation
        @return: a pydatalog string representation of the relation
        """

        # create a string representation of the relation's term list in pyDatalog
        pydatalog_string_terms = [self._convert_relation_term_to_string(term, term_type)
                                  for term, term_type in zip(relation.term_list, relation.type_list)]
        pydatalog_string_term_list = ', '.join(pydatalog_string_terms)

        # create a string representation of the relation in pydatalog and return it
        pydatalog_string_relation = f"{relation.relation_name}({pydatalog_string_term_list})"
        return pydatalog_string_relation

    def _get_all_relation_tuples(self, relation: Relation) -> List[Tuple]:
        """
        @param relation: a relation to be queried
        @return: all the tuples of 'relation' as a list of tuples
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

    def _create_unique_relation(self, arity, name=""):
        """
        declares a new temporary relation with the requested arity in pyDatalog
        note that the relation's schema is not needed as there's no typechecking in pyDatalog

        @param arity: the temporary relation's arity (needed for declaring the new relation inside pyDatalog)
        @param name: will be used as a part of the temporary relation's name. for example for the name 'RGX',
                     the temporary relation's name could be __rgxlog__RGX_0
        @return: the new temporary relation's name
        """

        if len(name) != 0:
            # if the temporary relation should have a name, add an underscore to separate the name from the id
            name = f'{name}_'

        # create the name of the new temporary relation
        temp_relation_id = next(self.temp_relation_id_counter)
        temp_relation_name = f'{RESERVED_RELATION_PREFIX}{name}{temp_relation_id}'

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

        @param ie_input: the input of the ie function (used in the exception when the type check fails)
        @param ie_output: an output of the ie function
        @param ie_output_schema: the expected schema for ie_output
        @param ie_relation: the ie relation for which the output was computed (will be used to print an exception
            in case the output is not properly typed)
        @raise Exception: if there is output term of an unsupported type or the output relation is not properly typed.
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

    @staticmethod
    def clear_all():
        """
        removes all the data from the pydatalog engine. without this, all sessions share their facts and relations
        """
        pyDatalog.clear()

    def execute_rule_aux(self, rule_term_id, parse_graph: TermGraphBase, symbol_table: SymbolTableBase):
        """
        rule_term_id is expected to be a root of a subtree in the term graph that represents a single rule
        the children of rule_term_id node should be:
        1. a rule head relation node
        2. a rule body relation list, whose children are all the body relations of the rule

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
        @param parse_graph:
        @param symbol_table:
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

        rule_children = parse_graph.get_children(rule_term_id)
        assert len(rule_children) == 2, "a rule must have exactly 2 children"

        rule_head_id, rule_body_id = rule_children
        body_relation_id_list = parse_graph.get_children(rule_body_id)

        body_relation_original_list = list()

        # compute the rule body relations from left to right and save the intermediate results in
        # 'intermediate_relation'
        intermediate_relation = None
        for relation_id in body_relation_id_list:
            relation_term_attrs = parse_graph.get_term_attributes(relation_id)

            relation = relation_term_attrs['value']
            relation_type = relation_term_attrs['type']

            body_relation_original_list.append(relation)

            # compute the relation in the engine if needed
            if relation_type == 'relation':
                # no special computation is required, take the relation as is
                result_relation = relation
            elif relation_type == 'ie_relation':
                # compute the ie relation
                ie_func_data = symbol_table.get_ie_func_data(relation.relation_name)
                result_relation = self.compute_ie_relation(relation, ie_func_data,
                                                           intermediate_relation)
            else:
                raise Exception(f'unexpected relation type: {relation_type}')

            # save the resulting relation in the term graph
            parse_graph.set_term_attribute(relation_id, 'value', result_relation)

            # join the resulting relation with the intermediate relation
            if intermediate_relation is None:
                intermediate_relation = result_relation
            else:
                intermediate_relation = self.join_relations(
                    [intermediate_relation, result_relation], name="temp_join")

        # declare the rule head in the rgxlog engine
        rule_head_attrs = parse_graph[rule_head_id]
        rule_head_relation = rule_head_attrs['value']
        rule_head_declaration = RelationDeclaration(rule_head_relation.relation_name,
                                                    symbol_table.get_relation_schema(rule_head_relation.relation_name))
        self.declare_relation(rule_head_declaration)

        # define the rule head in the rgxlog engine by filtering the tuples of the intermediate relation into it
        self.compute_rule(rule_head_relation, [intermediate_relation], body_relation_original_list)
