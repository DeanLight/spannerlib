from lark import Transformer, v_args, Tree
from lark.visitors import Interpreter, Visitor_Recursive
import rgxlog.engine.ie_functions as ie_functions
from rgxlog.engine.named_ast_nodes import *
from rgxlog.engine.datatypes import Span


def assert_expected_node_structure(lark_node, node_name=None, num_children=None, children_names=None):
    """
    Asserts that a lark node has the structure that it is expected to have.

    Args:
        lark_node: a node of a lark tree that will be checked
        node_name: the expected name of the node (that should be found in lark_node.data)
        num_children: the expected number of children that the node has
        children_names: a list of the expected children names, in the order that they should appear
        in the lark_node.children list
    """
    if node_name is not None:
        if lark_node.data != node_name:
            raise Exception(f'bad node name: {node_name}\n'
                            f'actual node name: {lark_node.data}')

    if num_children is not None:
        if len(lark_node.children) != num_children:
            raise Exception(f'bad number of children: {str(num_children)}\n'
                            f'actual number of children: {str(len(lark_node.children))}')

    if children_names is not None:
        actual_children_names = [child_node.data for child_node in lark_node.children]
        for name, expected_name in zip(actual_children_names, children_names):
            if name != expected_name:
                raise Exception(f'bad children names: {children_names}\n'
                                f'actual children names: {actual_children_names}')


@v_args(inline=False)
class RemoveTokensTransformer(Transformer):
    """
    transforms the lark tree by removing the redundant tokens.
    should be used before all the other passes as they assume no tokens exists
    """

    def __init__(self, **kw):
        super().__init__(visit_tokens=True)

    @staticmethod
    def INT(args):
        # transform the previous string representation to an integer
        return int(args[0:])

    @staticmethod
    def LOWER_CASE_NAME(args):
        return args[0:]

    @staticmethod
    def UPPER_CASE_NAME(args):
        return args[0:]

    @staticmethod
    def STRING(args):
        # removes the quotation marks
        return args[1:-1]


class CheckReservedRelationNames(Interpreter):
    """
    A lark tree semantic check.
    Checks if there are relations in the program with a name that starts with "__rgxlog__"
    if such relations exist, throw an exception as this is a reserved name for rgxlog.
    """

    def __init__(self, **kw):
        super().__init__()

    @staticmethod
    def relation_name(relation_name_node):
        assert_expected_node_structure(relation_name_node, node_name="relation_name", num_children=1)
        relation_name = relation_name_node.children[0]
        if relation_name.startswith("__rgxlog__"):
            raise Exception(f'encountered relation name: {relation_name}. '
                            f'names starting with __rgxlog__ are reserved')


class StringFixVisitor(Visitor_Recursive):
    """
     Fixes the strings in the lark tree.
     Removes the line overflow escapes from strings
     """

    def __init__(self, **kw):
        super().__init__()

    @staticmethod
    def string(string_node):
        # perform assertion to make sure we got the expected node structure
        assert_expected_node_structure(string_node, node_name='string', num_children=1)

        # get and fix the string that is stored in the node
        cur_string_value = string_node.children[0]
        fixed_string_value = cur_string_value.replace('\\\n', '')

        # replace the string that is stored in the node with the fixed string
        string_node.children[0] = fixed_string_value


class ConvertSpanNodeToSpanDataTypeVisitor(Visitor_Recursive):
    """
    Converts each span node in the ast to a span datatype.
    This means that a span in the tree will be represented by a single value (a "datatypes.Span" instance)
    instead of two integer nodes, making it easier to work with (as other data types are also represented by
    a single value).
    """

    def __init__(self, **kw):
        super().__init__()

    @staticmethod
    def span(span_node):
        # perform assertion to make sure we got the expected node structure
        assert_expected_node_structure(span_node, node_name="span", num_children=2,
                                       children_names=["integer", "integer"])

        # get the span start and end
        span_start = span_node.children[0].children[0]
        span_end = span_node.children[1].children[0]

        # replace the current representation of the span in the ast with a matching Span instance
        span_node.children = [Span(span_start, span_end)]


