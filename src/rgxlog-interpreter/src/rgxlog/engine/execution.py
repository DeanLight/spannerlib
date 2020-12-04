from abc import ABC, abstractmethod
import networkx as nx
from rgxlog.engine.term_graph import EvalState
from pyDatalog import pyDatalog
from rgxlog.engine.datatypes import DataTypes, Span
from rgxlog.engine.symbol_table import SymbolTable
import rgxlog.engine.ie_functions as ie_functions
from rgxlog.engine.ie_functions import IEFunctionData
from rgxlog.engine.named_ast_nodes import *


class DatalogEngineBase(ABC):
    """
    An abstraction for a datalog execution engine
    """

    def __init__(self):
        super().__init__()

    @abstractmethod
    def declare_relation(self, declaration):
        pass

    @abstractmethod
    def add_fact(self, fact):
        pass

    @abstractmethod
    def remove_fact(self, fact):
        pass

    @abstractmethod
    def query(self, query):
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

    @abstractmethod
    def remove_temp_result(self, relation):
        pass


class PydatalogEngine(DatalogEngineBase):
    """
    implementation of a datalog engine using pyDatalog
    """

    def __init__(self, debug=False):
        """
        Args:
            debug: print the commands that are loaded into pyDatalog
        """
        super().__init__()
        self.temp_relations = dict()
        self.new_temp_relation_idx = 0
        self.debug = debug

    def __create_new_temp_relation(self, arity):
        """
        creates a new temporary relation
        Args:
            arity: the temporary relation's arity (needed for declaration)

        Returns: the new temporary relation's name
        """
        temp_relation_name = "__rgxlog__" + str(self.new_temp_relation_idx)
        self.new_temp_relation_idx += 1
        # in pyDatalog there's no typechecking so we can put anything we want in the schema
        declaration = RelationDeclaration(temp_relation_name, [DataTypes.free_var_name] * arity)
        self.declare_relation(declaration)
        return temp_relation_name

    def __extract_temp_relation(self, relations: list) -> Relation:
        """
        creates a new temp relation where each free variable that appears in relations, appears once in the new
        relation.
        for example: for input relation A(X,Y,X), B("b",3,W) we'll get some_temp(X,Y,W)
        """
        temp_relation_terms = []
        for relation in relations:
            for idx, term in enumerate(relation.term_list):
                if relation.type_list[idx] == DataTypes.free_var_name and term not in temp_relation_terms:
                    # if the term is a free variable and is not in the temp relation terms already, add it as a term.
                    temp_relation_terms.append(term)
        temp_relation_types = [DataTypes.free_var_name] * len(temp_relation_terms)
        temp_relation_name = self.__create_new_temp_relation(len(temp_relation_terms))
        return Relation(temp_relation_name, temp_relation_terms, temp_relation_types)

    def declare_relation(self, declaration: RelationDeclaration):
        # add and remove a temporary fact to the relation that is declared, this creates an empty
        # relation in pyDatalog so it is allowed to be queried
        relation_name = declaration.relation_name
        schema_length = len(declaration.type_list)
        temp_fact = relation_name + "("
        for i in range(schema_length):
            temp_fact += "None"
            if i != schema_length - 1:
                temp_fact += ", "
        temp_fact += ")"
        if self.debug:
            print("+" + temp_fact)
            print("-" + temp_fact)
        pyDatalog.load("+" + temp_fact)
        pyDatalog.load("-" + temp_fact)

    def add_fact(self, fact: Relation):
        if self.debug:
            print("+" + fact.get_pydatalog_string())
        pyDatalog.load("+" + fact.get_pydatalog_string())

    def remove_fact(self, fact: Relation):
        if self.debug:
            print("-" + fact.get_pydatalog_string())
        pyDatalog.load("-" + fact.get_pydatalog_string())

    def query(self, query: Relation):
        if self.debug:
            print("print(" + query.get_pydatalog_string() + ")")
        pyDatalog.load("print(" + query.get_pydatalog_string() + ")")

    def add_rule(self, rule_head: Relation, rule_body):
        rule_string = rule_head.get_pydatalog_string() + " <= "
        for idx, rule_body_relation in enumerate(rule_body):
            rule_string += rule_body_relation.get_pydatalog_string()
            if idx < len(rule_body) - 1:
                rule_string += " & "
        if self.debug:
            print(rule_string)
        pyDatalog.load(rule_string)

    def compute_rule_body_relation(self, relation: Relation):
        temp_relation = self.__extract_temp_relation([relation])
        if self.debug:
            print(temp_relation.get_pydatalog_string() + " <= " + relation.get_pydatalog_string())
        pyDatalog.load(temp_relation.get_pydatalog_string() + " <= " + relation.get_pydatalog_string())
        return temp_relation

    def compute_rule_body_ie_relation(self, ie_relation: IERelation, ie_func_data: IEFunctionData,
                                      bounding_relation: Relation):
        input_relation_name = self.__create_new_temp_relation(len(ie_relation.input_term_list))
        output_relation_name = self.__create_new_temp_relation(len(ie_relation.output_term_list))
        input_relation = Relation(input_relation_name, ie_relation.input_term_list, ie_relation.input_type_list)
        output_relation = Relation(output_relation_name, ie_relation.output_term_list, ie_relation.output_type_list)
        if bounding_relation is None:
            # special case where the ie relation is the first rule body relation
            for input_term_type in ie_relation.input_type_list:
                # check if the relation is not bounded, should never happen
                assert input_term_type != DataTypes.free_var_name
            self.add_fact(
                Relation(input_relation.relation_name, ie_relation.input_term_list, ie_relation.input_type_list))
        else:
            # extract the input into an input relation.
            self.add_rule(input_relation, [bounding_relation])
        # get a list of input tuples. to get them we query pyDatalog using the input relation name, and all
        # of the terms will be free variables (so we get the whole tuple)
        query_str = input_relation.relation_name + "("
        for i in range(len(input_relation.term_list)):
            query_str += "X" + str(i)
            if i < len(input_relation.term_list) - 1:
                query_str += ","
        query_str += ")"
        ie_inputs = pyDatalog.ask(query_str).answers
        # get all the outputs
        ie_outputs = []
        for idx, ie_input in enumerate(ie_inputs):
            output = ie_func_data.ie_function(*ie_input)
            ie_outputs.extend(output)
        ie_output_types = tuple(ie_func_data.get_output_types(len(ie_relation.output_term_list)))
        # check output types
        for ie_output in ie_outputs:
            actual_output_types = []
            for value in ie_output:
                if isinstance(value, int):
                    actual_output_types.append(DataTypes.integer)
                elif isinstance(value, str):
                    actual_output_types.append(DataTypes.string)
                elif isinstance(value, tuple) and len(value) == 2:
                    actual_output_types.append(DataTypes.span)
                else:
                    raise Exception("invalid output type")
            if tuple(actual_output_types) != ie_output_types:
                raise Exception("invalid output types")
        # convert spans to a Span type
        for i in range(len(ie_outputs)):
            ie_outputs[i] = list(ie_outputs[i])
            for j in range(len(ie_output_types)):
                if ie_output_types[j] == DataTypes.span:
                    span_tuple = ie_outputs[i][j]
                    assert len(span_tuple) == 2
                    ie_outputs[i][j] = Span(span_tuple[0], span_tuple[1])
        # add the outputs to the output relation
        for ie_output in ie_outputs:
            output_fact = Relation(output_relation.relation_name, ie_output, ie_output_types)
            self.add_fact(output_fact)
        # return the result relation. it's a temp relation that is the inner join of the input and output relations
        return self.aggregate_relations_to_temp_relation([input_relation, output_relation])

    def aggregate_relations_to_temp_relation(self, relations):
        result = self.__extract_temp_relation(relations)
        self.add_rule(result, relations)
        return result

    def remove_temp_result(self, relation: Relation):
        """
        pydatalog saves the rules that we give it and uses them to compute later queries. That means
        we can't delete temporary relations, since we will effectively delete the relations that were computed from
        rules.
        """
        pass


