from lark import Transformer, v_args, Tree
from lark.visitors import Interpreter, Visitor_Recursive
from rgxlog.engine.datatypes import DataTypes
import rgxlog.engine.ie_functions as ie_functions
from rgxlog.engine.named_ast_nodes import *
from rgxlog.engine.datatypes import Span

NODES_OF_LIST_WITH_VAR_NAMES = {"term_list", "const_term_list"}
NODES_OF_LIST_WITH_RELATION_NODES = {"rule_body_relation_list"}
NODES_OF_LIST_WITH_FREE_VAR_NAMES = {"term_list", "free_var_name_list"}
NODES_OF_TERM_LISTS = {"term_list", "const_term_list"}
NODES_OF_RULE_BODY_TERM_LISTS = {"term_list"}
SCHEMA_DEFINING_NODES = {"decl_term_list", "free_var_name_list"}


# TODO fix the calls that we have to use only kwargs once the rewrite is done
def assert_expected_node_structure(node, node_name=None, num_children=None, *children_names):
    if node_name is not None:
        assert node.data == node_name, "bad node name: " + node_name + \
                                       "\n actual node name: " + node.data
    if num_children is not None:
        assert len(node.children) == num_children, "bad number of children: " + str(num_children) + \
                                                   "\n actual number of children: " + str(len(node.children))
    if children_names is not None:
        for idx, name in enumerate(children_names):
            assert node.children[idx].data == name, "bad child name at index " + str(idx) + ": " + \
                                                    name + \
                                                    "\n actual child name: " + node.children[idx].data


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
        assert_expected_node_structure(span_node, "span", 2, "integer", "integer")

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
        assert_expected_node_structure(assignment_node, assignment_type, 2, "var_name", value_node.data)
        assert_expected_node_structure(var_name_node, node_name="var_name", num_children=1)
        assert_expected_node_structure(value_node, node_name=value_node.data, num_children=1)

        # get the attributes that defines this assignment: the variable name, the assigned value and the
        # assigned value type
        var_name = var_name_node.children[0]
        value = value_node.children[0]
        value_type = DataTypes.from_string(value_node.data)

        # get a named node that represents this assignment
        if assignment_type == "assignment":
            named_assignment_node = AssignmentNode(var_name, value, value_type)
        elif assignment_type == "read_assignment":
            named_assignment_node = ReadAssignmentNode(var_name, value, value_type)
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
        named_relation_node = RelationNode(relation_name, term_list, type_list)
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
        named_ie_relation_node = IERelationNode(relation_name, input_term_list, input_type_list,
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
        assert_expected_node_structure(fact_node, fact_type, 2, "relation_name", "const_term_list")

        # a fact is defined by a relation, create that relation using the utility function
        relation_name_node = fact_node.children[0]
        term_list_node = fact_node.children[1]
        named_relation_node = self.__create_named_relation_node(relation_name_node, term_list_node)

        # create a named node that is fitting for this fact
        if fact_type == "add_fact":
            named_fact_node = AddFactNode(named_relation_node.relation_name, named_relation_node.term_list,
                                          named_relation_node.type_list)
        elif fact_type == "remove_fact":
            named_fact_node = RemoveFactNode(named_relation_node.relation_name, named_relation_node.term_list,
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
        assert_expected_node_structure(query_node, query_type, 2, "relation_name", "term_list")

        # a query is defined by a relation, create that relation using the utility function
        relation_name_node = query_node.children[0]
        term_list_node = query_node.children[1]
        named_relation_node = self.__create_named_relation_node(relation_name_node, term_list_node)

        # create a named node for the query
        query_named_node = QueryNode(named_relation_node.relation_name, named_relation_node.term_list,
                                     named_relation_node.type_list)

        # replace the current query representation with the named query node
        query_node.children = [query_named_node]

    @staticmethod
    def relation_declaration(relation_decl_node):

        # perform assertion to make sure we got the expected node structure
        assert_expected_node_structure(relation_decl_node, "relation_declaration", 2, "relation_name",
                                       "decl_term_list")
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
        relation_decl_named_node = RelationDeclarationNode(relation_name, type_list)

        # replace the current relation declaration representation with the named relation declaration node
        relation_decl_node.children = [relation_decl_named_node]

    def rule(self, rule_node):

        # perform assertion to make sure we got the expected node structure
        assert_expected_node_structure(rule_node, "rule", 2, "rule_head", "rule_body_relation_list")
        rule_head_node = rule_node.children[0]
        rule_body_relation_nodes = rule_node.children[1]
        assert_expected_node_structure(rule_head_node, "rule_head", 2, "relation_name", "free_var_name_list")
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
                assert_expected_node_structure(relation_node, "relation", 2, "relation_name", "term_list")
                relation_name_node = relation_node.children[0]
                term_list_node = relation_node.children[1]
                named_relation_node = self.__create_named_relation_node(relation_name_node, term_list_node)

            elif relation_type == "ie_relation":
                # this is an ie relation, get it's name, input terms and output term and construct a named ie
                # relation node
                assert_expected_node_structure(relation_node,
                                               "ie_relation", 3, "relation_name", "term_list", "term_list")
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
        named_rule_node = RuleNode(named_head_relation_node, named_body_relation_list, body_relation_type_list)

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


class CheckFilesInterpreter(Interpreter):
    """
    A lark tree semantic check.
    checks for existence and access to external documents
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']
        self.var_name_to_value = dict()

    def assignment(self, tree):
        value_node = tree.children[1]
        value_type = value_node.data
        assert_expected_node_structure(tree, "assignment", 2, "var_name", value_type)
        if value_type == "var_name":
            right_var_name = value_node.children[0]
            if self.symbol_table.contains_variable(right_var_name):
                value = self.symbol_table.get_variable_value(right_var_name)
            elif right_var_name in self.var_name_to_value:
                value = self.var_name_to_value[right_var_name]
            else:
                assert 0
        else:
            value = value_node.children[0]
        left_var_name = tree.children[0].children[0]
        self.var_name_to_value[left_var_name] = value

    def read_assignment(self, tree):
        read_param_node = tree.children[1]
        read_param_type = read_param_node.data
        assert_expected_node_structure(tree, "read_assignment", 2, "var_name", read_param_type)
        assert_expected_node_structure(read_param_node, read_param_type, 1)
        read_param = read_param_node.children[0]
        if read_param_type == "var_name":
            if read_param in self.var_name_to_value:
                read_param = self.var_name_to_value[read_param]
            elif self.symbol_table.contains_variable(read_param):
                read_param = self.symbol_table.get_variable_value(read_param)
            else:
                assert 0
        assert_expected_node_structure(tree.children[0], "var_name", 1)
        left_var_name = tree.children[0].children[0]
        try:
            file = open(read_param, 'r')
            self.var_name_to_value[left_var_name] = file.read()
            file.close()
        except Exception:
            raise Exception("couldn't open file")


class CheckRelationsRedefinitionInterpreter(Interpreter):
    """
    A lark tree semantic check.
    checks if a relation is being redefined, and raises an exception if this is the case.
    relations can be defined either by a relation declaration or by rules
    """
    """
    TODO: in a future version of rgxlog we might want to allow for a rule head to be "redefined", meaning
    a relation could be defined by multiple rule heads. This would mean changing this pass as it does
    not allow for this.
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
                self.__check_relation_exists_and_correct_arity(relation.name, arity)


class CheckReferencedIERelationsVisitor(Visitor_Recursive):
    """
    A lark tree semantic check.
    checks whether each ie relation reference refers to a defined ie function.
    """

    def __init__(self, **kw):
        super().__init__()

    @staticmethod
    def ie_relation(tree):
        assert_expected_node_structure(tree, "ie_relation", 3, "relation_name", "term_list", "term_list")
        ie_func_name = tree.children[0].children[0]
        ie_func_input_arity = len(tree.children[1].children)
        try:
            ie_function_data = getattr(ie_functions, ie_func_name)
        except Exception:
            raise Exception("can't find ie function")
        correct_arity = len(ie_function_data.get_input_types())
        if ie_func_input_arity != correct_arity:
            raise Exception("incorrect input arity")


class CheckRuleSafetyVisitor(Visitor_Recursive):
    """
    A lark tree semantic check.
    checks whether the rules in the programs are safe.

    For a rule to be safe, two conditions must apply:

    1. Every free variable in the head occurs at least once in the body as an output of a relation.

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
    def __get_set_of_free_var_names(list_node):
        assert list_node.data in NODES_OF_LIST_WITH_FREE_VAR_NAMES
        free_var_names = set()
        for term_node in list_node.children:
            if term_node.data == "free_var_name":
                assert_expected_node_structure(term_node, "free_var_name", 1)
                free_var_names.add(term_node.children[0])
        return free_var_names

    def __get_set_of_input_free_var_names(self, relation_node):
        if relation_node.data == "relation":
            assert_expected_node_structure(relation_node, "relation", 2, "relation_name", "term_list")
            return set()  # normal relations don't have an input
        elif relation_node.data == "ie_relation":
            assert_expected_node_structure(relation_node, "ie_relation", 3, "relation_name", "term_list", "term_list")
            return self.__get_set_of_free_var_names(relation_node.children[1])
        else:
            assert 0

    def __get_set_of_output_free_var_names(self, relation_node):
        if relation_node.data == "relation":
            assert_expected_node_structure(relation_node, "relation", 2, "relation_name", "term_list")
            return self.__get_set_of_free_var_names(relation_node.children[1])
        elif relation_node.data == "ie_relation":
            assert_expected_node_structure(relation_node, "ie_relation", 3, "relation_name", "term_list", "term_list")
            return self.__get_set_of_free_var_names(relation_node.children[2])
        else:
            assert 0

    def rule(self, tree):
        assert_expected_node_structure(tree, "rule", 2, "rule_head", "rule_body")
        assert_expected_node_structure(tree.children[0], "rule_head", 2, "relation_name", "free_var_name_list")
        assert_expected_node_structure(tree.children[1], "rule_body", 1, "rule_body_relation_list")
        rule_head_term_list_node = tree.children[0].children[1]
        rule_body_relation_list_node = tree.children[1].children[0]
        assert_expected_node_structure(rule_head_term_list_node, "free_var_name_list")
        assert_expected_node_structure(rule_body_relation_list_node, "rule_body_relation_list")
        rule_body_relations = rule_body_relation_list_node.children
        # check that every free variable in the head occurs at least once in the body as an output of a relation.
        # get the free variables in the rule head
        rule_head_free_vars = self.__get_set_of_free_var_names(rule_head_term_list_node)
        # get the free variables in the rule body
        rule_body_free_vars = set()
        for relation_node in rule_body_relations:
            # get all the free variables that appear in the relation's output
            relation_output_free_vars = self.__get_set_of_output_free_var_names(relation_node)
            rule_body_free_vars = rule_body_free_vars.union(relation_output_free_vars)
        # make sure that every free var in the rule head appears at least once in the rule body
        invalid_free_var_names = rule_head_free_vars.difference(rule_body_free_vars)
        if invalid_free_var_names:
            raise Exception("rule not safe")
        # check that every relation in the rule body is safe
        # initialize assuming every relation is unsafe and every free variable is unbound
        safe_relation_indexes = set()
        bound_free_vars = set()
        found_safe_relation = True
        while len(safe_relation_indexes) != len(rule_body_relations) and found_safe_relation:
            found_safe_relation = False
            for idx, relation_node in enumerate(rule_body_relations):
                if idx not in safe_relation_indexes:
                    input_free_vars = self.__get_set_of_input_free_var_names(relation_node)
                    unbound_free_vars = input_free_vars.difference(bound_free_vars)
                    if not unbound_free_vars:
                        # relation is safe, mark all of its output variables as bound
                        found_safe_relation = True
                        output_free_vars = self.__get_set_of_output_free_var_names(relation_node)
                        bound_free_vars = bound_free_vars.union(output_free_vars)
                        safe_relation_indexes.add(idx)
        if len(safe_relation_indexes) != len(rule_body_relations):
            raise Exception("rule not safe")


class ReorderRuleBodyVisitor(Visitor_Recursive):
    """
    Reorders each rule body so that each relation in the rule body has its input free variables bound by
    the relations to its right.
    """

    def __init__(self, **kw):
        super().__init__()

    @staticmethod
    def __get_set_of_free_var_names(list_node):
        assert list_node.data in NODES_OF_LIST_WITH_FREE_VAR_NAMES
        free_var_names = set()
        for term_node in list_node.children:
            if term_node.data == "free_var_name":
                assert_expected_node_structure(term_node, "free_var_name", 1)
                free_var_names.add(term_node.children[0])
        return free_var_names

    def __get_set_of_input_free_var_names(self, relation_node):
        if relation_node.data == "relation":
            assert_expected_node_structure(relation_node, "relation", 2, "relation_name", "term_list")
            return set()  # normal relations don't have an input
        elif relation_node.data == "ie_relation":
            assert_expected_node_structure(relation_node, "ie_relation", 3, "relation_name", "term_list", "term_list")
            return self.__get_set_of_free_var_names(relation_node.children[1])
        else:
            assert 0

    def __get_set_of_output_free_var_names(self, relation_node):
        if relation_node.data == "relation":
            assert_expected_node_structure(relation_node, "relation", 2, "relation_name", "term_list")
            return self.__get_set_of_free_var_names(relation_node.children[1])
        elif relation_node.data == "ie_relation":
            assert_expected_node_structure(relation_node, "ie_relation", 3, "relation_name", "term_list", "term_list")
            return self.__get_set_of_free_var_names(relation_node.children[2])
        else:
            assert 0

    def rule(self, tree):
        assert_expected_node_structure(tree, "rule", 2, "rule_head", "rule_body")
        assert_expected_node_structure(tree.children[1], "rule_body", 1, "rule_body_relation_list")
        rule_body_relation_list_node = tree.children[1].children[0]
        assert_expected_node_structure(rule_body_relation_list_node, "rule_body_relation_list")
        rule_body_relations = rule_body_relation_list_node.children
        # initialize assuming every relation is unsafe and every free variable is unbound
        reordered_relations = []
        reordered_relations_idx = set()
        bound_free_vars = set()
        found_safe_relation = True
        while len(reordered_relations) != len(rule_body_relations) and found_safe_relation:
            found_safe_relation = False
            for idx, relation_node in enumerate(rule_body_relations):
                if idx not in reordered_relations_idx:
                    input_free_vars = self.__get_set_of_input_free_var_names(relation_node)
                    unbound_free_vars = input_free_vars.difference(bound_free_vars)
                    if not unbound_free_vars:
                        # relation is safe, mark all of its output variables as bound
                        found_safe_relation = True
                        output_free_vars = self.__get_set_of_output_free_var_names(relation_node)
                        bound_free_vars = bound_free_vars.union(output_free_vars)
                        reordered_relations_idx.add(idx)
                        reordered_relations.append(relation_node)
        if len(reordered_relations) != len(rule_body_relations):
            raise Exception("rule not safe")
        rule_body_relation_list_node.children = reordered_relations


class TypeCheckingInterpreter(Interpreter):
    """
    A lark tree semantic check.
    Assumes that relations and ie relations references and correct arity were checked.
    Also assumes variable references were checked.

    performs the following checks:
    1. checks if relation references are properly typed.
    2. checks if ie relations are properly typed.
    3. checks if free variables in rules do not have conflicting types.

    example for the semantic check failing on check no. 3:
    new A(str)
    new B(int)
    C(X) <- A(X), B(X) # error since X is expected to be both an int and a string
    """

    def __init__(self, **kw):
        super().__init__()
        self.symbol_table = kw['symbol_table']

    def __add_var_type(self, var_name_node, var_type: DataTypes):
        assert_expected_node_structure(var_name_node, "var_name", 1)
        var_name = var_name_node.children[0]
        self.symbol_table.set_variable_type(var_name, var_type)

    def __get_var_type(self, var_name_node):
        assert_expected_node_structure(var_name_node, "var_name", 1)
        var_name = var_name_node.children[0]
        return self.symbol_table.get_variable_type(var_name)

    def __add_relation_schema(self, relation_name_node, relation_schema):
        assert_expected_node_structure(relation_name_node, "relation_name", 1)
        relation_name = relation_name_node.children[0]
        self.symbol_table.set_relation_schema(relation_name, relation_schema)

    def __get_relation_schema(self, relation_name_node):
        assert_expected_node_structure(relation_name_node, "relation_name", 1)
        relation_name = relation_name_node.children[0]
        return self.symbol_table.get_relation_schema(relation_name)

    def __get_const_value_type(self, const_term_node):
        term_type = const_term_node.data
        if term_type == "var_name":
            assert_expected_node_structure(const_term_node, "var_name", 1)
            return self.__get_var_type(const_term_node)
        else:
            return DataTypes.from_string(term_type)

    def __get_term_types_list(self, term_list_node: Tree, free_var_mapping: dict = None,
                              relation_name_node: Tree = None):
        """
        get a list of the term types. The optional variables determine what type is assigned to a free
        variable, one and only one of them should be used.
        Args:
            term_list_node: node of a list of terms (e.g. terms used when declaring a fact).
            free_var_mapping: when encountering a free variable, get its type from this mapping.
            relation_name_node: when encountering a free variable, get its type from the schema of this relation.

        Returns: a list of the term types nb
        """
        assert term_list_node.data in NODES_OF_TERM_LISTS
        term_nodes = term_list_node.children
        schema = None
        if relation_name_node is not None:
            assert_expected_node_structure(relation_name_node, "relation_name", 1)
            schema = self.__get_relation_schema(relation_name_node)
            assert len(schema) == len(term_nodes)
        assert schema is None or free_var_mapping is None
        term_types = []
        for idx, term_node in enumerate(term_nodes):
            if term_node.data == "free_var_name":
                assert_expected_node_structure(term_node, "free_var_name", 1)
                if schema:
                    term_types.append(schema[idx])
                elif free_var_mapping:
                    term_types.append(free_var_mapping[term_node.children[0]])
                else:
                    assert 0
            else:
                term_types.append(self.__get_const_value_type(term_node))
        return term_types

    def assignment(self, tree):
        assert_expected_node_structure(tree, "assignment", 2, "var_name", tree.children[1].data)
        self.__add_var_type(tree.children[0], self.__get_const_value_type(tree.children[1]))

    def read_assignment(self, tree):
        assert_expected_node_structure(tree, "read_assignment", 2, "var_name", tree.children[1].data)
        self.__add_var_type(tree.children[0], DataTypes.string)

    def relation_declaration(self, tree):
        assert_expected_node_structure(tree, "relation_declaration", 2, "relation_name", "decl_term_list")
        decl_term_list_node = tree.children[1]
        assert_expected_node_structure(decl_term_list_node, "decl_term_list")
        declared_schema = []
        for term_node in decl_term_list_node.children:
            if term_node.data == "decl_string":
                declared_schema.append(DataTypes.string)
            elif term_node.data == "decl_span":
                declared_schema.append(DataTypes.span)
            elif term_node.data == "decl_int":
                declared_schema.append(DataTypes.integer)
            else:
                assert 0
        self.__add_relation_schema(tree.children[0], declared_schema)

    def add_fact(self, tree):
        assert_expected_node_structure(tree, "add_fact", 2, "relation_name", "const_term_list")
        relation_name_node = tree.children[0]
        term_list_node = tree.children[1]
        term_types = self.__get_term_types_list(term_list_node)
        schema = self.__get_relation_schema(relation_name_node)
        if schema != term_types:
            raise Exception("typechecking failed")

    def remove_fact(self, tree):
        assert_expected_node_structure(tree, "remove_fact", 2, "relation_name", "const_term_list")
        relation_name_node = tree.children[0]
        term_list_node = tree.children[1]
        term_types = self.__get_term_types_list(term_list_node)
        schema = self.__get_relation_schema(relation_name_node)
        if schema != term_types:
            raise Exception("typechecking failed")

    def query(self, tree):
        assert_expected_node_structure(tree, "query", 1, "relation")
        relation_node = tree.children[0]
        assert_expected_node_structure(relation_node, "relation", 2, "relation_name", "term_list")
        relation_name_node = relation_node.children[0]
        term_list_node = relation_node.children[1]
        term_types = self.__get_term_types_list(term_list_node, relation_name_node=relation_name_node)
        schema = self.__get_relation_schema(relation_name_node)
        if schema != term_types:
            raise Exception("typechecking failed")

    def __type_check_rule_body_term_list(self, term_list_node: Tree, correct_types: list,
                                         free_var_to_type: dict):
        """
        checks if a rule body relation is properly typed
        also checks for conflicting free variables
        Args:
            term_list_node: the term list of a rule body relation
            correct_types: a list of the types that the terms in the term list should have
            free_var_to_type: a mapping of free variables to their type (those that are currently known)
        """
        assert term_list_node.data in NODES_OF_RULE_BODY_TERM_LISTS
        assert len(term_list_node.children) == len(correct_types)
        for idx, term_node in enumerate(term_list_node.children):
            correct_type = correct_types[idx]
            if term_node.data == "free_var_name":
                assert_expected_node_structure(term_node, "free_var_name", 1)
                free_var = term_node.children[0]
                if free_var in free_var_to_type:
                    # free var already has a type, make sure there's no conflict with the currently wanted type
                    free_var_type = free_var_to_type[free_var]
                    if free_var_type != correct_type:
                        # found a conflicted free var
                        raise Exception("free var conflict found in typechecking")
                else:
                    # free var does not currently have a type, map it to the correct type
                    free_var_to_type[free_var] = correct_type
            else:
                term_type = self.__get_const_value_type(term_node)
                if term_type != correct_type:
                    # term is not properly typed
                    raise Exception("typechecking failed")

    def rule(self, tree):
        assert_expected_node_structure(tree, "rule", 2, "rule_head", "rule_body")
        assert_expected_node_structure(tree.children[0], "rule_head", 2, "relation_name", "free_var_name_list")
        assert_expected_node_structure(tree.children[1], "rule_body", 1, "rule_body_relation_list")
        rule_head_name_node = tree.children[0].children[0]
        rule_head_term_list_node = tree.children[0].children[1]
        rule_body_relation_list_node = tree.children[1].children[0]
        assert_expected_node_structure(rule_head_name_node, "relation_name", 1)
        assert_expected_node_structure(rule_head_term_list_node, "free_var_name_list")
        assert_expected_node_structure(rule_body_relation_list_node, "rule_body_relation_list")
        rule_body_relations = rule_body_relation_list_node.children
        free_var_to_type = dict()
        # Look for conflicting free variables and improperly typed relations
        for idx, relation_node in enumerate(rule_body_relations):
            if relation_node.data == "relation":
                assert_expected_node_structure(relation_node, "relation", 2, "relation_name", "term_list")
                relation_name_node = relation_node.children[0]
                term_list_node = relation_node.children[1]
                schema = self.__get_relation_schema(relation_name_node)
                self.__type_check_rule_body_term_list(term_list_node, schema, free_var_to_type)
            elif relation_node.data == "ie_relation":
                assert_expected_node_structure(relation_node, "ie_relation", 3, "relation_name", "term_list",
                                               "term_list")
                ie_func_name = relation_node.children[0].children[0]
                input_term_list_node = relation_node.children[1]
                output_term_list_node = relation_node.children[2]
                ie_func_data = getattr(ie_functions, ie_func_name)
                input_schema = ie_func_data.get_input_types()
                output_schema = ie_func_data.get_output_types(len(output_term_list_node.children))
                if output_schema is None:
                    raise Exception("invalid output arity")
                self.__type_check_rule_body_term_list(input_term_list_node, input_schema, free_var_to_type)
                self.__type_check_rule_body_term_list(output_term_list_node, output_schema, free_var_to_type)
            else:
                assert 0

        # no issues were found, add the new schema to the schema dict
        rule_head_schema = []
        for rule_head_term_node in rule_head_term_list_node.children:
            assert_expected_node_structure(rule_head_term_node, "free_var_name", 1)
            free_var_name = rule_head_term_node.children[0]
            assert free_var_name in free_var_to_type
            var_type = free_var_to_type[free_var_name]
            rule_head_schema.append(var_type)
        self.__add_relation_schema(rule_head_name_node, rule_head_schema)