class ConvertStatementsToNamedNodesVisitor(Visitor_Recursive):
    """
    converts each statement node in the tree to a named node, making it easier to parse in future passes.
    a named node is a namedtuple representation of a a node in the abstract syntax tree.
    note that after using this pass, non statement nodes will no longer appear in the tree, so passes that
    should work on said nodes need to be before this pass in the passes pipeline (e.g. StringFixVisitor)
    """

    def __init__(self, **kw):
        super().__init__()

    @staticmethod
    def __assignment_aux(assignment_node: Tree):
        """
        an utility function that converts an assignment node to a named assignment node

        Args:
            assignment_node: the lark assignment node to be converted to a named assignment node.
        """

        # perform assertions to make sure we got the expected node structure
        assignment_type = assignment_node.data
        assert_expected_node_structure(assignment_node, num_children=2)
        var_name_node = assignment_node.children[0]
        value_node = assignment_node.children[1]
        # since there are multiple types of assigned values, we get the current type using value_node.data
        assert_expected_node_structure(assignment_node, node_name=assignment_type, num_children=2,
                                       children_names=["var_name", value_node.data])
        assert_expected_node_structure(var_name_node, node_name="var_name", num_children=1)
        assert_expected_node_structure(value_node, node_name=value_node.data, num_children=1)

        # get the attributes that defines this assignment: the variable name, the assigned value and the
        # assigned value type
        var_name = var_name_node.children[0]
        value = value_node.children[0]
        value_type = DataTypes.from_string(value_node.data)

        # get a named node that represents this assignment
        if assignment_type == "assignment":
            named_assignment_node = Assignment(var_name, value, value_type)
        elif assignment_type == "read_assignment":
            named_assignment_node = ReadAssignment(var_name, value, value_type)
        else:
            raise Exception(f'received unexpected assignment type: {assignment_type}')

        # replace the current assignment representation with the named node
        assignment_node.children = [named_assignment_node]

    def assignment(self, assignment_node):
        self.__assignment_aux(assignment_node)

    def read_assignment(self, assignment_node):
        self.__assignment_aux(assignment_node)

    @staticmethod
    def __create_named_relation_node(relation_name_node: Tree, term_list_node: Tree):
        """
        an utility function that constructs a named relation node.
        while a relation node isn't a statement in and of itself, it is useful for defining
        a named rule node (which is constructed from multiple relations).
        This is also a useful method for getting the attributes of a relation that defines a fact or a query
        (as facts and queries are actions that are defined by a relation)

        Args:
            relation_name_node: a lark node that contains the name of the relation
            term_list_node: a lark node that contains the term list of the relation

        Returns: a named node that represents the relation
        """

        # make sure that we got the expected nodes
        assert_expected_node_structure(relation_name_node, node_name="relation_name", num_children=1)
        if term_list_node.data not in ['const_term_list', 'term_list', 'free_var_name_list']:
            raise Exception(f'unexpected term list node type: {term_list_node.type}')

        # get the attributes that define a relation: its name, its terms, and the type of its terms
        relation_name = relation_name_node.children[0]
        term_list = [term_node.children[0] for term_node in term_list_node.children]
        type_list = [DataTypes.from_string(term_node.data) for term_node in term_list_node.children]

        # create a named relation node and return it
        named_relation_node = Relation(relation_name, term_list, type_list)
        return named_relation_node

    @staticmethod
    def __create_named_ie_relation_node(relation_name_node: Tree, input_term_list_node: Tree,
                                        output_term_list_node: Tree):
        """
        an utility function that constructs a named ie relation node.
        while an ie relation node isn't a statement in and of itself, it is useful for defining
        a named rule node (which is constructed from multiple relations which may include ie relations).

        Args:
            relation_name_node: a lark node that contains the name of the relation
            input_term_list_node: a lark node that contains the input term list of the relation
            output_term_list_node: a lark node that contains the output term list of the relation

        Returns: a named node that represents the ie relation
        """

        # make sure that we got the expected nodes
        assert_expected_node_structure(relation_name_node, node_name="relation_name", num_children=1)
        assert_expected_node_structure(input_term_list_node, node_name="term_list")
        assert_expected_node_structure(output_term_list_node, node_name="term_list")

        # get the name of the ie relation
        relation_name = relation_name_node.children[0]

        # get the input terms of the ie relation and their types
        input_term_list = [term_node.children[0] for term_node in input_term_list_node.children]
        input_type_list = [DataTypes.from_string(term_node.data) for term_node in input_term_list_node.children]

        # get the output terms of the ie relation and their types
        output_term_list = [term_node.children[0] for term_node in output_term_list_node.children]
        output_type_list = [DataTypes.from_string(term_node.data) for term_node in output_term_list_node.children]

        # create a named ie relation node and return it
        named_ie_relation_node = IERelation(relation_name, input_term_list, input_type_list,
                                            output_term_list, output_type_list)
        return named_ie_relation_node

    def __fact_aux(self, fact_node: Tree):
        """
        an utility function that converts a fact node to a named fact node

        Args:
            fact_node: the lark fact node to be converted
        """

        # perform assertion to make sure we got the expected node structure
        fact_type = fact_node.data
        assert_expected_node_structure(fact_node, node_name=fact_type, num_children=2,
                                       children_names=["relation_name", "const_term_list"])

        # a fact is defined by a relation, create that relation using the utility function
        relation_name_node = fact_node.children[0]
        term_list_node = fact_node.children[1]
        named_relation_node = self.__create_named_relation_node(relation_name_node, term_list_node)

        # create a named node that is fitting for this fact
        if fact_type == "add_fact":
            named_fact_node = AddFact(named_relation_node.relation_name, named_relation_node.term_list,
                                      named_relation_node.type_list)
        elif fact_type == "remove_fact":
            named_fact_node = RemoveFact(named_relation_node.relation_name, named_relation_node.term_list,
                                         named_relation_node.type_list)
        else:
            raise Exception(f'unexpected fact type: {fact_type}')

        # replace the current fact representation with the named fact node
        fact_node.children = [named_fact_node]

    def add_fact(self, fact_node):
        self.__fact_aux(fact_node)

    def remove_fact(self, fact_node):
        self.__fact_aux(fact_node)

    def query(self, query_node):

        # perform assertion to make sure we got the expected node structure
        query_type = query_node.data
        assert_expected_node_structure(query_node, node_name=query_type, num_children=2,
                                       children_names=["relation_name", "term_list"])

        # a query is defined by a relation, create that relation using the utility function
        relation_name_node = query_node.children[0]
        term_list_node = query_node.children[1]
        named_relation_node = self.__create_named_relation_node(relation_name_node, term_list_node)

        # create a named node for the query
        query_named_node = Query(named_relation_node.relation_name, named_relation_node.term_list,
                                 named_relation_node.type_list)

        # replace the current query representation with the named query node
        query_node.children = [query_named_node]

    @staticmethod
    def relation_declaration(relation_decl_node):

        # perform assertion to make sure we got the expected node structure
        assert_expected_node_structure(relation_decl_node, node_name="relation_declaration", num_children=2,
                                       children_names=["relation_name", "decl_term_list"])
        relation_name_node = relation_decl_node.children[0]
        decl_term_list_node = relation_decl_node.children[1]
        assert_expected_node_structure(relation_name_node, node_name="relation_name", num_children=1)
        assert_expected_node_structure(decl_term_list_node, node_name="decl_term_list")

        # get the attributes of the relation declaration: the declared relation name and the types of its terms
        relation_name = relation_name_node.children[0]

        type_list = []
        for decl_term_node in decl_term_list_node.children:
            decl_term_node_type = decl_term_node.data
            if decl_term_node_type == "decl_string":
                type_list.append(DataTypes.string)
            elif decl_term_node_type == "decl_span":
                type_list.append(DataTypes.span)
            elif decl_term_node_type == "decl_int":
                type_list.append(DataTypes.int)
            else:
                raise Exception(f'unexpected declaration term node type: {decl_term_node_type}')

        # create a named node for the relation declaration
        relation_decl_named_node = RelationDeclaration(relation_name, type_list)

        # replace the current relation declaration representation with the named relation declaration node
        relation_decl_node.children = [relation_decl_named_node]

    def rule(self, rule_node):

        # perform assertion to make sure we got the expected node structure
        assert_expected_node_structure(rule_node, node_name="rule", num_children=2,
                                       children_names=["rule_head", "rule_body_relation_list"])
        rule_head_node = rule_node.children[0]
        rule_body_relation_nodes = rule_node.children[1]
        assert_expected_node_structure(rule_head_node, node_name="rule_head", num_children=2,
                                       children_names=["relation_name", "free_var_name_list"])
        assert_expected_node_structure(rule_body_relation_nodes, node_name="rule_body_relation_list")

        # create the named relation node that defines the head of the rule
        head_relation_name_node = rule_head_node.children[0]
        head_relation_terms_node = rule_head_node.children[1]
        named_head_relation_node = self.__create_named_relation_node(
            head_relation_name_node, head_relation_terms_node)

        # create a list of named relation nodes that defines the body of the rule
        named_body_relation_list = []
        for relation_node in rule_body_relation_nodes.children:
            relation_type = relation_node.data

            if relation_type == "relation":
                # this is a normal relation, get it's name and terms and construct a named relation node
                assert_expected_node_structure(relation_node, node_name="relation", num_children=2,
                                               children_names=["relation_name", "term_list"])
                relation_name_node = relation_node.children[0]
                term_list_node = relation_node.children[1]
                named_relation_node = self.__create_named_relation_node(relation_name_node, term_list_node)

            elif relation_type == "ie_relation":
                # this is an ie relation, get it's name, input terms and output term and construct a named ie
                # relation node
                assert_expected_node_structure(relation_node,
                                               node_name="ie_relation", num_children=3,
                                               children_names=["relation_name", "term_list", "term_list"])
                relation_name_node = relation_node.children[0]
                input_term_list_node = relation_node.children[1]
                output_term_list_node = relation_node.children[2]
                named_relation_node = self.__create_named_ie_relation_node(relation_name_node, input_term_list_node,
                                                                           output_term_list_node)

            else:
                raise Exception(f'unexpected relation type: {relation_type}')

            named_body_relation_list.append(named_relation_node)

        # create a list of the types of the relations in the rule body
        body_relation_type_list = [relation_node.data for relation_node in rule_body_relation_nodes.children]

        # create a named rule node
        named_rule_node = Rule(named_head_relation_node, named_body_relation_list, body_relation_type_list)

        # replace the current rule representation with the named rule node
        rule_node.children = [named_rule_node]


