import logging
import sqlite3 as sqlite
import tempfile
from abc import ABC, abstractmethod
from itertools import count
from jinja2 import Template
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple, Any, List, Union, Dict, no_type_check, Sequence

from rgxlog.engine.datatypes.ast_node_types import RelationDeclaration, AddFact, RemoveFact, Query, IERelation, Relation
from rgxlog.engine.datatypes.primitive_types import Span, DataTypes, DataTypeMapping
from rgxlog.engine.ie_functions.ie_function_base import IEFunction
from rgxlog.engine.utils.general_utils import strip_lines, string_to_span, get_free_var_to_relations_dict, get_output_free_var_names, extract_one_relation

# rgx constants
RESERVED_RELATION_PREFIX = "__rgxlog__"

FALSE_VALUE: List = []
TRUE_VALUE: List[Tuple] = [tuple()]

logger = logging.getLogger(__name__)


class RgxlogEngineBase(ABC):
    """
    An abstraction for a rgxlog execution engine, used by GenericExecution.
    it includes relational algebra operators like join and project, database modification operators like
    `add_fact` (insert) and `remove_fact` (delete), and rgxlog-specific operators like `compute_ie_relation`.
    """

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def declare_relation_table(self, relation_decl: RelationDeclaration) -> None:
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
    def query(self, query: Query) -> List[Tuple]:
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
    def clear_relation(self, table: str) -> None:
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
            self.clear_relation(table)

    @abstractmethod
    def get_table_len(self, table: str) -> int:
        """
        @param table: name of a table.
        @return: number of tuples inside the table.
        """
        pass

    @abstractmethod
    def compute_ie_relation(self, ie_relation: IERelation, ie_func: IEFunction, bounding_relation: Optional[Relation]) -> Relation:
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
        @param ie_func: the data for the ie function that will be used to compute the ie relation.
        @param bounding_relation: a relation that contains the inputs for ie_funcs. the actual input needs to be
                                  queried from it2
        @return: a normal relation that contains all of the resulting tuples in the rgxlog engine.
        """
        pass

    @abstractmethod
    def _convert_relation_term_to_string_or_int(self, datatype: DataTypes, term: Any) -> Union[str, int]:
        """
        Return the string/int representation of a relation term, e.g. "[1,4)"

        @param datatype: the type of the term.
        @param term: the term object itself.
        @return: string/int representation.
        """
        pass

    @abstractmethod
    def operator_select(self, relation: Relation, select_info: Set[Tuple[int, Any, DataTypes]], *args: Any) -> Relation:
        """
        @param relation: the relation from which we select tuples.
        @param select_info: set of tuples. each tuple contains the index of the column, the value to select
                            and the type of the column.
        @return: a filtered relation.
        """
        pass

    @abstractmethod
    def operator_join(self, relations: List[Relation], *args: Any) -> Relation:
        """
        Performs a join between all of the relations in the relation list and saves the result to a new relation.
        the results of the join are filtered so they only include columns in the relations that were defined by
        a free variable term.
        all of the relations in relation_list must be normal (not ie relations)

        for an example and more details see RgxlogEngineBase.join_relations.

        @param relations: a list of normal relations.
        @return: a new relation as described above.
        """
        pass

    @abstractmethod
    def operator_project(self, relation: Relation, project_vars: List[str], *args: Any) -> Relation:
        """
        @param relation: the relation on which we project.
        @param project_vars: a list of variables on which we project.
        @return: the projected relation.
        """
        pass

    @abstractmethod
    def operator_union(self, relations: List[Relation], *args: Any) -> Relation:
        """
        Relation union.
        @note: we assume that all the relations have same free_vars in the same order.


        @param relations: a list of relations to unite.
        @return: the united relation.
        """
        pass

    @abstractmethod
    def operator_copy(self, src_rel: Relation, output_relation: Optional[Relation] = None, *args: Any) -> Relation:
        """
        Copies computed_relation to rule_relation.

        @param src_rel: the relation to copy from.
        @param output_relation: if this is None, create a unique name for the output relation.
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
    DATABASE_SUFFIX = "_sqlite"

    # ~~ dunder methods ~~
    def __init__(self, database_name: Optional[str] = None) -> None:
        """
        Creates/opens an SQL database file + connection.

        @param database_name: open an existing database instead of a new one.
        """
        super().__init__()
        self.unique_relation_id_counter = count()

        self.df_filename = SqliteEngine._get_db_filename(database_name)
        logger.info(f"using database file: {self.df_filename}")

        self.sql_conn = sqlite.connect(self.df_filename)
        self.sql_cursor = self.sql_conn.cursor()

    def __del__(self) -> None:
        self.sql_conn.close()

    # ~~ simple logic methods ~~
    def add_fact(self, fact: AddFact) -> None:
        """
        Add a row into an existing table.
        """
        num_types = len(fact.type_list)
        col_names = [f"{self._get_col_name(i)}" for i in range(num_types)]
        col_values = [self._convert_relation_term_to_string_or_int(datatype, term) for datatype, term in
                      zip(fact.type_list, fact.term_list)]

        template_dict = {"col_values": col_values, "fact": fact, "col_names": col_names}

        sql_template = ("""
        INSERT INTO {{fact.relation_name}} ({{col_names | join(", ")}})
        VALUES ({{col_values | join(", ")}})
        """)

        self._run_sql_from_jinja_template(sql_template, template_dict)

    def remove_fact(self, fact: RemoveFact) -> None:
        num_types = len(fact.type_list)
        col_names = [f"{self._get_col_name(i)}" for i in range(num_types)]
        col_values = [self._convert_relation_term_to_string_or_int(datatype, term) for datatype, term in
                      zip(fact.type_list, fact.term_list)]
        constraint_pairs = zip(col_names, col_values)

        template_dict = {"fact": fact, "constraint_pairs": constraint_pairs}

        sql_template = ("""
        DELETE FROM {{fact.relation_name}} WHERE
        {% for left, right in constraint_pairs %}
            {{left}}={{right}}
            {% if not loop.last %}
                ,
            {% endif %}
        {% endfor %}
        """)

        self._run_sql_from_jinja_template(sql_template, template_dict)

    def query(self, query: Query, allow_duplicates: bool = False) -> List[Tuple]:
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

        query_result = self._run_sql(f"{self.SQL_SELECT} * FROM {projected_relation_name}", do_commit=True)

        self.remove_table(selected_relation_name)
        self.remove_table(projected_relation_name)

        # we need to convert values of type `True` and `Span` into their true form. `False` is already in its true form.
        if (not has_free_vars) and query_result != FALSE_VALUE:
            query_result = TRUE_VALUE

        spanned_query_result = self._convert_strings_to_spans_in_query_result(query_result)

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
            self._run_sql(sql_command)

    def declare_relation_table(self, relation_decl: RelationDeclaration) -> None:
        """
        Declares a relation as an SQL table, whose types are named t0, t1, ...
        if the relation is already declared, do nothing.

        @param relation_decl: the declaration info.
        """
        # create the relation table. we don't use an id because it would allow inserting the same values twice
        # note: to ignore duplicates, we can either use UNIQUE when creating the table, or DISTINCT when selecting.
        #  right now we use DISTINCT
        if self.is_table_exists(relation_decl.relation_name):
            return

        # note: sqlite can guess datatypes. if this causes bugs, use `{self._datatype_to_sql_type(relation_type)}`.
        col_names = [f"{self._get_col_name(i)}" for i in range(len(relation_decl.type_list))]
        template_dict = {"rel_name": relation_decl.relation_name, "col_names": col_names}
        sql_template = 'CREATE TABLE {{rel_name}} ({{col_names | join(", ")}})'

        self._run_sql_from_jinja_template(sql_template, template_dict)

    def is_table_exists(self, table_name: str) -> bool:
        """
        Checks whether a table exists in the database.

        @param table_name: the table which is checked for existence.
        @return: True if it exists, else False.
        """
        sql_check_if_exists = (f"{self.SQL_SELECT} name FROM {self.SQL_TABLE_OF_TABLES} WHERE "
                               f"type='table' AND name='{table_name}'")
        return bool(self._run_sql(sql_check_if_exists))

    def clear_relation(self, table_name: str) -> None:
        sql_command = f"DELETE FROM {table_name}"
        self._run_sql(sql_command)

    def get_table_len(self, table_name: str) -> int:
        sql_command = f"SELECT COUNT(*) FROM {table_name}"
        table_len, = self._run_sql(sql_command)[0]
        return table_len

    # ~~ operator methods ~~
    @extract_one_relation
    def operator_select(self, src_relation: Relation, constant_variables_info: Set[Tuple[int, Any, DataTypes]], *args: Any) -> Relation:
        """
        Performs sql WHERE, whose constraints are based on `select_info`

        @param src_relation: the relation from which we select tuples.
        @param constant_variables_info: a set of tuples. each tuple contains the index of the column, the value to select (a constant variable),
                                        and the type of the column.

        @return: a filtered relation.
        """

        constant_var_pairs = []
        equal_var_pairs = []

        def _create_new_relation_for_select_result() -> Relation:
            new_term_list = src_relation.term_list
            new_arity = len(new_term_list)
            new_type_list = src_relation.type_list
            new_relation_name = self._create_unique_relation(new_arity, prefix=f"{src_relation.relation_name}{self.SQL_SEPARATOR}{self.SELECT_PREFIX}")
            return Relation(new_relation_name, new_term_list, new_type_list)

        def _extract_constant_variable_pairs() -> List[Tuple[str, str]]:
            """
            generate constraints based on `constant_variables_info`

            @return: column + constant pairs, which are used as constraints for `select`
            """
            for i, value, datatype in constant_variables_info:
                col_name = self._get_col_name(i)
                value = self._convert_relation_term_to_string_or_int(datatype, value)
                constant_var_pairs.append((col_name, value))
            return constant_var_pairs

        def _extract_equal_variable_pairs() -> List[Tuple[str, str]]:
            """
            add constraints based on repeating free variables like a(X,X,8,Y,X) - add constrains to make the 'X's equal.
            notice we only have a single relation here, so we don't have to rename columns.
            for the example above, the `src_relation_var_dict` looks like this:
            {X:[(a,0), (a,1), (a,4)], Y:[(a,3)]}
            in the loop below, we will get, for the variable `X`:
            `first_pair`=`(a,0)`
            `other_pairs`=`[(a,1), (a,4)]`
            and then, our constraints (`equal_var_pairs`) will look like this:
            `[("col0","col1"), ("col0", "col4")]`

            @return: pairs of equal columns
            """
            # get variables in var_dict that repeat - used below to add constraints
            src_relation_var_dict = get_free_var_to_relations_dict({src_relation})
            repeating_vars_in_relation = [(free_var, pairs) for (free_var, pairs) in src_relation_var_dict.items() if (len(pairs) > 1)]

            # convert repeated variables to pairs of columns which should be equal
            for free_var, pairs in repeating_vars_in_relation:
                first_pair, other_pairs = pairs[0], pairs[1:]
                first_index = first_pair[1]
                first_col_name = self._get_col_name(first_index)
                for _, second_index in other_pairs:
                    second_col_name = self._get_col_name(second_index)
                    equal_var_pairs.append((first_col_name, second_col_name))
            return equal_var_pairs

        selected_relation = _create_new_relation_for_select_result()

        constant_constraints = _extract_constant_variable_pairs()
        equal_var_constraints = _extract_equal_variable_pairs()
        all_constraints = constant_constraints + equal_var_constraints

        template_dict = {"new_rel_name": selected_relation.relation_name, "SELECT": self.SQL_SELECT, "src_rel_name": src_relation.relation_name,
                         "all_constraints": all_constraints}

        sql_template = ("""
        INSERT INTO {{new_rel_name}} {{SELECT}} * FROM {{src_rel_name}}
        {%- if all_constraints %}
        WHERE
            {% for left, right in all_constraints %}
                {{left}}={{right}}
                {% if not loop.last %}
                    AND
                {% endif %}
            {% endfor %}
        {%- endif -%}
        """)

        self._run_sql_from_jinja_template(sql_template, template_dict)

        return selected_relation

    def operator_join(self, relations: List[Relation], *args: Any) -> Relation:
        """
        note: SQL's inner_join without `IN` is actually cross-join (product), so this covers product as well.

        @param relations: a list of normal relations.
        @return: a new relation as described above.
        """
        on_constraints_list: List[Tuple[str, str]] = []
        inner_join_list: List[Tuple[str, str]] = []
        free_var_cols: List[Tuple[str, str]] = []

        def _create_new_relation_for_join_result() -> Relation:
            # get all of the free variables in all of the relations, they'll serve as the terms of the joined relation
            free_var_sets: Sequence[Set] = [get_output_free_var_names(relation) for relation in relations]
            free_vars: Set = set().union(*free_var_sets)
            joined_relation_terms = list(free_vars)

            # get the type list of the joined relation (all of the terms are free variables)
            relation_arity = len(joined_relation_terms)
            relation_types = [DataTypes.free_var_name] * relation_arity

            # declare the joined relation in sql and get its name
            joined_relation_name = self._create_unique_relation(relation_arity, prefix=self.JOIN_PREFIX)

            # create a structured node of the joined relation
            return Relation(joined_relation_name, joined_relation_terms, relation_types)

        @no_type_check
        def _extract_col_names_and_constraints() -> None:
            # iterate over the free_vars and do 2 things:
            for i, free_var in enumerate(joined_relation.term_list):
                free_var_pairs: List[Tuple[Union[Relation, IERelation], int]] = var_dict[free_var]
                first_pair, other_pairs = free_var_pairs[0], free_var_pairs[1:]

                relation_with_free_var, first_index = first_pair
                name_of_relation_with_free_var = relation_temp_names[relation_with_free_var]
                new_col_name = self._get_col_name(i)
                first_col_name = self._get_col_name(first_index)

                # 1. name the new columns. the columns should be named col0, col1, etc.
                old_col_name = f"{name_of_relation_with_free_var}.{first_col_name}"
                new_temp_col_name = f"{new_col_name}"
                free_var_cols.append((old_col_name, new_temp_col_name))

                # 2. create the comparison between all of them, using `ON`
                for (second_relation, second_index) in other_pairs:
                    second_col_name = self._get_col_name(second_index)
                    name_of_second_relation = relation_temp_names[second_relation]
                    first_full_col_name = f"{name_of_relation_with_free_var}.{first_col_name}"
                    second_full_col_name = f"{name_of_second_relation}.{second_col_name}"
                    on_constraints_list.append((first_full_col_name, second_full_col_name))

        assert len(relations) > 0, "can't join an empty list"
        if len(relations) == 1:
            return relations[0]

        # create a mapping between the relations and their temporary names for sql
        relation_temp_names = {relation: f"table{i}" for (i, relation) in enumerate(relations)}
        var_dict = get_free_var_to_relations_dict(set(relations))

        joined_relation = _create_new_relation_for_join_result()
        _extract_col_names_and_constraints()

        # first relation - used after `FROM`
        first_relation, other_relations = relations[0], relations[1:]

        # every next relation is used after `INNER JOIN`
        for relation in other_relations:
            old_relation_name = relation.relation_name
            new_temp_relation_name = relation_temp_names[relation]
            inner_join_list.append((old_relation_name, new_temp_relation_name))

        template_dict = {"new_rel_name": joined_relation.relation_name, "SELECT": self.SQL_SELECT, "new_columns_names": free_var_cols,
                         "first_rel_name": first_relation.relation_name, "first_rel_temp_name": relation_temp_names[first_relation],
                         "relations_temp_names": inner_join_list, "join_constraints": on_constraints_list}

        sql_template = ("""
        INSERT INTO {{new_rel_name}} {{SELECT}}
        {% for left, right in new_columns_names %}
            {{left}} AS {{right}}
            {% if not loop.last %}
            ,
            {% endif %}
        {% endfor %}

        FROM {{first_rel_name}} AS {{first_rel_temp_name}}
        {% for left, right in relations_temp_names %}
            INNER JOIN {{left}} AS {{right}}
        {% endfor %}

        {%- if join_constraints %}
            ON
            {% for left, right in join_constraints %}
                {{left}}={{right}}
                {% if not loop.last %}
                    AND
                {% endif %}
            {% endfor %}
        {%- endif -%}
        """)

        self._run_sql_from_jinja_template(sql_template, template_dict)

        return joined_relation

    @extract_one_relation
    def operator_project(self, src_relation: Relation, project_vars: List[str], *args: Any) -> Relation:
        """
        Performs SQL select.

        @param src_relation: the relation on which we project.
        @param project_vars: a list of variables on which we project.
        @return: the projected relation.
        """
        project_indexes = []
        dest_col_list = []

        def _create_new_relation_for_project_result() -> Relation:
            # get the indexes to project from (in `src_relation`) based on `var_dict`
            var_dict: Dict[str, List[Tuple[Union[Relation, IERelation], int]]] = get_free_var_to_relations_dict({src_relation})

            for var in project_vars:
                var_index_in_src = (var_dict[var][0][1])
                project_indexes.append(var_index_in_src)

            src_type_list = src_relation.type_list
            new_type_list = [src_type_list[i] for i in project_indexes]
            new_arity = len(project_vars)
            new_relation_name = self._create_unique_relation(new_arity, prefix=f"{src_relation.relation_name}{self.SQL_SEPARATOR}{self.PROJECT_PREFIX}")
            return Relation(new_relation_name, project_vars, new_type_list)

        def _extract_project_col_names() -> None:
            for new_col_num, src_col_num in enumerate(project_indexes):
                new_col = self._get_col_name(new_col_num)
                src_col = self._get_col_name(src_col_num)
                if new_col == src_col:
                    # this prevents selecting "colX AS colX", for aesthetic reasons
                    dest_col_list.append(src_col)
                else:
                    dest_col_list.append(f"{src_col} AS {new_col}")

        new_relation = _create_new_relation_for_project_result()
        _extract_project_col_names()

        sql_command = (f"INSERT INTO {new_relation.relation_name} {self.SQL_SELECT} {', '.join(dest_col_list)}"
                       f" FROM {src_relation.relation_name}")

        self._run_sql(sql_command)
        return new_relation

    def operator_union(self, relations: List[Relation], *args: Any) -> Relation:
        """
        @param relations: a list of relations to unite.
        @return: the united relation.
        """
        union_list: List[str] = []

        def _create_new_relation_for_union() -> Relation:
            new_relation_name = self._create_unique_relation(len(relations[0].term_list), prefix=self.UNION_PREFIX)
            new_term_list = relations[0].term_list
            new_type_list = relations[0].type_list
            return Relation(new_relation_name, new_term_list, new_type_list)

        def _extract_union_selections() -> None:
            """
            create the union command by iterating over the relations and finding the index of each term
            @return: None
            """

            for relation in relations:
                # we assume the same order in the source and the destination, so no need to use 'AS'
                selection_list = [self._get_col_name(col_index) for col_index in range(len(united_relation.term_list))]

                # render a jinja template into an SQL select
                relation_string_template = '{{SELECT}} {{ selected_cols | join(", ") }} FROM {{rel_name}}'
                template_dict = {"SELECT": self.SQL_SELECT, "selected_cols": selection_list, "rel_name": relation.relation_name}
                rendered_relation_string = Template(strip_lines(relation_string_template)).render(**template_dict)
                union_list.append(rendered_relation_string)

        new_arity = len(relations)
        assert new_arity > 0, "cannot perform union on an empty list"
        if new_arity == 1:
            return relations[0]

        united_relation = _create_new_relation_for_union()
        _extract_union_selections()

        sql_command = f"INSERT INTO {united_relation.relation_name} {' UNION '.join(union_list)}"

        self._run_sql(sql_command)
        return united_relation

    @extract_one_relation
    def operator_copy(self, src_rel: Relation, output_relation: Optional[Relation] = None, *args: Any) -> Relation:
        src_rel_name = src_rel.relation_name
        if output_relation:
            dest_rel_name = output_relation.relation_name

            # check if the relation already exists
            if self.is_table_exists(dest_rel_name):
                self.clear_relation(dest_rel_name)
            else:
                dest_decl_rel = RelationDeclaration(dest_rel_name, src_rel.type_list)
                self.declare_relation_table(dest_decl_rel)

        else:
            dest_rel_name = self._create_unique_relation(arity=len(src_rel.type_list),
                                                         prefix=f"{src_rel_name}{self.SQL_SEPARATOR}{self.COPY_PREFIX}")

        dest_rel = Relation(dest_rel_name, src_rel.term_list, src_rel.type_list)

        # sql part
        sql_command = f"INSERT INTO {dest_rel_name} {self.SQL_SELECT} * FROM {src_rel_name}"
        self._run_sql(sql_command)

        return dest_rel

    @no_type_check
    def compute_ie_relation(self, ie_relation: IERelation, ie_func: IEFunction, bounding_relation: Optional[Relation]) -> Relation:
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

        def _looks_like_span(checked_value):
            """
            checks whether `term` is a tuple of 2 numbers
            @param checked_value: the value to check
            @return: True/False according to the above description
            """
            if isinstance(checked_value, tuple) and len(checked_value) == 2:
                try:
                    _, _ = int(checked_value[0]), int(checked_value[1])
                    return True
                except ValueError:
                    # an item in the tuple could not be converted to int
                    return False
            return False

        def _get_all_ie_function_inputs():
            # define the ie input relation
            if bounding_relation is None:
                # special case where the ie relation is the first rule body relation
                # in this case, the ie input relation is defined exclusively by constant terms, i.e, by a single tuple
                # add that tuple as a fact to the input relation
                # create the input relation for the ie function, and also declare it inside SQL
                all_ie_inputs = [tuple(ie_relation.input_term_list)]
            else:
                # get a list of inputs to the ie function - some of them may be constants
                inputs_without_constants = self._get_all_relation_tuples(bounding_relation)
                all_ie_inputs = []
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
                    all_ie_inputs.append(tuple(result_input_list))
            return all_ie_inputs

        def _format_ie_output(raw_ie_output):
            # the output should be a tuple, but if a single value is returned, we accept it as well
            if isinstance(raw_ie_output, (str, int, Span)):
                return [raw_ie_output]
            else:
                # the user is allowed to represent a span in an ie output as a tuple of length 2
                # convert said tuples to spans
                return [Span(int(term[0]), int(term[1])) if _looks_like_span(term) else term for term in list(raw_ie_output)]

        def _run_ie_function_and_add_outputs_as_facts():
            # run the ie function on each input and process the outputs
            for ie_input in ie_inputs:
                # run the ie function on the input, resulting in a list of tuples
                ie_outputs = ie_func.ie_function(*ie_input)
                # process each ie output and add it to the output relation
                for ie_output in ie_outputs:
                    spanned_ie_output = _format_ie_output(ie_output)

                    # assert the ie output is properly typed
                    self._assert_ie_output_properly_typed(ie_input, spanned_ie_output, ie_output_schema, ie_relation)

                    # add the output as a fact to the output relation
                    # notice - repetitions are ignored here (results are in a set)
                    if len(spanned_ie_output) != 0:
                        output_fact = AddFact(output_relation.relation_name, spanned_ie_output, list(ie_output_schema))
                        self.add_fact(output_fact)

        ie_relation_name = ie_relation.relation_name
        # create the output relation for the ie function, and also declare it inside SQL
        output_relation_arity = len(ie_relation.output_term_list)
        output_relation_name = self._create_unique_relation(output_relation_arity,
                                                            prefix=f'{ie_relation_name}{self.SQL_SEPARATOR}output')
        output_relation = Relation(output_relation_name, ie_relation.output_term_list, ie_relation.output_type_list)

        ie_inputs = _get_all_ie_function_inputs()
        ie_output_schema = ie_func.get_output_types(output_relation_arity)
        _run_ie_function_and_add_outputs_as_facts()

        return output_relation

    # ~~ util methods ~~
    def _run_sql_from_jinja_template(self, sql_template: str, template_dict: Optional[dict] = None) -> None:
        if not template_dict:
            template_dict = {}
        sql_command = Template(strip_lines(sql_template)).render(**template_dict)
        self._run_sql(sql_command)

    def _run_sql(self, command: str, command_args: Optional[List] = None, do_commit: bool = False) -> List:
        logger.debug(f"sql {command=}")
        if command_args:
            logger.debug(f"...with args: {command_args}")

        if command_args:
            self.sql_cursor.execute(command, command_args)
        else:
            self.sql_cursor.execute(command)

        if do_commit:
            # save to file
            self.sql_conn.commit()

        return self.sql_cursor.fetchall()

    def _create_unique_relation(self, arity: int, prefix: str = "") -> str:
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
        self.declare_relation_table(unique_relation_decl)
        return unique_relation_name

    def _datatype_to_sql_type(self, datatype: DataTypes) -> str:
        return self.DATATYPE_TO_SQL_TYPE[datatype]

    def _convert_relation_term_to_string_or_int(self, datatype: DataTypes, term: DataTypeMapping.term) -> Union[str, int]:
        if datatype is DataTypes.integer:
            assert isinstance(term, int), "an integer must be of int type"
            return term
        else:
            unquoted_term = str(term).strip('"')
            return f'"{unquoted_term}"'

    def _get_col_name(self, col_id: int) -> str:
        return f'{self.RELATION_COLUMN_PREFIX}{col_id}'

    @staticmethod
    def _get_free_variable_indexes(type_list: Sequence[DataTypes]) -> List[int]:
        return [i for i, term_type in enumerate(type_list) if (term_type is DataTypes.free_var_name)]

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
    def _assert_ie_output_properly_typed(ie_input: Iterable, ie_output: Iterable, ie_output_schema: Iterable, ie_relation: IERelation) -> None:
        """
        Even though rgxlog performs typechecking during the semantic checks phase, information extraction functions
        are written by the users and could yield results that are not properly typed.
        this method asserts an information extraction function's output is properly typed.

        @param ie_input: the input of the ie function (used in the exception when the type check fails).
        @param ie_output: an output of the ie function.
        @param ie_output_schema: the expected schema for ie_output.
        @param ie_relation: the ie relation for which the output was computed (will be used to print an exception
            in case the output is not properly typed).
        @raise TypeError: if there is output term of an unsupported type or the output relation is not properly typed.
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
                raise TypeError(f'executing ie relation {ie_relation}\n'
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
            raise TypeError(f'executing ie relation {ie_relation}\n'
                            f'with the input {ie_input}\n'
                            f'failed because one of the outputs had unexpected term types\n'
                            f'the output: {ie_output}\n'
                            f'the output term types: {ie_output_term_types}\n'
                            f'the expected types: {ie_output_schema}')

    @staticmethod
    def _convert_strings_to_spans_in_query_result(query_result: List[Tuple]) -> List[Tuple]:
        """
        convert strings that look like spans into spans
        @param query_result: the list of tuples which may contain strings that should be converted to spans
        @return: the same list, but with span-looking strings converted to `Span` objects
        """
        spanned_query_result = []
        for row in query_result:
            converted_row: List[Union[str, int, Span]] = []
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

    @staticmethod
    def _get_db_filename(database_name: Optional[Any]):
        if database_name:
            if not Path(database_name).is_file():
                raise IOError(f"database file: {database_name} was not found")
            return database_name

        temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=SqliteEngine.DATABASE_SUFFIX)
        temp_db_file.close()
        return temp_db_file.name


if __name__ == "__main__":
    my_engine = SqliteEngine()
    print("hello world")

    # add relation
    my_relation = RelationDeclaration("yoyo", [DataTypes.integer, DataTypes.string])
    my_engine.declare_relation_table(my_relation)

    # add fact
    my_fact = AddFact("yoyo", [8, "hihi"], [DataTypes.integer, DataTypes.string])
    my_engine.add_fact(my_fact)

    my_query = Query("yoyo", ["X", "Y"], [DataTypes.free_var_name, DataTypes.free_var_name])
    print(my_engine.query(my_query))

    print(my_engine.get_table_len("yoyo"))
