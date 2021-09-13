"""
this modules contains implementations of 'RgxlogEngineBase' which is an abstraction for the rgxlog engine
and also implementations of 'ExecutionBase' which serves as an abstraction for an interface between a term graph
and an rgxlog engine.
"""
import logging

from jinja2 import Template
import sqlite3 as sqlite
import tempfile
from abc import ABC, abstractmethod
from itertools import count
from pathlib import Path
from typing import (Tuple, Optional, Dict, Set, Iterable, Union, Any, List)

from rgxlog.engine.datatypes.ast_node_types import (DataTypes, Relation, AddFact, RemoveFact, Query,
                                                    RelationDeclaration, IERelation)
from rgxlog.engine.datatypes.primitive_types import Span
from rgxlog.engine.ie_functions.ie_function_base import IEFunction
from rgxlog.engine.state.symbol_table import SymbolTableBase
from rgxlog.engine.state.term_graph import EvalState, GraphBase, ComputationTermGraph
from rgxlog.engine.utils.general_utils import get_output_free_var_names, get_free_var_to_relations_dict, string_to_span, strip_lines

VALUE_ATTRIBUTE = 'value'
OUT_REL_ATTRIBUTE = "output_rel"

RESERVED_RELATION_PREFIX = "__rgxlog__"

FREE_VAR_PREFIX = "COL"

# rgx constants
FALSE_VALUE = []
TRUE_VALUE = [tuple()]

logger = logging.getLogger(__name__)


class RgxlogEngineBase(ABC):
    """
    An abstraction for a rgxlog execution engine, used by GenericExecution.
    it includes relational algebra operators like join and project, database modification operators like
    `add_fact` (insert) and `remove_fact` (delete), and rgxlog-specific operators like `compute_ie_relation`.
    """

    def __init__(self):
        super().__init__()

    @abstractmethod
    def declare_relation(self, relation_decl: RelationDeclaration) -> None:
        """
        Declares a relation in the rgxlog engine.
        @note: if the relation is already declared does nothing.


        @param relation_decl: a relation declaration.
        """
        pass

    @abstractmethod
    def add_fact(self, fact: AddFact) -> None:
        """
        Adds a fact to the rgxlog engine.

        @param fact: the fact to be added.
        """
        pass

    @abstractmethod
    def remove_fact(self, fact: RemoveFact) -> None:
        """
        Removes a fact from the rgxlog engine.

        @param fact: the fact to be removed.
        """
        pass

    @abstractmethod
    def query(self, query: Query):
        """
        Queries the rgxlog engine.
        Outputs a preformatted query result, e.g. [("a",5),("b",6)].
        notice that `query` isn't a string; it's a `Query` object which inherits from `Relation`.
        for example, parsing the string `?excellent("bill","ted")` yields the following `Query`:

        ```
        relation_name = excellent
        term_list = ["bill", "ted"]
        type_list = [DataType.string, DataType.string]
        ```

        @param query: a query for the rgxlog engine.
        @return: a list of tuples that are the query's results.
        """
        pass

    @abstractmethod
    def remove_tables(self, tables_names: Iterable[str]) -> None:
        """
        Removes all the tables inside the input from sql.

        @param tables_names: tables to remove.
        """
        pass

    @abstractmethod
    def clear_table(self, table: str) -> None:
        """
        Resets the table (deletes all its tuples).

        @param table: tables to reset.
        """
        pass

    def clear_tables(self, tables_names: Iterable[str]) -> None:
        """
        Resets all the tables inside the input (deletes all their tuples).

        @param tables_names: tables to reset.
        """
        for table in tables_names:
            self.clear_table(table)

    @abstractmethod
    def get_table_len(self, table: str) -> int:
        """
        @param table: name of a table.
        @return: number of tuples inside the table.
        """
        pass

    @abstractmethod
    def compute_ie_relation(self, ie_relation: IERelation, ie_func_data,
                            bounding_relation: Optional[Relation]) -> Relation:
        """
        Computes an information extraction relation, returning the result as a normal relation.

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

        @param ie_relation: an ie relation that determines the input and output terms of the ie function.
        @param ie_func_data: the data for the ie function that will be used to compute the ie relation.
        @param bounding_relation: a relation that contains the inputs for ie_funcs. the actual input needs to be
                                  queried from it2
        @return: a normal relation that contains all of the resulting tuples in the rgxlog engine.
        """
        pass

    #  TODO@tom: @niv, why do we need this method?
    # @staticmethod
    # @abstractmethod
    # def clear_all() -> None:
    #     """
    #     Removes all facts and clauses from the engine.
    #     """
    #     pass

    @staticmethod
    def _get_span_string(span: Span) -> str:
        """
        Converts Span(start,end) to string("[start, end)").

        @param span: a span object.
        @return: a string representation of the span.
        """

        span_string = f'[{span.span_start}, {span.span_end})'
        return span_string

    @abstractmethod
    def _convert_relation_term_to_string(self, datatype: DataTypes, term) -> str:
        """
        Return the string representation of a relation term, e.g. "[1,4)"

        @param datatype: the type of the term.
        @param term: the term object itself.
        @return: string representation.
        """
        pass

    def _get_relation_string(self, relation: Relation) -> str:
        """
        Returns the string representation of a relation which has terms, e.g. REL(3, "hello").

        @param relation: a relation object.
        @return: a string representation of the relation.
        """
        terms_string = ', '.join([self._convert_relation_term_to_string(term, term_type)
                                  for term, term_type in zip(relation.term_list, relation.type_list)])

        final_string = f"{relation.relation_name}({terms_string})"
        return final_string

    @abstractmethod
    def operator_select(self, relation: Relation, select_info: Set[Tuple[int, Any, DataTypes]]) -> Relation:
        """
        @param relation: the relation from which we select tuples.
        @param select_info: set of tuples. each tuple contains the index of the column, the value to select
                            and the type of the column.
        @return: a filtered relation.
        """
        pass

    @abstractmethod
    def operator_join(self, relations: List[Relation], prefix: str = "") -> Relation:
        """
        Performs a join between all of the relations in the relation list and saves the result to a new relation.
        the results of the join are filtered so they only include columns in the relations that were defined by
        a free variable term.
        all of the relations in relation_list must be normal (not ie relations)

        for an example and more details see RgxlogEngineBase.join_relations.

        @param relations: a list of normal relations.
        @param prefix: a prefix for the name of the joined relation.
        @return: a new relation as described above.
        """
        pass

    @abstractmethod
    def operator_project(self, relation: Relation, project_vars: Set[str]) -> Relation:
        """
        @param relation: the relation on which we project.
        @param project_vars: a set of variables on which we project.
        @return: the projected relation.
        """
        pass

    @abstractmethod
    def operator_union(self, relations: List[Relation]) -> Relation:
        """
        Relation union.
        @note: we assume that all the relations have same free_vars in the same order.


        @param relations: a list of relations to unite.
        @return: the united relation.
        """
        pass

    @abstractmethod
    def operator_copy(self, src_rel: Relation, output_relation_name: Optional[str] = None) -> Relation:
        """
        Copies computed_relation to rule_relation.

        @param src_rel: the relation to copy from.
        @param output_relation_name: if this is None, create a unique name for the output relation.
            otherwise, this will be the name of the output relation.
        @return: tje copied relation.
        """
        pass