class CheckReferencedVariablesInterpreter(Interpreter):
    """
    A lark tree semantic check.
    checks whether each variable reference refers to a defined variable.
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def __check_if_var_is_not_defined(self, var_name):
        if not self.symbol_table.contains_variable(var_name):
            raise Exception(f'variable "{var_name}" is not defined')

    def __check_if_vars_in_list_are_not_defined(self, term_list, type_list):
        for term, term_type in zip(term_list, type_list):
            if term_type is DataTypes.var_name:
                self.__check_if_var_is_not_defined(term)

    def assignment(self, assignment_node):
        assignment = assignment_node.children[0]
        if assignment.value_type == "var_name":
            self.__check_if_var_is_not_defined(assignment.value)

    def read_assignment(self, assignment_node):
        assignment = assignment_node.children[0]
        if assignment.value_type == "var_name":
            self.__check_if_var_is_not_defined(assignment.value)

    def add_fact(self, fact_node):
        fact = fact_node.children[0]
        self.__check_if_vars_in_list_are_not_defined(fact.term_list, fact.type_list)

    def remove_fact(self, fact_node):
        fact = fact_node.children[0]
        self.__check_if_vars_in_list_are_not_defined(fact.term_list, fact.type_list)

    def query(self, query_node):
        query = query_node.children[0]
        self.__check_if_vars_in_list_are_not_defined(query.term_list, query.type_list)

    def rule(self, rule_node):
        rule = rule_node.children[0]
        rule_head = rule.head_relation
        self.__check_if_vars_in_list_are_not_defined(rule_head.term_list, rule_head.type_list)
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            if relation_type == "relation":
                self.__check_if_vars_in_list_are_not_defined(relation.term_list, relation.type_list)
            elif relation_type == "ie_relation":
                self.__check_if_vars_in_list_are_not_defined(relation.input_term_list, relation.input_type_list)
                self.__check_if_vars_in_list_are_not_defined(relation.output_term_list, relation.output_type_list)
            else:
                raise Exception(f'unexpected relation type: {relation_type}')


# class CheckFilesInterpreter(Interpreter):
#     """
#     A lark tree semantic check.
#     checks for existence and access to external documents
#     """
#
#     def __init__(self, **kw):
#         super().__init__()
#         self.symbol_table = kw['symbol_table']
#         self.var_name_to_value = dict()
#
#     def assignment(self, tree):
#         value_node = tree.children[1]
#         value_type = value_node.data
#         assert_expected_node_structure(tree, "assignment", 2, "var_name", value_type)
#         if value_type == "var_name":
#             right_var_name = value_node.children[0]
#             if self.symbol_table.contains_variable(right_var_name):
#                 value = self.symbol_table.get_variable_value(right_var_name)
#             elif right_var_name in self.var_name_to_value:
#                 value = self.var_name_to_value[right_var_name]
#             else:
#                 assert 0
#         else:
#             value = value_node.children[0]
#         left_var_name = tree.children[0].children[0]
#         self.var_name_to_value[left_var_name] = value
#
#     def read_assignment(self, tree):
#         read_param_node = tree.children[1]
#         read_param_type = read_param_node.data
#         assert_expected_node_structure(tree, "read_assignment", 2, "var_name", read_param_type)
#         assert_expected_node_structure(read_param_node, read_param_type, 1)
#         read_param = read_param_node.children[0]
#         if read_param_type == "var_name":
#             if read_param in self.var_name_to_value:
#                 read_param = self.var_name_to_value[read_param]
#             elif self.symbol_table.contains_variable(read_param):
#                 read_param = self.symbol_table.get_variable_value(read_param)
#             else:
#                 assert 0
#         assert_expected_node_structure(tree.children[0], "var_name", 1)
#         left_var_name = tree.children[0].children[0]
#         try:
#             file = open(read_param, 'r')
#             self.var_name_to_value[left_var_name] = file.read()
#             file.close()
#         except Exception:
#             raise Exception("couldn't open file")