class ExecutionBase(ABC):
    """
    Abstraction for a class that gets a term graph and execute it
    """

    def __init__(self, datalog_engine, symbol_table):
        super().__init__()
        self.datalog_engine = datalog_engine
        self.symbol_table = symbol_table

    @abstractmethod
    def transform(self, term_graph, root_name):
        pass


class NetworkxExecution(ExecutionBase):
    """
    Executes a networkx based term graph
    """

    def __init__(self, datalog_engine: DatalogEngineBase, symbol_table: SymbolTable):
        super().__init__(datalog_engine, symbol_table)

    def transform(self, term_graph: nx.OrderedDiGraph, root_name):
        for node in nx.dfs_postorder_nodes(term_graph, source=root_name):
            if 'state' not in term_graph.nodes[node] or term_graph.nodes[node]['state'] == EvalState.COMPUTED:
                continue
            successors = list(term_graph.successors(node))
            node_type = term_graph.nodes[node]['type']
            if node_type == "relation_declaration":
                self.datalog_engine.declare_relation(term_graph.nodes[node]['value'])
            if node_type == "add_fact":
                self.datalog_engine.add_fact(term_graph.nodes[node]['value'])
            elif node_type == "remove_fact":
                self.datalog_engine.remove_fact(term_graph.nodes[node]['value'])
            elif node_type == "query":
                self.datalog_engine.query(term_graph.nodes[node]['value'])
            if node_type == "rule":
                """
                This rule execution assumes that a previous pass reordered the rule body relations in a way that
                each relation's input free variables (should they exist) are bounded by relations to the relation's
                left. lark_passes.ReorderRuleBodyVisitor is an example for such a pass.

                this implementation computes each rule body relation from left to right, each time aggregating
                all of the free variables (and their values) seen so far.
                Once all of the rule body relations are computed, the aggregated relation is filtered into the
                rule head relation.
                See example at https://github.com/DeanLight/spanner_workbench/issues/23#issuecomment-721704745

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
                rule_head_node = successors[0]
                rule_body_node = successors[1]
                assert term_graph.nodes[rule_head_node]['type'] == 'rule_head'
                assert term_graph.nodes[rule_body_node]['type'] == 'rule_body'
                rule_body_relation_nodes = list(term_graph.successors(rule_body_node))
                temp_result = None
                for relation_node in rule_body_relation_nodes:
                    relation_value = term_graph.nodes[relation_node]['value']
                    if term_graph.nodes[relation_node]['type'] == 'relation':
                        term_graph.nodes[relation_node]['value'] = self.datalog_engine.compute_rule_body_relation(
                            relation_value)
                        term_graph.nodes[relation_node]['state'] = EvalState.COMPUTED
                        if temp_result is None:
                            temp_result = term_graph.nodes[relation_node]['value']
                        else:
                            temp_result = self.datalog_engine.aggregate_relations_to_temp_relation(
                                [temp_result, term_graph.nodes[relation_node]['value']])
                    elif term_graph.nodes[relation_node]['type'] == 'ie_relation':
                        ie_func_data = getattr(ie_functions, relation_value.relation_name)
                        term_graph.nodes[relation_node]['value'] = self.datalog_engine.compute_rule_body_ie_relation(
                            relation_value, ie_func_data, temp_result)
                        if temp_result is not None:
                            temp_result = self.datalog_engine.aggregate_relations_to_temp_relation(
                                [temp_result, term_graph.nodes[relation_node]['value']])
                        else:
                            temp_result = term_graph.nodes[relation_node]['value']
                        term_graph.nodes[relation_node]['state'] = EvalState.COMPUTED
                    else:
                        assert 0
                rule_head_value = term_graph.nodes[rule_head_node]['value']
                rule_head_declaration = RelationDeclaration(rule_head_value.relation_name,
                                                            self.symbol_table.get_relation_schema(
                                                                rule_head_value.relation_name))
                self.datalog_engine.declare_relation(rule_head_declaration)
                self.datalog_engine.add_rule(rule_head_value, [temp_result])
            term_graph.nodes[node]['state'] = EvalState.COMPUTED