class SqliteEngine(RgxlogEngineBase):
    """
    in this implementation of the engine, we use python's sqlite3, which allows creating an SQL database easily, without using servers.
    the engine is called from `GenericExecution`, and uses `run_sql` as an interface to the database, which queries/modifies a table.
    each `operator` method implements a relational algebra operator by constructing an SQL command and executing it.
    """

    # useful prefixes
    PROJECT_PREFIX = "project"
    JOIN_PREFIX = "join"
    COPY_PREFIX = "copy"
    SELECT_PREFIX = "select"
    UNION_PREFIX = "union"
    RELATION_COLUMN_PREFIX = "col"

    # sql constants
    SQL_SELECT = 'SELECT DISTINCT'
    SQL_TABLE_OF_TABLES = 'sqlite_master'
    SQL_SEPARATOR = "_"
    DATATYPE_TO_SQL_TYPE = {DataTypes.string: "TEXT", DataTypes.integer: "INTEGER", DataTypes.span: "TEXT"}

    # TODO@niv: refactor everything to jinja2
    def __init__(self, database_name=None):
        """
        Creates/opens an SQL database file + connection.

        @param database_name: open an existing database instead of a new one.
        """
        super().__init__()
        self.unique_relation_id_counter = count()
        self.rules_history = dict()

        if database_name:
            if not Path(database_name).is_file():
                raise IOError(f"database file: {database_name} was not found")
            self.db_filename = database_name
        else:
            temp_db_file = tempfile.NamedTemporaryFile(delete=False)
            temp_db_file.close()
            self.db_filename = temp_db_file.name

        logger.info(f"using database file: {self.db_filename}")

        self.sql_conn = sqlite.connect(self.db_filename)
        self.sql_cursor = self.sql_conn.cursor()

    def run_sql(self, command, command_args=None) -> List:
        logger.debug(f"sql {command=}")
        if command_args:
            logger.debug(f"...with args: {command_args}")

        if command_args:
            self.sql_cursor.execute(command, command_args)
        else:
            self.sql_cursor.execute(command)

        return self.sql_cursor.fetchall()

    def add_fact(self, fact: AddFact) -> None:
        """
        Add a row into an existing table.
        """
        num_types = len(fact.type_list)
        sql_template = strip_lines("""
        INSERT INTO {{fact.relation_name}} (
        {%- for col_index in range(num_types) -%}
            {{engine.RELATION_COLUMN_PREFIX}}{{col_index}}
            {%- if not loop.last -%}
            , 
            {%- endif -%}
        {% endfor -%}
        ) VALUES (
        {%- for i in range(num_types) -%}
            ?
            {%- if not loop.last -%}
            , 
            {%- endif -%}
        {%- endfor -%}
        )
        """)
        sql_command = Template(sql_template).render(num_types=num_types, fact=fact, engine=self)

        # sql_command = f"INSERT INTO {fact.relation_name} ("
        # sql_command += ", ".join([f"{self.RELATION_COLUMN_PREFIX}{i}" for i in range(num_types)])
        # sql_command += ") VALUES ("
        # sql_command += ", ".join(["?"] * num_types)
        # sql_command += ")"

        sql_term_list = [self._convert_relation_term_to_string(datatype, term) for datatype, term in
                         zip(fact.type_list, fact.term_list)]
        self.run_sql(sql_command, sql_term_list)

    def remove_fact(self, fact: RemoveFact) -> None:
        # use a `DELETE` statement
        sql_terms = fact.term_list  # add quotes here

        sql_command = (f"DELETE FROM {fact.relation_name} WHERE"
                       f"(t1='{sql_terms[0]}' AND t2='{sql_terms[1]}')")
        self.run_sql(sql_command)

    def query(self, query: Query, allow_duplicates=False) -> List[tuple]:
        """
        Outputs a preformatted query result, e.g. [("a",5),("b",6)].
        notice that `query` isn't a string; it's a `Query` object which inherits from `Relation`.
        for example, parsing the string `?excellent("bill","ted")` yields the following `Query`:

        ```
        relation_name = excellent
        term_list = ["bill", "ted"]
        type_list = [DataType.string, DataType.string]
        ```

        @param allow_duplicates: if True, query result may contain duplicate values.
        @param query: the query to be performed.
        @return: a query results which is True, False, or a list of tuples.
        """
        # note: this is an engine query (which asks a single question),
        # not a session query (which can do anything).
        # so we only need to select + project here
        query_free_var_indexes = self._get_free_variable_indexes(query.type_list)
        has_free_vars = bool(query_free_var_indexes)
        select_info = query.get_select_cols_values_and_types()

        # create temporary tables for the select/project, and delete them
        selected_relation = self.operator_select(query, select_info)
        selected_relation_name = selected_relation.relation_name

        free_var_names_for_project = [term for term, term_type in zip(query.term_list, query.type_list)
                                      if term_type is DataTypes.free_var_name]
        if has_free_vars:
            projected_relation_name = self.operator_project(selected_relation, free_var_names_for_project).relation_name
        else:
            projected_relation_name = selected_relation_name

        query_result = self.run_sql(f"{self.SQL_SELECT} * FROM {projected_relation_name}")

        self.remove_table(selected_relation_name)
        self.remove_table(projected_relation_name)

        if (not has_free_vars) and query_result != FALSE_VALUE:
            query_result = TRUE_VALUE

        spanned_query_result = self.convert_strings_to_spans_in_query_result(query_result)

        return spanned_query_result

    @staticmethod
    def convert_strings_to_spans_in_query_result(query_result: List[tuple]) -> List[tuple]:
        """
        convert strings that look like spans into spans
        @param query_result: the list of tuples which may contain strings that should be converted to spans
        @return: the same list, but with span-looking strings converted to `Span` objects
        """
        spanned_query_result = []
        for row in query_result:
            converted_row = []
            for value in row:
                if isinstance(value, str):
                    transformed_string = string_to_span(value)
                    if transformed_string is None:
                        converted_row.append(value)
                    else:
                        converted_row.append(transformed_string)
                else:
                    converted_row.append(value)

            spanned_query_result.append(tuple(converted_row))
        return spanned_query_result

    def remove_tables(self, table_names: Iterable[str]) -> None:
        """
        Removes the given tables from sql.

        @param table_names: tables to remove.
        """
        for table_name in table_names:
            self.remove_table(table_name)

    def remove_table(self, table_name: str) -> None:
        """
        Removes a table from the sql database, if it exists.

        @param table_name: the table to remove.
        """
        if self.is_table_exists(table_name):
            sql_command = f"DROP TABLE {table_name}"
            self.run_sql(sql_command)

    def _create_unique_relation(self, arity, prefix=""):
        """
        Declares a new relation with the requested arity in SQL, the relation will have a unique name.

        @param arity: the relation's arity.
        @param prefix: will be used as a part of the relation's name.
                for example: prefix='join' -> full name = __rgxlog__join{counter}.
        @return: the new relation's name.
        """
        # create the name of the new relation
        unique_relation_id = next(self.unique_relation_id_counter)
        if RESERVED_RELATION_PREFIX in prefix:
            # we don't want relations to be called __rgxlog__rgxlog__rgxlog...
            unique_relation_name = f'{prefix}{unique_relation_id}'
        else:
            unique_relation_name = f'{RESERVED_RELATION_PREFIX}{prefix}{unique_relation_id}'

        # in SQLite there's no typechecking so we just need to make sure that the schema has the correct arity
        unique_relation_schema = [DataTypes.free_var_name] * arity

        # create the declaration
        unique_relation_decl = RelationDeclaration(unique_relation_name, unique_relation_schema)

        # create the relation's SQL table, and return its name
        self.declare_relation(unique_relation_decl)
        return unique_relation_name

    def compute_ie_relation(self, ie_relation: IERelation, ie_func: IEFunction,
                            bounding_relation: Optional[Relation]) -> Relation:
        """
        Computes an information extraction relation, returning the result as a normal relation.
        for more details see RgxlogEngineBase.compute_ie_relation.
        notice comments below regarding constants

        @param ie_relation: an ie relation that determines the input and output terms of the ie function.
        @param ie_func: the ie function that will be used to compute the ie relation.
        @param bounding_relation: a relation that contains the inputs for ie_funcs. the actual input needs to be
                                  queried from it.
        @return: a normal relation that contains all of the resulting tuples in the rgxlog engine.
        """
        ie_relation_name = ie_relation.relation_name

        # create the output relation for the ie function, and also declare it inside SQL
        output_relation_arity = len(ie_relation.output_term_list)
        output_relation_name = self._create_unique_relation(output_relation_arity,
                                                            prefix=f'{ie_relation_name}{self.SQL_SEPARATOR}output')
        output_relation = Relation(output_relation_name, ie_relation.output_term_list, ie_relation.output_type_list)

        # define the ie input relation
        if bounding_relation is None:
            # special case where the ie relation is the first rule body relation
            # in this case, the ie input relation is defined exclusively by constant terms, i.e, by a single tuple
            # add that tuple as a fact to the input relation
            # create the input relation for the ie function, and also declare it inside SQL
            ie_inputs = [tuple(ie_relation.input_term_list)]
        else:
            # get a list of inputs to the ie function - some of them may be constants
            inputs_without_constants = self._get_all_relation_tuples(bounding_relation)
            ie_inputs = []
            for bounded_input in inputs_without_constants:
                result_input_list = []
                index_in_bounded_input = 0
                for term, datatype in zip(ie_relation.input_term_list, ie_relation.input_type_list):
                    if datatype is DataTypes.free_var_name:
                        # add value from `bounded_input`
                        result_input_list.append(bounded_input[index_in_bounded_input])
                        index_in_bounded_input += 1
                    else:
                        # add a constant from the ie_relation's input
                        result_input_list.append(term)

                assert index_in_bounded_input == len(bounded_input), "parsing input relation failed"
                ie_inputs.append(tuple(result_input_list))

        # get the schema for the ie outputs
        ie_output_schema = ie_func.get_output_types(output_relation_arity)

        # run the ie function on each input and process the outputs
        for ie_input in ie_inputs:
            # run the ie function on the input, resulting in a list of tuples
            ie_outputs = ie_func.ie_function(*ie_input)
            # process each ie output and add it to the output relation
            for ie_output in ie_outputs:
                # the output should be a tuple, but if a single value is returned, we accept it as well
                if isinstance(ie_output, (str, int, Span)):
                    ie_output = [ie_output]
                else:
                    ie_output = list(ie_output)
                    # the user is allowed to represent a span in an ie output as a tuple of length 2
                    # convert said tuples to spans
                    ie_output = [Span(term[0], term[1]) if (isinstance(term, tuple) and len(term) == 2)
                                 else term for term in ie_output]

                # assert the ie output is properly typed
                self._assert_ie_output_properly_typed(ie_input, ie_output, ie_output_schema, ie_relation)

                # add the output as a fact to the output relation
                # notice - repetitions are ignored here (results are in a set)
                if len(ie_output) != 0:
                    output_fact = AddFact(output_relation.relation_name, ie_output, ie_output_schema)
                    self.add_fact(output_fact)

        return output_relation

    def _get_all_relation_tuples(self, relation: Relation) -> List[Tuple]:
        """
        @param relation: a relation to be queried.
        @return: all the tuples of 'relation' as a list of tuples.
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
        Even though rgxlog performs typechecking during the semantic checks phase, information extraction functions
        are written by the users and could yield results that are not properly typed.
        this method asserts an information extraction function's output is properly typed.

        @param ie_input: the input of the ie function (used in the exception when the type check fails).
        @param ie_output: an output of the ie function.
        @param ie_output_schema: the expected schema for ie_output.
        @param ie_relation: the ie relation for which the output was computed (will be used to print an exception
            in case the output is not properly typed).
        @raise Exception: if there is output term of an unsupported type or the output relation is not properly typed.
        """

        # get a list of the ie output's term types
        ie_output_term_types = []
        for output_term in ie_output:
            if isinstance(output_term, int):
                output_type = DataTypes.integer
            elif isinstance(output_term, str):
                output_type = DataTypes.string
            elif isinstance(output_term, Span):
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
        Declares a relation as an SQL table, whose types are named t0, t1, ...
        if the relation is already declared does nothing.

        @param relation_decl: the declaration info.
        """
        # create the relation table. we don't use an id because it would allow inserting the same values twice
        # note: to ignore duplicates, we can either use UNIQUE when creating the table, or DISTINCT when selecting.
        #  right now we use DISTINCT
        if self.is_table_exists(relation_decl.relation_name):
            return

        # note: sqlite can guess datatypes. if this causes bugs, use `{self._datatype_to_sql_type(relation_type)}`.
        sql_command = f"CREATE TABLE {relation_decl.relation_name} ("
        sql_command += ", ".join([f"{self.RELATION_COLUMN_PREFIX}{i}" for i in range(len(relation_decl.type_list))])
        sql_command += ")"

        self.run_sql(sql_command)

        # save to file
        self.sql_conn.commit()

    def operator_select(self, src_relation: Relation, select_info: Set[Tuple[int, Any, DataTypes]]) -> Relation:
        """
        Performs sql WHERE.

        @param src_relation: the relation from which we select tuples.
        @param select_info: set of tuples. each tuple contains the index of the column, the value to select
                            and the type of the column.

        @return: a filtered relation.
        """
        # get the columns based on `select_info`
        src_relation_name = src_relation.relation_name

        new_arity = len(src_relation.term_list)
        new_term_list = src_relation.term_list
        new_type_list = src_relation.type_list

        new_relation_name = self._create_unique_relation(new_arity,
                                                         prefix=f"{src_relation_name}{self.SQL_SEPARATOR}{self.SELECT_PREFIX}")

        selected_relation = Relation(new_relation_name, new_term_list, new_type_list)

        # sql part
        sql_command = f'INSERT INTO {new_relation_name} {self.SQL_SELECT} * FROM {src_relation_name}'
        sql_args = []

        # get variables in var_dict that repeat - used below to add conditions
        src_relation_var_dict = get_free_var_to_relations_dict({src_relation})
        repeating_vars_in_relation = [(free_var, pairs) for (free_var, pairs) in
                                      src_relation_var_dict.items() if (len(pairs) > 1)]
        if (len(select_info) > 0) or repeating_vars_in_relation:
            # TODO@niv: refactor this into new helper method
            sql_command_where = " WHERE "
            sql_conditions = []
            # add conditions based on `select_info`
            for i, value, _ in select_info:
                col_name = self._get_col_name(i)
                if type(value) is Span:
                    # sql does not accept spans
                    value = str(value)
                sql_args.append(value)
                sql_conditions.append(f"{col_name}=?")

            # add conditions based on repeating free variables like a(X,X) - check if they are equal
            for free_var, pairs in repeating_vars_in_relation:
                first_pair, other_pairs = pairs[0], pairs[1:]
                first_index = first_pair[1]
                first_col_name = self._get_col_name(first_index)
                for _, second_index in other_pairs:
                    second_col_name = self._get_col_name(second_index)
                    sql_conditions.append(f"{first_col_name}={second_col_name}")

            sql_command_where += " AND ".join(sql_conditions)

            # """
        #     data={
        #         constant_terms_positions=[
        #                                      (1,"yes"),
        #                                      (4,"no")
        #                                  ],
        #                                  same_variable_positions=[
        #         (0,2),
        #         (0,3)
        #     ]
        #
        #     }
        #
        #
        # template =
        # INSERT . INTO ..  WHERE
        # {% for index,constant in constant_terms_positions %}
        # 	col{index}={constant}
        #
        # {% for lhs,rhs in same_variable_positions %}
        # 	{lhs}={rhs}
        #
        #
        # """

        else:
            sql_command_where = ""

        sql_command += sql_command_where

        self.run_sql(sql_command, sql_args)
        return selected_relation

    def operator_join(self, relations: List[Relation], prefix: str = "") -> Relation:
        """
        note: SQL's inner_join without `IN` is actually cross-join (product), so this covers product as well.

        @param relations: a list of normal relations.
        @param prefix: a prefix for the name of the joined relation.
        @return: a new relation as described above.
        """

        def _create_new_relation_for_join_result(relation_terms, relation_prefix):
            # get the type list of the joined relation (all of the terms are free variables)
            relation_arity = len(relation_terms)
            relation_types = [DataTypes.free_var_name] * relation_arity

            # declare the joined relation in sql and get its name
            joined_relation_name = self._create_unique_relation(relation_arity,
                                                                prefix=f"{relation_prefix}{self.SQL_SEPARATOR}{self.JOIN_PREFIX}")

            # create a structured node of the joined relation
            return Relation(joined_relation_name, relation_terms, relation_types)

        assert len(relations) > 0, "can't join an empty list"
        if len(relations) == 1:
            return self.operator_copy(relations[0])

        # create a mapping between the relations and their temporary names for sql
        relation_sql_names = {relation: f"table{i}" for (i, relation) in enumerate(relations)}
        var_dict = get_free_var_to_relations_dict(set(relations))

        # get all of the free variables in all of the relations, they'll serve as the terms of the joined relation
        free_var_sets = [get_output_free_var_names(relation) for relation in relations]
        free_vars = set().union(*free_var_sets)
        joined_relation_terms = list(free_vars)

        joined_relation = _create_new_relation_for_join_result(joined_relation_terms, prefix)

        # construct the sql join command
        on_conditions_list = []
        inner_join_list = []
        free_var_cols = []

        # iterate over the free_vars and do 2 things:
        for i, free_var in enumerate(joined_relation_terms):
            free_var_pairs: List[Tuple[Union[Relation, IERelation], int]] = var_dict[free_var]
            first_pair, other_pairs = free_var_pairs[0], free_var_pairs[1:]

            relation_with_free_var, first_index = first_pair
            name_of_relation_with_free_var = relation_sql_names[relation_with_free_var]
            new_col_name = self._get_col_name(i)
            first_col_name = self._get_col_name(first_index)

            # 1. name the new columns. the columns should be named col0, col1, etc.
            free_var_cols.append(f"{name_of_relation_with_free_var}.{first_col_name} AS {new_col_name}")

            # 2. create the comparison between all of them, using `ON`
            for (second_relation, second_index) in other_pairs:
                second_col_name = self._get_col_name(second_index)
                name_of_second_relation = relation_sql_names[second_relation]
                on_conditions_list.append(f"{name_of_relation_with_free_var}.{first_col_name}="
                                          f"{name_of_second_relation}.{second_col_name}")

        # first relation - just `FROM`
        first_relation, other_relations = relations[0], relations[1:]

        # for every next relation: `INNER JOIN`
        for relation in other_relations:
            inner_join_list.append(f"INNER JOIN {relation.relation_name} AS {relation_sql_names[relation]}")

        # add the join conditions (`ON`)
        if on_conditions_list:
            on_conditions_str = " ON " + " AND ".join(on_conditions_list)
        else:
            on_conditions_str = ""

        sql_command = f"INSERT INTO {joined_relation.relation_name} {self.SQL_SELECT} "
        sql_command += ", ".join(free_var_cols)
        sql_command += f" FROM {first_relation.relation_name} AS {relation_sql_names[first_relation]} "
        sql_command += " ".join(inner_join_list)
        sql_command += on_conditions_str

        self.run_sql(sql_command)

        return joined_relation

    def operator_project(self, src_relation: Relation, project_vars: List[str]) -> Relation:
        """
        Performs SQL select.

        @param src_relation: the relation on which we project.
        @param project_vars: a list of variables on which we project.
        @return: the projected relation.
        """
        # get the indexes to project from (in `src_relation`) based on `var_dict`
        var_dict: Dict[str, List[Tuple[Union[Relation, IERelation], int]]] = get_free_var_to_relations_dict(
            {src_relation})
        project_indexes = []
        for var in project_vars:
            var_index_in_src = (var_dict[var][0][1])
            project_indexes.append(var_index_in_src)

        src_type_list = src_relation.type_list
        new_type_list = [src_type_list[i] for i in project_indexes]

        new_arity = len(project_vars)

        src_relation_name = src_relation.relation_name
        new_relation_name = self._create_unique_relation(new_arity, prefix=self.PROJECT_PREFIX)

        new_relation = Relation(new_relation_name, project_vars, new_type_list)

        dest_col_list = []
        for new_col_num, src_col_num in enumerate(project_indexes):
            new_col = self._get_col_name(new_col_num)
            src_col = self._get_col_name(src_col_num)
            if new_col == src_col:
                # this prevents selecting "colX AS colX", for aesthetic reasons
                dest_col_list.append(src_col)
            else:
                dest_col_list.append(f"{src_col} AS {new_col}")

        sql_command = (f"INSERT INTO {new_relation_name} {self.SQL_SELECT} {', '.join(dest_col_list)}"
                       f" FROM {src_relation_name}")

        self.run_sql(sql_command)
        return new_relation

    def operator_union(self, relations: List[Relation]) -> Relation:
        """
        @param relations: a list of relations to unite.
        @return: the united relation.
        """
        new_arity = len(relations)
        assert new_arity > 0, "cannot perform union on an empty list"
        if new_arity == 1:
            return relations[0]

        new_relation_name = self._create_unique_relation(len(relations[0].term_list), prefix=self.UNION_PREFIX)
        new_term_list = relations[0].term_list
        new_type_list = relations[0].type_list
        new_relation = Relation(new_relation_name, new_term_list, new_type_list)

        # create the union command by iterating over the relations and finding the index of each term
        union_list = []
        for relation in relations:
            curr_relation_string = f"{self.SQL_SELECT} "
            selection_list = []
            for col_index, term in enumerate(new_term_list):
                # we assume the same order in the source and the destination, so no need to use 'AS'
                col_name = self._get_col_name(col_index)
                selection_list.append(f"{col_name}")
            curr_relation_string += ", ".join(selection_list) + f" FROM {relation.relation_name}"
            union_list.append(curr_relation_string)

        sql_command = f"INSERT INTO {new_relation_name} {' UNION '.join(union_list)}"

        self.run_sql(sql_command)
        return new_relation

    def operator_copy(self, src_rel: Relation, output_relation_name=None) -> Relation:
        src_rel_name = src_rel.relation_name
        if output_relation_name:
            dest_rel_name = output_relation_name

            # check if the relation already exists
            if self.is_table_exists(output_relation_name):
                self.clear_table(output_relation_name)
            else:
                dest_decl_rel = RelationDeclaration(dest_rel_name, src_rel.type_list)
                self.declare_relation(dest_decl_rel)

        else:
            dest_rel_name = self._create_unique_relation(arity=len(src_rel.type_list),
                                                         prefix=f"{src_rel_name}{self.SQL_SEPARATOR}{self.COPY_PREFIX}")

        dest_rel = Relation(dest_rel_name, src_rel.term_list, src_rel.type_list)

        # sql part
        sql_command = f"INSERT INTO {dest_rel_name} {self.SQL_SELECT} * FROM {src_rel_name}"
        self.run_sql(sql_command)

        return dest_rel

    def is_table_exists(self, table_name) -> bool:
        """
        Checks whether a table exists in the database.

        @param table_name: the table which is checked for existence.
        @return: True if it exists, else False.
        """
        sql_check_if_exists = (f"{self.SQL_SELECT} name FROM {self.SQL_TABLE_OF_TABLES} WHERE "
                               f"type='table' AND name='{table_name}'")
        return bool(self.run_sql(sql_check_if_exists))

    def _datatype_to_sql_type(self, datatype: DataTypes):
        return self.DATATYPE_TO_SQL_TYPE[datatype]

    def _convert_relation_term_to_string(self, datatype: DataTypes, term) -> str:
        if datatype == DataTypes.span:
            return self._get_span_string(term)
        else:
            return term

    def __del__(self):
        self.sql_conn.close()

    def _get_col_name(self, col_id: int) -> str:
        return f'{self.RELATION_COLUMN_PREFIX}{col_id}'

    @staticmethod
    def _get_free_variable_indexes(type_list) -> List[int]:
        return [i for i, term_type in enumerate(type_list) if (term_type is DataTypes.free_var_name)]

    def clear_table(self, table_name) -> None:
        sql_command = f"DELETE FROM {table_name}"
        self.run_sql(sql_command)

    def get_table_len(self, table: str) -> int:
        sql_command = f"SELECT COUNT(*) FROM {table}"
        table_len, = self.run_sql(sql_command)[0]
        return table_len