class CheckRelationsRedefinitionInterpreter(Interpreter):
    """
    A lark tree semantic check.
    checks if a relation is being redefined, and raises an exception if this is the case.
    relations can be defined either by a relation declaration or by appearing in a rule head
    """
    """
    TODO: in a future version of rgxlog we might want to allow for a rule head to be "redefined", meaning
    a relation could be defined by multiple rule heads, allowing for recursion. 
    This would mean changing this pass as it does not allow a relation to appear in multiple rule heads.
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def __check_if_relation_is_already_defined(self, relation_name):
        """
        an utility function that checks if a relation is already defined and raises an exception
        if it does.

        Args:
            relation_name: the relation name to be checked for redefinition
        """
        if self.symbol_table.contains_relation(relation_name):
            raise Exception(f'relation "{relation_name}" is already defined. relation redefinition is not allowed')

    def relation_declaration(self, relation_decl_node):
        relation_decl = relation_decl_node.children[0]
        self.__check_if_relation_is_already_defined(relation_decl.relation_name)

    def rule(self, rule_node):
        """
        a rule is a definition of the relation that appears in the rule head.
        this function checks that the relation that appears in the rule head is not being redefined.
        """
        rule = rule_node.children[0]
        self.__check_if_relation_is_already_defined(rule.head_relation.relation_name)


class CheckReferencedRelationsExistenceAndArityInterpreter(Interpreter):
    """
    A lark tree semantic check.
    Checks whether each relation (that is not an ie relation) reference refers to a defined relation.
    Also checks if the relation reference uses the correct arity.
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def __check_relation_exists_and_correct_arity(self, relation_name, arity):
        """
        An utility function that checks if a referenced relation exists and if the correct arity was used

        Args:
            relation_name: the relation that was referenced
            arity: the arity that was used.
        """

        # check if the relation exists using the symbol table
        if not self.symbol_table.contains_relation(relation_name):
            raise Exception(f'relation "{relation_name}" is not defined')

        # at this point we know the relation exists but we still need to check that the correct arity was used
        # get the correct arity
        relation_schema = self.symbol_table.get_relation_schema(relation_name)
        correct_arity = len(relation_schema)

        # check if that arity that was used is correct
        if arity != correct_arity:
            raise Exception(f'relation "{relation_name}" was referenced with an incorrect arity: {arity}. The'
                            f'correct arity is: {correct_arity}')

    def query(self, query_node):
        query = query_node.children[0]
        arity = len(query.term_list)
        self.__check_relation_exists_and_correct_arity(query.relation_name, arity)

    def add_fact(self, fact_node):
        fact = fact_node.children[0]
        arity = len(fact.term_list)
        self.__check_relation_exists_and_correct_arity(fact.relation_name, arity)

    def remove_fact(self, fact_node):
        fact = fact_node.children[0]
        arity = len(fact.term_list)
        self.__check_relation_exists_and_correct_arity(fact.relation_name, arity)

    def rule(self, rule_node):
        """
        a rule is a definition of the relation in the rule head. Therefore the rule head reference does not
        need to be checked.
        The rule body references relations that should already exist. Those will be checked in this method.
        """
        rule = rule_node.children[0]
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            if relation_type == "relation":
                arity = len(relation.term_list)
                self.__check_relation_exists_and_correct_arity(relation.relation_name, arity)


class CheckReferencedIERelationsExistenceAndArityVisitor(Visitor_Recursive):
    """
    A lark tree semantic check.
    Checks whether each ie relation reference refers to a defined ie function.
    Also checks if the correct input arity and output arity for the ie function were used.
    """

    def __init__(self, **kw):
        super().__init__()

    @staticmethod
    def rule(rule_node):
        rule = rule_node.children[0]
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            if relation_type == "ie_relation":
                # found an ie relation, check if its ie function exists and if the correct input arity was used

                # get the name of the ie function, it is the same as the name of the ie relation
                ie_func_name = relation.relation_name
                try:
                    # get the data of the ie function
                    ie_function_data = getattr(ie_functions, ie_func_name)
                except Exception:
                    # couldn't find the ie function, raise an exception
                    raise Exception(f'the information extraction function "{ie_func_name}" does not exist')

                # the ie function exists, check if the correct input arity was used
                used_input_arity = len(relation.input_term_list)
                correct_input_arity = len(ie_function_data.get_input_types())
                if used_input_arity != correct_input_arity:
                    raise Exception(f'used incorrect input arity for ie function "{ie_func_name}":'
                                    f' {used_input_arity} (should be {correct_input_arity})')

                # check if the correct output arity was used
                used_output_arity = len(relation.output_term_list)
                correct_output_arity = len(ie_function_data.get_output_types(used_output_arity))
                if used_output_arity != correct_output_arity:
                    raise Exception(f'used incorrect output arity for ie function {ie_func_name}:'
                                    f' {used_output_arity} (should be {correct_output_arity})')


class CheckRuleSafetyVisitor(Visitor_Recursive):
    """
    A lark tree semantic check.
    checks whether the rules in the programs are safe.

    For a rule to be safe, two conditions must apply:

    1. Every free variable in the head occurs at least once in the body as an output term of a relation.

    examples:
    a. "parent(X,Y) <- son(X)" is not a safe rule because the free variable Y only appears in the rule head.
    b. "parent(X,Z) <- parent(X,Y), parent(Y,Z)" is a safe rule as both X,Z that appear in the rule head, also
        appear in the rule body.
    c. "happy(X) <- is_happy<X>(Y)" is not a safe rule as X does not appear as an output of a relation.

    2. Every free variable is bound.
    A bound free variable is a free variable that has a constraint that imposes a
    limit on the amount of values it can take.

    In order to check that every free variable is bound, we will check that every relation in the rule body
    is a safe relation, meaning:
    a. A safe relation is one where its input relation is safe,
    meaning all its input's free variables are bound.
    b. A bound variable is one that exists in the output of a safe relation.

    examples:
    a. "rel2(X,Y) <- rel1(X,Z),ie1<X>(Y)" is safe as the only input free variable, X, exists in the output of
    the safe relation rel1(X,Z).
    b. " rel2(Y) <- ie1<Z>(Y)" is not safe as the input free variable Z does not exist in the output of any
    safe relation.
    """

    def __init__(self, **kw):
        super().__init__()

    @staticmethod
    def __get_set_of_free_var_names(term_list, type_list):
        """
        Args:
            term_list: a list of terms
            type_list: a list of the term types

        Returns: a set of all the free variable names in term_list
        """
        free_var_names = set(term for term, term_type in zip(term_list, type_list)
                             if term_type is DataTypes.free_var_name)
        return free_var_names

    def __get_set_of_input_free_var_names(self, relation, relation_type):
        """
        Args:
            relation: a relation (either a normal relation or an ie relation)
            relation_type: the type of the relation

        Returns: a set of the free variable input terms of the relation
        """
        if relation_type == "relation":
            # normal relations don't have input terms, return an empty set
            return set()
        elif relation_type == "ie_relation":
            # return a set of the free variables in the input term list
            return self.__get_set_of_free_var_names(relation.input_term_list, relation.input_type_list)
        else:
            raise Exception(f'unexpected relation type: {relation_type}')

    def __get_set_of_output_free_var_names(self, relation, relation_type):
        """
        Args:
            relation: a relation (either a normal relation or an ie relation)
            relation_type: the type of the relation

        Returns: a set of the free variable output terms of the relation
        """
        if relation_type == "relation":
            # the term list of a normal relation serves as the output term list, return its free variables
            return self.__get_set_of_free_var_names(relation.term_list, relation.type_list)
        elif relation_type == "ie_relation":
            # return a set of the free variables in the output term list
            return self.__get_set_of_free_var_names(relation.output_term_list, relation.output_type_list)
        else:
            raise Exception(f'unexpected relation type: {relation_type}')

    def rule(self, rule_node):
        rule = rule_node.children[0]

        # check condition 1:
        # every free variable in the head occurs at least once in the body as an output term of a relation.

        # get the free variables in the rule head
        head_relation_term_list = rule.head_relation.term_list
        head_relation_type_list = rule.head_relation.type_list
        rule_head_free_vars = self.__get_set_of_free_var_names(head_relation_term_list, head_relation_type_list)

        # get the free variables in the rule body that serve as output terms.
        rule_body_output_free_var_sets = [self.__get_set_of_output_free_var_names(relation, relation_type)
                                          for relation, relation_type in
                                          zip(rule.body_relation_list, rule.body_relation_type_list)]
        rule_body_output_free_vars = set().union(*rule_body_output_free_var_sets)

        # make sure that every free var in the rule head appears at least once in the rule body
        invalid_free_var_names = rule_head_free_vars.difference(rule_body_output_free_vars)
        if invalid_free_var_names:
            raise Exception(f'The rule "{rule}" \n'
                            f'is not safe because the following free variables appear in the '
                            'rule head but not as output terms in the rule body:\n'
                            f'{invalid_free_var_names}')

        # check condition 2:
        # every free variable is bound.
        # we will do this by checking that all of the rule body relations are safe.

        # use a fix point iteration algorithm to find if all the relations are safe:
        # a. iterate over all of the rule body relations and check if they are safe, meaning all their input
        # free variable terms are bound.
        # b. if a new safe relation was found, mark its output free variables as bound, and the relation as safe.
        # c. repeat step 'a' until all relations were found to be safe relations,
        # or no new safe relations were found.

        # initialize assuming every relation is unsafe and every free variable is unbound
        safe_relations = set()
        bound_free_vars = set()
        found_new_safe_relation = False
        all_relations_are_safe = False
        first_pass = True

        while first_pass or (found_new_safe_relation and not all_relations_are_safe):
            first_pass = False
            found_new_safe_relation = False

            # try to find new safe relations
            for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
                if relation not in safe_relations:
                    # this relation was not marked as safe yet.
                    # check if all of its input free variable terms are bound
                    input_free_vars = self.__get_set_of_input_free_var_names(relation, relation_type)
                    unbound_input_free_vars = input_free_vars.difference(bound_free_vars)
                    if not unbound_input_free_vars:
                        # all input free variables are bound, mark the relation as safe
                        safe_relations.add(relation)
                        # mark the relation's output free variables as bound
                        output_free_vars = self.__get_set_of_output_free_var_names(relation, relation_type)
                        bound_free_vars = bound_free_vars.union(output_free_vars)
                        # make sure we iterate over the relations again if not all of them were found
                        # to be safe
                        found_new_safe_relation = True
            # the pass was completed, check if all of the relations were found to be safe
            all_relations_are_safe = len(safe_relations) == len(rule.body_relation_list)

        if not all_relations_are_safe:
            # condition 2 check failed, get all of the unbound free variables and pass them in an exception
            rule_body_input_free_var_sets = [self.__get_set_of_input_free_var_names(relation, relation_type)
                                             for relation, relation_type in
                                             zip(rule.body_relation_list, rule.body_relation_type_list)]
            rule_body_input_free_vars = set().union(*rule_body_input_free_var_sets)
            unbound_free_vars = rule_body_input_free_vars.difference(bound_free_vars)
            raise Exception(f'The rule "{rule}" \n'
                            f'is not safe because the following free variables are not bound:\n'
                            f'{unbound_free_vars}')