class ExecutionBase(ABC):
    """
    Abstraction for a class that gets a term graph and executes it
    """

    # TODO@niv: i don't understand why we need this class, since `GenericExecution` is already generic.
    def __init__(self, parse_graph: GraphBase, term_graph: ComputationTermGraph,
                 symbol_table: SymbolTableBase, rgxlog_engine: RgxlogEngineBase):
        """
        @param parse_graph: a term graph to execute.
        @param symbol_table: a symbol table.
        @param rgxlog_engine: a rgxlog engine that will be used to execute the term graph.
        """

        super().__init__()
        self.parse_graph = parse_graph
        self.term_graph = term_graph
        self.symbol_table = symbol_table
        self.rgxlog_engine = rgxlog_engine

    @abstractmethod
    def execute(self) -> Tuple[Query, List]:
        """
        Executes the term graph.
        """
        pass


class GenericExecution(ExecutionBase):
    """
    Executes a parse graph
    this execution is generic, meaning it does not require any specific kind of term graph, symbol table or
    rgxlog engine in order to work.
    this execution performs no special optimization and merely serves as an interface between the term graph
    and the rgxlog engine.

    the main idea behind this class is that it uses the `term_graph` to understand how relations are related to
    one another, and thanks to that information, it is able to execute the commands in the `parse_graph`.
    for example, let's say the parse graph looks like this:

    ```
    (root) -> (query relation a)
    ```

    and the term graph looks like this:

    (a)  --> union --> (b)
                   --> (c)

    the execution class will perform a union over `b` and `c`, and put it in a new relation, let's say `union_b_c`.
    then it will copy `union_b_c` into `a`, and finally it will query `a` and return the result.
    """

    def __init__(self, parse_graph: GraphBase, term_graph: ComputationTermGraph,
                 symbol_table: SymbolTableBase, rgxlog_engine: RgxlogEngineBase):
        super().__init__(parse_graph, term_graph, symbol_table, rgxlog_engine)

    def execute(self) -> Tuple[Query, List]:
        parse_graph = self.parse_graph
        rgxlog_engine = self.rgxlog_engine
        exec_result = None

        # get the parse_graph's node ids. note that the order of the ids does not actually matter as long as the statements
        # are ordered the same way as they were in the original program
        parse_node_ids = parse_graph.post_order_dfs()

        # execute each non computed statement in the parse graph
        for parse_id in parse_node_ids:
            parse_node_attrs = parse_graph[parse_id]

            if parse_node_attrs["state"] is EvalState.COMPUTED:
                continue

            # the parse node is not computed, get its type and compute it accordingly
            parse_node_type = parse_node_attrs["type"]

            if parse_node_type in ("root", "relation"):
                # pass and not continue, because we want to mark them as computed
                pass

            elif parse_node_type == "rule":
                rule = parse_node_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.declare_relation(rule.head_relation.as_relation_declaration())

            elif parse_node_type == "relation_declaration":
                relation_decl = parse_node_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.declare_relation(relation_decl)

            elif parse_node_type == "add_fact":
                fact = parse_node_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.add_fact(fact)

            elif parse_node_type == "remove_fact":
                fact = parse_node_attrs[VALUE_ATTRIBUTE]
                rgxlog_engine.remove_fact(fact)

            elif parse_node_type == "query":
                # we return the query as well as the result, because we print as part of the output
                query = parse_node_attrs[VALUE_ATTRIBUTE]
                self.compute_rule(query.relation_name)
                exec_result = (query, rgxlog_engine.query(query))

            else:
                raise ValueError("illegal node type in parse graph")

            # statement was executed, mark it as "computed"
            parse_graph.set_node_attribute(parse_id, "state", EvalState.COMPUTED)

        return exec_result

    def compute_node(self, node_id: int) -> None:
        """
        Computes the current node based on its type.

        @param node_id: the current node.
        """
        term_graph = self.term_graph

        term_attrs = term_graph[node_id]
        if term_attrs["state"] is EvalState.COMPUTED:
            return

        term_type = term_attrs["type"]

        if term_type in "get_rel":
            term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, term_attrs["value"])

        elif term_type == "rule_rel":
            self.compute_rule_rel_node(term_attrs)

        elif term_type == "union":
            self.compute_union_node(node_id)

        elif term_type == "join":
            self.compute_join_node(node_id)

        elif term_type == "project":
            self.compute_project_node(node_id, term_attrs)

        elif term_type == "calc":
            self.compute_calc_node(node_id, term_attrs)

        elif term_type == "select":
            self.compute_select_node(node_id, term_attrs)

        else:
            raise ValueError(f"illegal term type in rule's execution graph. The bad type is {term_type}")

        # statement was executed, mark it as "computed" or "visited"
        compute_status = EvalState.COMPUTED if self.is_node_computed(node_id) else EvalState.VISITED
        term_graph.set_node_attribute(node_id, 'state', compute_status)

    def compute_rule_rel_node(self, term_attrs: Dict) -> None:
        """
        Computes a rule rel node.

        @param term_attrs: the attributes of the rule rel node.
        """
        rule_rel = term_attrs[VALUE_ATTRIBUTE]
        rule_name = rule_rel.relation_name
        rel_in: Relation = self.get_child_relation(rule_name)
        copy_rel = self.rgxlog_engine.operator_copy(rel_in, rule_name)
        self.term_graph.set_node_attribute(rule_name, OUT_REL_ATTRIBUTE, copy_rel)

    def compute_join_node(self, node_id: int) -> None:
        """
        Computes a join node.

        @param node_id: the node.
        """

        join_rel = self.rgxlog_engine.operator_join(self.get_children_relations(node_id))
        self.term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, join_rel)

    def compute_project_node(self, node_id: int, term_attrs: Dict) -> None:
        """
        Computes a project node.

        @param node_id: the node.
        @param term_attrs: the attributes of the node.
        """

        output_rel: Relation = self.get_child_relation(node_id)
        project_info = term_attrs[VALUE_ATTRIBUTE]
        project_rel = self.rgxlog_engine.operator_project(output_rel, project_info)
        self.term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, project_rel)

    def compute_calc_node(self, node_id: int, term_attrs: Dict) -> None:
        """
        Computes a calc node.

        @param node_id: the node.
        @param term_attrs: the attributes of the node.
        """

        children = self.get_children_relations(node_id)
        rel_in = children[0] if children else None
        # note: we use the same `VALUE_ATTRIBUTE` keyword for different things to be able to print it easily
        # when printing the tree
        ie_rel_in: IERelation = term_attrs[VALUE_ATTRIBUTE]
        ie_func_data = self.symbol_table.get_ie_func_data(ie_rel_in.relation_name)
        ie_rel_out = self.rgxlog_engine.compute_ie_relation(ie_rel_in, ie_func_data, rel_in)
        self.term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, ie_rel_out)

    def compute_union_node(self, node_id: int) -> None:
        """
        Computes a union node.

        @param node_id: the node.
        """

        union_rel = self.rgxlog_engine.operator_union(self.get_children_relations(node_id))
        self.term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, union_rel)

    def compute_select_node(self, node_id: int, term_attrs: Dict) -> None:
        """
        Computes a select node.

        @param node_id: the node.
        @param term_attrs: the attributes of the node.
        """

        output_rel = self.get_child_relation(node_id)
        select_info = term_attrs[VALUE_ATTRIBUTE]
        select_rel = self.rgxlog_engine.operator_select(output_rel, select_info)
        self.set_output_relation(node_id, select_rel)

    def is_node_computed(self, node_id) -> bool:
        """
        Finds out whether the node is computed.

        @param node_id: the node for which we check the status.
        @return: True if all the children of the node are computed or it has no children, False otherwise.
        """

        children = self.term_graph.get_children(node_id)
        if not children:
            return True

        children_statuses_is_computed = [self.term_graph[child_id]["state"] is EvalState.COMPUTED
                                         for child_id in children]
        return all(children_statuses_is_computed)

    def set_output_relation(self, node_id, relation: Relation) -> None:
        """
        Sets the output relation of a node in term graph.

        @param node_id: the id of the node.
        @param relation: the output relation.
        """
        self.term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, relation)

    def get_children_relations(self, node_id) -> List[Relation]:
        """
        Gets the node's children output relations.

        @param node_id: a node.
        @return: a list containing the children output relations.
        """
        term_graph = self.term_graph
        relations_ids = term_graph.get_children(node_id)
        relations_nodes = [term_graph[rel_id] for rel_id in relations_ids]
        relations = [rel_node[OUT_REL_ATTRIBUTE] for rel_node in relations_nodes]
        return relations

    def get_child_relation(self, node_id) -> Relation:
        """
        Gets the node's child output relation.
        @note: this method is called when we know that the node has at most one child.

        @param node_id: a node.
        @return: the output relation of the node's child.
        """
        children = self.get_children_relations(node_id)
        assert len(children) <= 1, "this node should have exactly one child"
        return children[0]

    def compute_rule(self, relation_name: str, to_reset: bool = True, only_one_iteration: bool = False) -> bool:
        """
        Computes the rule (including the mutual recursive rules).

        @param relation_name: the name of the relation to compute.
        @param to_reset: if set to True we reset the nodes after the computation.
        @param only_one_iteration: if set to True we evaluate one iteration, Otherwise we do fixed-point.
        """
        term_graph = self.term_graph
        rgxlog_engine = self.rgxlog_engine

        # check if the relation is base relation
        if not term_graph.has_node(relation_name):
            return True

        # stores all the nodes that were visited during the dfs
        visited_nodes = set()
        mutually_recursive = term_graph.get_mutually_recursive_relations(relation_name)

        # declare methods used in rule computation
        def compute_iteration() -> bool:
            """
            Computes one iteration. if reaches a mutually recursive relation it uses the relation current state
            (rather than computing it).

            @return: whether the rule we computed converged (no new tuples).
            """

            initial_len = rgxlog_engine.get_table_len(relation_name)
            compute_dfs(relation_name)

            return rgxlog_engine.get_table_len(relation_name) == initial_len

        def compute_dfs(node_id) -> None:
            """
            Runs postorder dfs over the term graph and evaluates the tree.

            @param node_id: the current node.
            """
            if is_stop_dfs(node_id):
                return

            visited_nodes.add(node_id)
            children = self.term_graph.get_children(node_id)
            for child in children:
                compute_dfs(child)

            self.compute_node(node_id)

        def is_stop_dfs(node_id) -> bool:
            """
            Catches the cases of rule rel.

            @param node_id: the current node.
            @return: True if we can continue the DFS, False otherwise.
            """

            if node_id in visited_nodes:
                return True

            term_attrs = self.term_graph[node_id]
            if term_attrs["state"] is EvalState.COMPUTED:
                return True

            # if type is not rule_rel it's fine to continue the dfs
            if term_attrs["type"] != "rule_rel":
                return False

            rule_rel = term_attrs[VALUE_ATTRIBUTE]
            if rule_rel.relation_name not in mutually_recursive:
                # computes the independent rule and stop
                self.compute_rule(rule_rel.relation_name, to_reset=False)
                return True

            # if rule rel is the rule we're currently computing - continue the dfs
            if rule_rel.relation_name == relation_name:
                return False

            # in case of dependent rule we use the current state of that rule
            term_graph.set_node_attribute(node_id, OUT_REL_ATTRIBUTE, rule_rel)
            return True

        def set_visited_nodes(state_: EvalState) -> None:
            """
            Marks all the nodes that were visited during the computation as not computed.

            @param state_: the state of the visited nodes.
            """

            for term_id in self.term_graph.post_order_dfs_from(relation_name):
                self.term_graph.set_node_attribute(term_id, "state", state_)

        if only_one_iteration:
            return compute_iteration()

        # clear all the mutually recursive tables.
        rgxlog_engine.clear_tables(mutually_recursive)

        fixed_point = False
        while not fixed_point:
            # computes one iteration for all of the mutually recursive rules
            stopped = [self.compute_rule(relation, only_one_iteration=True)
                       for relation in mutually_recursive]

            # we stop iterating when all the rules converged at the same step
            fixed_point = all(stopped)

        state = EvalState.NOT_COMPUTED if to_reset else EvalState.COMPUTED
        set_visited_nodes(state)


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

    print(my_engine.get_table_len("yoyo"))