class ReorderRuleBodyVisitor(Visitor_Recursive):
    """
    A lark optimization pass.
    Reorders each rule body relations list so that each relation in the list has its input free variables bound by
    previous relations in the list, or it has no input free variables terms.
    for example: the rule "B(Z) <- RGX(X,Y)->(Z), A(X), A(Y)"
           will change to "B(Z) <- A(X), A(Y), RGX(X,Y)->(Z)"
    This way it is possible to easily compute the rule body relations from the start of the list to its end.
    for more details on the execution of rules see execution.NetworkxExecution
    """

    def __init__(self, **kw):
        super().__init__()

    @staticmethod
    def __get_set_of_free_var_names(term_list, type_list):
        """
        Args:
            term_list: a list of terms
            type_list: a list of the term types

        Returns: a set of all the free variable names in term_list
        """
        free_var_names = set(term for term, term_type in zip(term_list, type_list)
                             if term_type is DataTypes.free_var_name)
        return free_var_names

    def __get_set_of_input_free_var_names(self, relation, relation_type):
        """
        Args:
            relation: a relation (either a normal relation or an ie relation)
            relation_type: the type of the relation

        Returns: a set of the free variable input terms of the relation
        """
        if relation_type == "relation":
            # normal relations don't have input terms, return an empty set
            return set()
        elif relation_type == "ie_relation":
            # return a set of the free variables in the input term list
            return self.__get_set_of_free_var_names(relation.input_term_list, relation.input_type_list)
        else:
            raise Exception(f'unexpected relation type: {relation_type}')

    def __get_set_of_output_free_var_names(self, relation, relation_type):
        """
        Args:
            relation: a relation (either a normal relation or an ie relation)
            relation_type: the type of the relation

        Returns: a set of the free variable output terms of the relation
        """
        if relation_type == "relation":
            # the term list of a normal relation serves as the output term list, return its free variables
            return self.__get_set_of_free_var_names(relation.term_list, relation.type_list)
        elif relation_type == "ie_relation":
            # return a set of the free variables in the output term list
            return self.__get_set_of_free_var_names(relation.output_term_list, relation.output_type_list)
        else:
            raise Exception(f'unexpected relation type: {relation_type}')

    def rule(self, rule_node):
        rule = rule_node.children[0]

        # in order to reorder the relations, we will use the same algorithm from the CheckRuleSafetyVisitor pass.
        # when a safe relation is found, it will be inserted into a list. This way, an order in which each
        # relation's input free variables are bound by previous relations in the list is found.

        # use a fix point iteration algorithm to find a correct order:
        # a. iterate over all of the rule body relations and check if they are safe, meaning all their input
        # free variable terms are bound by the current relations in the reordered list
        # (or they have no input free variables).
        # b. if a new safe relation was found, mark its output free variables as bound, and add the relation to the list
        # c. repeat step 'a' until all relations were found to be safe relations,
        # or no new safe relations were found.
        # d. replace the original rule body relations list with the reordered list

        # initialize assuming every relation is unsafe and every free variable is unbound
        reordered_relations_list = []
        reordered_relations_type_list = []  # note that this we also need to update the type list of the relations
        bound_free_vars = set()
        found_new_safe_relation = False
        all_relations_were_reordered = False
        first_pass = True

        while first_pass or (found_new_safe_relation and not all_relations_were_reordered):
            first_pass = False
            found_new_safe_relation = False

            # try to find new safe relations
            for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
                if relation not in reordered_relations_list:
                    # this relation was not marked as safe yet.
                    # check if all of its input free variable terms are bound
                    input_free_vars = self.__get_set_of_input_free_var_names(relation, relation_type)
                    unbound_input_free_vars = input_free_vars.difference(bound_free_vars)
                    if not unbound_input_free_vars:
                        # all input free variables are bound, mark the relation as safe by adding it to the reordered
                        # list. also save its type.
                        reordered_relations_list.append(relation)
                        reordered_relations_type_list.append(relation_type)
                        # mark the relation's output free variables as bound
                        output_free_vars = self.__get_set_of_output_free_var_names(relation, relation_type)
                        bound_free_vars = bound_free_vars.union(output_free_vars)
                        # make sure we iterate over the relations again if not all of them were found
                        # to be safe
                        found_new_safe_relation = True
            # the pass was completed, check if all of the relations were found to be safe (and thus were reordered)
            all_relations_were_reordered = len(reordered_relations_list) == len(rule.body_relation_list)

        if not all_relations_were_reordered:
            raise Exception(f'The rule "{rule}"\n'
                            f'is not safe. This pass assumes its input rule is safe, '
                            f'so make sure to check for rule safety before using it')

        # replace the current relation list with the reordered relation list
        rule.body_relation_list = reordered_relations_list
        rule.body_relation_type_list = reordered_relations_type_list


class TypeCheckingInterpreter(Interpreter):
    """
    A lark tree semantic check.
    This pass makes the following assumptions and might not work correctly if they are not met
    1. that relations and ie relations references and correct arity were checked.
    2. variable references were checked.
    3. it only gets a single statement as an input.

    this pass performs the following checks:
    1. checks if relation references are properly typed.
    2. checks if ie relations are properly typed.
    3. checks if free variables in rules do have conflicting types.

    example for the semantic check failing on check no. 3:
    new A(str)
    new B(int)
    C(X) <- A(X), B(X) # error since X is expected to be both an int and a string
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def __type_check_term_list(self, term_list: list, type_list: list, correct_type_list: list):
        """
        check if the term list is properly typed.
        the term list could include free variables, this method will assume their actual type is correct.
        Args:
            term_list: the term list to be type checked
            type_list: the types of the terms in term_list
            correct_type_list: a list of the types that the terms must have to pass the type check

        Returns: True if the type check passed, else False
        """
        if len(term_list) != len(type_list) or len(term_list) != len(correct_type_list):
            raise Exception("the length of term_list, type_list and correct_type_list should be the same")

        # perform the type check
        for term, term_type, correct_type in zip(term_list, type_list, correct_type_list):
            if term_type is DataTypes.var_name:
                # current term is a variable, get its type from the symbol table and check if it is correct
                var_type = self.symbol_table.get_variable_type(term)
                if var_type != correct_type:
                    # the variable is not properly typed, the type check failed
                    return False
            elif term_type is not DataTypes.free_var_name and term_type != correct_type:
                # the term is a literal that is not properly typed, the type check failed
                return False
        # all variables are properly typed, the type check succeeded
        return True

    def relation_declaration(self, relation_decl_node):
        relation_decl = relation_decl_node.children[0]
        self.symbol_table.set_relation_schema(relation_decl.relation_name, relation_decl.type_list)

    def add_fact(self, fact_node):
        fact = fact_node.children[0]
        # get the schema of the referenced relation from the symbol table and perform a type check
        relation_schema = self.symbol_table.get_relation_schema(fact.relation_name)
        type_check_passed = self.__type_check_term_list(fact.term_list, fact.type_list, relation_schema)
        if not type_check_passed:
            raise Exception(f'type check failed for fact: "{fact}"')

    def remove_fact(self, fact_node):
        fact = fact_node.children[0]
        # get the schema of the referenced relation from the symbol table and perform a type check
        relation_schema = self.symbol_table.get_relation_schema(fact.relation_name)
        type_check_passed = self.__type_check_term_list(fact.term_list, fact.type_list, relation_schema)
        if not type_check_passed:
            raise Exception(f'type check failed for fact: "{fact}"')

    def query(self, query_node):
        query = query_node.children[0]
        # get the schema of the referenced relation from the symbol table and perform a type check
        relation_schema = self.symbol_table.get_relation_schema(query.relation_name)
        type_check_passed = self.__type_check_term_list(query.term_list, query.type_list, relation_schema)
        if not type_check_passed:
            raise Exception(f'type check failed for query: "{query}"')

    @staticmethod
    def __rule_free_vars_type_check_aux(term_list: list, type_list: list, correct_type_list: list,
                                        free_var_to_type: dict, conflicted_free_vars: set):
        """
        free variables in rules get their type from the relations in the rule body.
        it is possible for a free variable to be expected to be more than one type.
        for each free variable in term_list, this method will check for it's type, save it in
        free_var_to_type (for future calls), and check if it is expected to be more than one type.

        Args:
            term_list: the term list of a rule body relation
            type_list: the types of the terms in term_list
            correct_type_list: a list of the types that the terms in the term list should have
            free_var_to_type: a mapping of free variables to their type (those that are currently known)
            this function updates this mapping if it finds new free variables in term_list
            conflicted_free_vars: a set of the free variables that are found to have conflicting types
            this function adds conflicting free variables that it finds to this set
        """
        if len(term_list) != len(type_list) or len(term_list) != len(correct_type_list):
            raise Exception("the length of term_list, type_list and correct_type_list should be the same")

        for term, term_type, correct_type in zip(term_list, type_list, correct_type_list):
            if term_type is DataTypes.free_var_name:
                # found a free variable, check for conflicting types
                free_var = term
                if free_var in free_var_to_type:
                    # free var already has a type, make sure there's no conflict with the expected type.
                    free_var_type = free_var_to_type[free_var]
                    if free_var_type != correct_type:
                        # found a conflicted free var
                        conflicted_free_vars.add(free_var)
                else:
                    # free var does not currently have a type, map it to the expected type
                    free_var_to_type[free_var] = correct_type

    def rule(self, rule_node):
        rule = rule_node.children[0]

        free_var_to_type = dict()
        conflicted_free_vars = set()

        # Look for conflicting free variables and improperly typed relations
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):

            if relation_type == "relation":
                # perform the type check
                relation_schema = self.symbol_table.get_relation_schema(relation.relation_name)
                type_check_passed = self.__type_check_term_list(
                    relation.term_list, relation.type_list, relation_schema)
                # check for conflicted free variables
                self.__rule_free_vars_type_check_aux(
                    relation.term_list, relation.type_list, relation_schema, free_var_to_type, conflicted_free_vars)

            elif relation_type == "ie_relation":
                # get the input and output schema of the ie function
                ie_func_name = relation.relation_name
                ie_func_data = getattr(ie_functions, ie_func_name)
                input_schema = ie_func_data.get_input_types()
                output_arity = len(relation.output_term_list)
                output_schema = ie_func_data.get_output_types(output_arity)
                # perform the type check
                input_type_check_passed = self.__type_check_term_list(
                    relation.input_term_list, relation.input_type_list, input_schema)
                output_type_check_passed = self.__type_check_term_list(
                    relation.output_term_list, relation.output_type_list, output_schema)
                type_check_passed = input_type_check_passed and output_type_check_passed
                # check for conflicting free variables
                self.__rule_free_vars_type_check_aux(relation.input_term_list, relation.input_type_list,
                                                     input_schema, free_var_to_type, conflicted_free_vars)
                self.__rule_free_vars_type_check_aux(relation.output_term_list, relation.output_type_list,
                                                     output_schema, free_var_to_type, conflicted_free_vars)

            else:
                raise Exception(f'unexpected relation type: {relation_type}')

            # raise an exception if the type check failed
            if not type_check_passed:
                raise Exception(f'type check failed for rule "{rule}"\n'
                                f'because the relation "{relation}"\n'
                                f'is not properly typed')

        # raise an exception if there are any free variables with conflicting types
        if conflicted_free_vars:
            raise Exception(f'type check failed for rule "{rule}"\n'
                            f'because the following free variables have conflicting types:\n'
                            f'{conflicted_free_vars}')

        # no issues were found, get the relation's head schema using the free variable to type mapping
        # and add it to the symbol table
        head_relation = rule.head_relation
        rule_head_schema = [free_var_to_type[term] for term in head_relation.term_list]
        self.symbol_table.set_relation_schema(head_relation.relation_name, rule_head_schema)


class ResolveVariablesInterpreter(Interpreter):
    """
    a lark execution pass
    This pass performs the variable assignments and replaces variable references with their literal values.
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def assignment(self, assignment_node):
        assignment = assignment_node.children[0]

        # get the assigned value and type
        if assignment.value_type is DataTypes.var_name:
            # the assigned value is a variable, get its value and type using the symbol table.
            assigned_var_name = assignment.value
            assigned_value = self.symbol_table.get_variable_value(assigned_var_name)
            assigned_type = self.symbol_table.get_variable_type(assigned_var_name)
        else:
            # the assigned value is a literal, get its value and type
            # (they already exist in the assignment named node)
            assigned_value = assignment.value
            assigned_type = assignment.value_type

        # perform the assignment by saving the variable attributes in the symbol table
        self.symbol_table.set_variable_value_and_type(assignment.var_name, assigned_value, assigned_type)

    def read_assignment(self, assignment_node):
        assignment = assignment_node.children[0]

        # get the argument for the read() function
        if assignment.value_type is DataTypes.var_name:
            # the argument is a variable, get its literal value
            read_arg_var_name = assignment.value
            read_arg = self.symbol_table.get_variable_value(read_arg_var_name)
        else:
            # the argument is a literal string, get it from the assignment node
            read_arg = assignment.value

        # try to read the file and get its content as a single string. this string is the assigned value.
        try:
            file = open(read_arg, 'r')
            assigned_value = file.read()
            file.close()
        except Exception:
            raise Exception(f'could not open file "{read_arg}"')

        # perform the assignment by saving the variable attributes in the symbol table
        # note that since this is a read assignment, the type of the variable will always be a string
        self.symbol_table.set_variable_value_and_type(assignment.var_name, assigned_value, DataTypes.string)

    def __get_term_list_with_resolved_var_values(self, term_list, type_list):
        # TODO
        resolved_var_values_term_list = [
            self.symbol_table.get_variable_value(term) if term_type is DataTypes.var_name
            else term
            for term, term_type in zip(term_list, type_list)]
        return resolved_var_values_term_list

    def __get_type_list_with_resolved_var_types(self, term_list, type_list):
        # TODO
        resolved_var_types_type_list = [
            self.symbol_table.get_variable_type(term) if term_type is DataTypes.var_name
            else term_type
            for term, term_type in zip(term_list, type_list)]
        return resolved_var_types_type_list

    def resolve_var_terms_in_relation(self, relation: Relation):
        # TODO commenting

        term_list = relation.term_list
        type_list = relation.type_list

        relation.term_list = self.__get_term_list_with_resolved_var_values(term_list, type_list)
        relation.type_list = self.__get_type_list_with_resolved_var_types(term_list, type_list)

    def resolve_var_terms_in_ie_relation(self, relation: IERelation):
        # TODO commenting

        input_term_list = relation.input_term_list
        input_type_list = relation.input_type_list

        relation.input_term_list = self.__get_term_list_with_resolved_var_values(input_term_list, input_type_list)
        relation.input_type_list = self.__get_type_list_with_resolved_var_types(input_term_list, input_type_list)

        output_term_list = relation.output_term_list
        output_type_list = relation.output_type_list

        relation.output_term_list = self.__get_term_list_with_resolved_var_values(output_term_list, output_type_list)
        relation.output_type_list = self.__get_type_list_with_resolved_var_types(output_term_list, output_type_list)

    def query(self, query_node):
        query = query_node.children[0]
        self.resolve_var_terms_in_relation(query)

    def add_fact(self, fact_node):
        fact = fact_node.children[0]
        self.resolve_var_terms_in_relation(fact)

    def remove_fact(self, fact_node):
        fact = fact_node.children[0]
        self.resolve_var_terms_in_relation(fact)

    def rule(self, rule_node):
        rule = rule_node.children[0]

        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            if relation_type == "relation":
                self.resolve_var_terms_in_relation(relation)
            elif relation_type == "ie_relation":
                self.resolve_var_terms_in_ie_relation(relation)
            else:
                raise Exception(f'unexpected relation type: {relation_type}')


class AddStatementsToNetxTermGraphInterpreter(Interpreter):
    """
    a lark execution pass.
    This pass adds each statement in the input parse tree to the term graph.
    This pass is made to work with execution.NetworkxExecution as the execution engine and
    term_graph.NetxTermGraph as the term graph.

    Each statement in the term graph will be a child of the term graph's root.

    each statement in the term graph will have a type attribute that contains the statement's name in the
    rgxlog grammar.

    some nodes in the term graph will contain a value attribute that would describe that statement.
    e.g. a add_fact node would have a value which is a Relation instance that describes the
    fact that will be added.

    Some statements are more complex and will be described by more than a single node, e.g. a rule node.
    The reason for this is that we want a single netx node to not contain more than one Relation
    (or IERelation) instance. This will make the term graph a "graph of relation nodes", allowing
     for flexibility for optimization in the future.
    """

    def __init__(self, **kw):
        super().__init__()
        self.term_graph = kw['term_graph']

    def __add_statement_to_term_graph(self, statement_type, statement_value):
        """
        An utility function that adds a statement to the term graph, meaning it adds a node that
        represents the statement to the term graph, then attach the node to the term graph's root.
        Should only be used for simple statements (i.e. can be described by a single node)

        Args:
            statement_type: the type of the statement, (e.g. add_fact). should be the same as the statement's
            name in the grammar. Will be set as the node's type attribute.
            statement_value: will be set as the value attribute of the node.
        """
        new_statement_node = self.term_graph.add_term(type=statement_type, value=statement_value)
        self.term_graph.add_dependency(self.term_graph.get_root(), new_statement_node)

    def add_fact(self, fact_node):
        fact = fact_node.children[0]
        # add the fact to the term graph
        self.__add_statement_to_term_graph("add_fact", fact)

    def remove_fact(self, fact_node):
        fact = fact_node.children[0]
        # add the fact to the term graph
        self.__add_statement_to_term_graph("remove_fact", fact)

    def query(self, query_node):
        query = query_node.children[0]
        # add the query to the term graph
        self.__add_statement_to_term_graph("query", query)

    def relation_declaration(self, relation_decl_node):
        relation_decl = relation_decl_node.children[0]
        # add the relation declaration to the term graph
        self.__add_statement_to_term_graph("relation_declaration", relation_decl)

    def rule(self, rule_node):
        rule = rule_node.children[0]

        # create the root of the rule statement in the term graph. Note that this is an "empty" node (it does
        # not contain a value). This is because the rule statement will be defined by the children of this node.
        tg_rule_node = self.term_graph.add_term(type="rule")
        # attach the rule node to the term graph root
        self.term_graph.add_dependency(self.term_graph.get_root(), tg_rule_node)

        # create the rule head node for the term graph.
        # since a rule head is defined by a single relation, this node will contain a value which is that relation.
        tg_head_relation_node = self.term_graph.add_term(type="rule_head", value=rule.head_relation)
        # attach the rule head node to the rule statement node
        self.term_graph.add_dependency(tg_rule_node, tg_head_relation_node)

        # create the rule body node. Unlike the rule head node, we can't define the rule body node
        # with a single value since a rule body can be defined by multiple relations.
        # Instead, each of the rule body relations will be represented by a term graph node
        # that is a child of the rule body node.
        tg_rule_body_node = self.term_graph.add_term(type="rule_body")
        # attach the rule body node to the rule statement node
        self.term_graph.add_dependency(tg_rule_node, tg_rule_body_node)

        # add each rule body relation to the graph as a child node of the rule body node.
        for relation, relation_type in zip(rule.body_relation_list, rule.body_relation_type_list):
            # add the relation to the term graph
            tg_body_relation_node = self.term_graph.add_term(type=relation_type, value=relation)
            # attach the relation to the rule body
            self.term_graph.add_dependency(tg_rule_body_node, tg_body_relation_node)
