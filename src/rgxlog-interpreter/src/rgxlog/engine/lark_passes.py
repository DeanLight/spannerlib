from lark import Transformer, v_args, Visitor, Tree
from lark.visitors import Interpreter, Visitor_Recursive
from enum import Enum

NODES_OF_LIST_WITH_VAR_NAMES = {"term_list", "const_term_list"}
NODES_OF_LIST_WITH_RELATION_NODES = {"rule_body_relation_list"}
NODES_OF_LIST_WITH_FREE_VAR_NAMES = {"term_list", "free_var_name_list"}
NODES_OF_TERM_LISTS = {"term_list", "const_term_list"}
NODES_OF_RULE_BODY_TERM_LISTS = {"term_list"}
SCHEMA_DEFINING_NODES = {"decl_term_list", "free_var_name_list"}


class VarTypes(Enum):
    STRING = 0
    SPAN = 1
    INT = 2


def assert_correct_node(tree, node_name, len_children=None, *children_names):
    assert tree.data == node_name, "bad node name: " + node_name + \
                                   "\n actual node name: " + tree.data
    if len_children is not None:
        assert len(tree.children) == len_children, "bad children length: " + str(len_children) + \
                                                   "\n actual children length: " + str(len(tree.children))
    if children_names is not None:
        for idx, name in enumerate(children_names):
            assert tree.children[idx].data == name, "bad child name at index " + str(idx) + ": " + \
                                                    name + \
                                                    "\n actual child name: " + tree.children[idx].data


@v_args(inline=False)
class RemoveTokensTransformer(Transformer):
    """
    transforms the lark tree by removing the redundant tokens.
    should be used before all the other passes as they assume no tokens exists
    """

    def __init__(self):
        super().__init__(visit_tokens=True)

    def INT(self, args):
        return int(args[0:])

    def LOWER_CASE_NAME(self, args):
        return args[0:]

    def UPPER_CASE_NAME(self, args):
        return args[0:]

    def STRING(self, args):
        # removes the quotation marks
        return args[1:-1]


class StringVisitor(Visitor_Recursive):
    """
     Fixes the strings in the lark tree.
     Removes the line overflow escapes from strings
     """

    def string(self, tree):
        tree.children[0] = tree.children[0].replace('\\\n', '')


class CheckReferencedVariablesInterpreter(Interpreter):
    """
    A lark tree semantic check.
    checks whether each variable reference refers to a defined variable.
    """

    def __init__(self):
        super().__init__()
        self.vars = set()

    def __add_var_name_to_vars(self, var_name_node):
        assert_correct_node(var_name_node, "var_name", 1)
        var_name = var_name_node.children[0]
        self.vars.add(var_name)

    def __check_if_var_not_defined(self, var_name_node):
        assert_correct_node(var_name_node, "var_name", 1)
        var_name = var_name_node.children[0]
        if var_name not in self.vars:
            raise Exception

    def __check_if_vars_in_list_not_defined(self, tree):
        assert tree.data in NODES_OF_LIST_WITH_VAR_NAMES
        for child in tree.children:
            if child.data == "var_name":
                self.__check_if_var_not_defined(child)

    def assign_literal_string(self, tree):
        assert_correct_node(tree, "assign_literal_string", 2, "var_name", "string")
        self.__add_var_name_to_vars(tree.children[0])

    def assign_string_from_file_string_param(self, tree):
        assert_correct_node(tree, "assign_string_from_file_string_param", 2, "var_name", "string")
        self.__add_var_name_to_vars(tree.children[0])

    def assign_string_from_file_var_param(self, tree):
        assert_correct_node(tree, "assign_string_from_file_var_param", 2, "var_name", "var_name")
        self.__check_if_var_not_defined(tree.children[1])
        self.__add_var_name_to_vars(tree.children[0])

    def assign_span(self, tree):
        assert_correct_node(tree, "assign_span", 2, "var_name", "span")
        self.__add_var_name_to_vars(tree.children[0])

    def assign_int(self, tree):
        assert_correct_node(tree, "assign_int", 2, "var_name", "integer")
        self.__add_var_name_to_vars(tree.children[0])

    def assign_var(self, tree):
        assert_correct_node(tree, "assign_var", 2, "var_name", "var_name")
        self.__check_if_var_not_defined(tree.children[1])
        self.__add_var_name_to_vars(tree.children[0])

    def relation(self, tree):
        assert_correct_node(tree, "relation", 2, "relation_name", "term_list")
        self.__check_if_vars_in_list_not_defined(tree.children[1])

    def add_fact(self, tree):
        assert_correct_node(tree, "add_fact", 2, "relation_name", "const_term_list")
        self.__check_if_vars_in_list_not_defined(tree.children[1])

    def remove_fact(self, tree):
        assert_correct_node(tree, "remove_fact", 2, "relation_name", "const_term_list")
        self.__check_if_vars_in_list_not_defined(tree.children[1])

    def rgx_ie_relation(self, tree):
        assert_correct_node(tree, "rgx_ie_relation", 3, "term_list", "term_list", "var_name")
        self.__check_if_vars_in_list_not_defined(tree.children[0])
        self.__check_if_vars_in_list_not_defined(tree.children[1])
        self.__check_if_var_not_defined(tree.children[2])

    def func_ie_relation(self, tree):
        assert_correct_node(tree, "func_ie_relation", 3, "function_name", "term_list", "term_list")
        self.__check_if_vars_in_list_not_defined(tree.children[1])
        self.__check_if_vars_in_list_not_defined(tree.children[2])


class CheckReferencedRelationsInterpreter(Interpreter):
    """
    A lark tree semantic check.
    checks whether each non ie relation reference refers to a defined relation.
    Also checks if the relation reference uses the correct arity.
    """

    def __init__(self):
        super().__init__()
        self.relation_name_to_arity = dict()

    def __add_relation_definition(self, relation_name_node, schema_defining_node):
        assert_correct_node(relation_name_node, "relation_name", 1)
        assert schema_defining_node.data in SCHEMA_DEFINING_NODES
        relation_name = relation_name_node.children[0]
        assert relation_name not in self.relation_name_to_arity
        arity = len(schema_defining_node.children)
        self.relation_name_to_arity[relation_name] = arity

    def __check_if_relation_not_defined(self, relation_name_node, term_list_node):
        assert_correct_node(relation_name_node, "relation_name", 1)
        assert term_list_node.data in NODES_OF_TERM_LISTS
        relation_name = relation_name_node.children[0]
        if relation_name not in self.relation_name_to_arity:
            raise Exception
        arity = len(term_list_node.children)
        correct_arity = self.relation_name_to_arity[relation_name]
        if arity != correct_arity:
            raise Exception

    def __check_if_relation_already_defined(self, relation_name_node):
        assert_correct_node(relation_name_node, "relation_name", 1)
        relation_name = relation_name_node.children[0]
        if relation_name in self.relation_name_to_arity:
            raise Exception

    def relation_declaration(self, tree):
        assert_correct_node(tree, "relation_declaration", 2, "relation_name", "decl_term_list")
        self.__check_if_relation_already_defined(tree.children[0])
        self.__add_relation_definition(tree.children[0], tree.children[1])

    def query(self, tree):
        assert_correct_node(tree, "query", 1, "relation")
        relation_node = tree.children[0]
        assert_correct_node(relation_node, "relation", 2, "relation_name", "term_list")
        self.__check_if_relation_not_defined(relation_node.children[0], relation_node.children[1])

    def add_fact(self, tree):
        assert_correct_node(tree, "add_fact", 2, "relation_name", "const_term_list")
        self.__check_if_relation_not_defined(tree.children[0], tree.children[1])

    def remove_fact(self, tree):
        assert_correct_node(tree, "remove_fact", 2, "relation_name", "const_term_list")
        self.__check_if_relation_not_defined(tree.children[0], tree.children[1])

    def rule(self, tree):
        assert_correct_node(tree, "rule", 2, "rule_head", "rule_body")
        rule_head_node = tree.children[0]
        rule_body_node = tree.children[1]
        assert_correct_node(rule_head_node, "rule_head", 2, "relation_name", "free_var_name_list")
        assert_correct_node(rule_body_node, "rule_body", 1, "rule_body_relation_list")
        self.__check_if_relation_already_defined(rule_head_node.children[0])
        relation_list_node = rule_body_node.children[0]
        assert_correct_node(relation_list_node, "rule_body_relation_list")
        for relation_node in relation_list_node.children:
            if relation_node.data == "relation":
                assert_correct_node(relation_node, "relation", 2, "relation_name", "term_list")
                self.__check_if_relation_not_defined(relation_node.children[0], relation_node.children[1])
        self.__add_relation_definition(rule_head_node.children[0], rule_head_node.children[1])


class CheckReferencedIERelationsVisitor(Visitor_Recursive):
    """
    A lark tree semantic check.
    checks whether each ie relation reference refers to a defined ie function.
    Also checks if the ie relation reference uses the correct arity for the ie function.
    """

    def __init__(self):
        super().__init__()

    def func_ie_relation(self, tree):
        assert_correct_node(tree, "func_ie_relation", 3, "function_name", "term_list", "term_list")
        # TODO

    def rgx_ie_relation(self, tree):
        assert_correct_node(tree, "rgx_ie_relation", 3, "term_list", "term_list", "var_name")
        # TODO


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

    def __init__(self):
        super().__init__()

    @staticmethod
    def __get_set_of_free_var_names(list_node):
        assert list_node.data in NODES_OF_LIST_WITH_FREE_VAR_NAMES
        free_var_names = set()
        for term_node in list_node.children:
            if term_node.data == "free_var_name":
                assert_correct_node(term_node, "free_var_name", 1)
                free_var_names.add(term_node.children[0])
        return free_var_names

    def __get_set_of_input_free_var_names(self, relation_node):
        if relation_node.data == "relation":
            assert_correct_node(relation_node, "relation", 2, "relation_name", "term_list")
            return set()  # normal relations don't have an input
        elif relation_node.data == "func_ie_relation":
            assert_correct_node(relation_node, "func_ie_relation", 3, "function_name", "term_list", "term_list")
            return self.__get_set_of_free_var_names(relation_node.children[1])
        else:
            assert_correct_node(relation_node, "rgx_ie_relation", 3, "term_list", "term_list", "var_name")
            return self.__get_set_of_free_var_names(relation_node.children[0])

    def __get_set_of_output_free_var_names(self, relation_node):
        if relation_node.data == "relation":
            assert_correct_node(relation_node, "relation", 2, "relation_name", "term_list")
            return self.__get_set_of_free_var_names(relation_node.children[1])
        elif relation_node.data == "func_ie_relation":
            assert_correct_node(relation_node, "func_ie_relation", 3, "function_name", "term_list", "term_list")
            return self.__get_set_of_free_var_names(relation_node.children[2])
        else:
            assert_correct_node(relation_node, "rgx_ie_relation", 3, "term_list", "term_list", "var_name")
            return self.__get_set_of_free_var_names(relation_node.children[1])

    def rule(self, tree):
        assert_correct_node(tree, "rule", 2, "rule_head", "rule_body")
        assert_correct_node(tree.children[0], "rule_head", 2, "relation_name", "free_var_name_list")
        assert_correct_node(tree.children[1], "rule_body", 1, "rule_body_relation_list")
        rule_head_term_list_node = tree.children[0].children[1]
        rule_body_relation_list_node = tree.children[1].children[0]
        assert_correct_node(rule_head_term_list_node, "free_var_name_list")
        assert_correct_node(rule_body_relation_list_node, "rule_body_relation_list")
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
            raise Exception
        # check that every relation in the rule body is safe
        # initialize assuming every relation is unsafe and every free variable is unbound
        safe_relation_indexes = set()
        bound_free_vars = set()
        found_safe_relation_in_cur_iter = True
        while len(safe_relation_indexes) != len(rule_body_relations) \
                and found_safe_relation_in_cur_iter:
            found_safe_relation_in_cur_iter = False
            for idx, relation_node in enumerate(rule_body_relations):
                if idx not in safe_relation_indexes:
                    input_free_vars = self.__get_set_of_input_free_var_names(relation_node)
                    unbound_free_vars = input_free_vars.difference(bound_free_vars)
                    if not unbound_free_vars:
                        # relation is safe, mark all of its output variables as bound
                        found_safe_relation_in_cur_iter = True
                        output_free_vars = self.__get_set_of_output_free_var_names(relation_node)
                        bound_free_vars = bound_free_vars.union(output_free_vars)
                        safe_relation_indexes.add(idx)
        if len(safe_relation_indexes) != len(rule_body_relations):
            raise Exception


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

    def __init__(self):
        super().__init__()
        self.var_name_to_type = dict()
        self.relation_name_to_schema = dict()

    def __add_var_type(self, var_name_node, var_type: VarTypes):
        assert_correct_node(var_name_node, "var_name", 1)
        var_name = var_name_node.children[0]
        self.var_name_to_type[var_name] = var_type

    def __get_var_type(self, var_name_node):
        assert_correct_node(var_name_node, "var_name", 1)
        var_name = var_name_node.children[0]
        assert var_name in self.var_name_to_type
        return self.var_name_to_type[var_name]

    def __add_relation_schema(self, relation_name_node, relation_schema):
        assert_correct_node(relation_name_node, "relation_name", 1)
        relation_name = relation_name_node.children[0]
        assert relation_name not in self.relation_name_to_schema
        self.relation_name_to_schema[relation_name] = relation_schema

    def __get_relation_schema(self, relation_name_node):
        assert_correct_node(relation_name_node, "relation_name", 1)
        relation_name = relation_name_node.children[0]
        assert relation_name in self.relation_name_to_schema
        return self.relation_name_to_schema[relation_name]

    def __get_const_term_type(self, const_term_node):
        term_type = const_term_node.data
        if term_type == "string":
            return VarTypes.STRING
        elif term_type == "span":
            return VarTypes.SPAN
        elif term_type == "integer":
            return VarTypes.INT
        elif term_type == "var_name":
            assert_correct_node(const_term_node, "var_name", 1)
            return self.__get_var_type(const_term_node)
        else:
            # do not allow for term type of "free_var_name" as it is not a constant
            assert 0

    def __get_term_types_list(self, term_list_node: Tree, free_var_mapping: dict = None,
                              relation_name_node: Tree = None):
        """
        get a list of the term types. The optional variables determine what type is assigned to a free
        variable, one and only one of them should be used.
        :param term_list_node: node of a list of terms (e.g. terms used when declaring a fact).
        :param free_var_mapping: when encountering a free variable, get its type from this mapping.
        :param relation_name_node: when encountering a free variable, get its type from the schema of this relation.
        :return: a list of the term types
        """
        assert term_list_node.data in NODES_OF_TERM_LISTS
        term_nodes = term_list_node.children
        schema = None
        if relation_name_node is not None:
            assert_correct_node(relation_name_node, "relation_name", 1)
            schema = self.__get_relation_schema(relation_name_node)
            assert len(schema) == len(term_nodes)
        assert schema is None or free_var_mapping is None
        term_types = []
        for idx, term_node in enumerate(term_nodes):
            if term_node.data == "free_var_name":
                assert_correct_node(term_node, "free_var_name", 1)
                if schema:
                    term_types.append(schema[idx])
                elif free_var_mapping:
                    term_types.append(free_var_mapping[term_node.children[0]])
                else:
                    assert 0
            else:
                term_types.append(self.__get_const_term_type(term_node))
        return term_types

    def assign_literal_string(self, tree):
        assert_correct_node(tree, "assign_literal_string", 2, "var_name", "string")
        self.__add_var_type(tree.children[0], VarTypes.STRING)

    def assign_string_from_file_string_param(self, tree):
        assert_correct_node(tree, "assign_string_from_file_string_param", 2, "var_name", "string")
        self.__add_var_type(tree.children[0], VarTypes.STRING)

    def assign_string_from_file_var_param(self, tree):
        assert_correct_node(tree, "assign_string_from_file_var_param", 2, "var_name", "var_name")
        self.__add_var_type(tree.children[0], VarTypes.STRING)

    def assign_span(self, tree):
        assert_correct_node(tree, "assign_span", 2, "var_name", "span")
        self.__add_var_type(tree.children[0], VarTypes.SPAN)

    def assign_int(self, tree):
        assert_correct_node(tree, "assign_int", 2, "var_name", "integer")
        self.__add_var_type(tree.children[0], VarTypes.INT)

    def assign_var(self, tree):
        assert_correct_node(tree, "assign_var", 2, "var_name", "var_name")
        self.__add_var_type(tree.children[0], self.__get_var_type(tree.children[1]))

    def relation_declaration(self, tree):
        assert_correct_node(tree, "relation_declaration", 2, "relation_name", "decl_term_list")
        decl_term_list_node = tree.children[1]
        assert_correct_node(decl_term_list_node, "decl_term_list")
        declared_schema = []
        for term_node in decl_term_list_node.children:
            if term_node.data == "decl_string":
                declared_schema.append(VarTypes.STRING)
            elif term_node.data == "decl_span":
                declared_schema.append(VarTypes.SPAN)
            elif term_node.data == "decl_int":
                declared_schema.append(VarTypes.INT)
            else:
                assert 0
        self.__add_relation_schema(tree.children[0], declared_schema)

    def add_fact(self, tree):
        assert_correct_node(tree, "add_fact", 2, "relation_name", "const_term_list")
        relation_name_node = tree.children[0]
        term_list_node = tree.children[1]
        term_types = self.__get_term_types_list(term_list_node)
        schema = self.__get_relation_schema(relation_name_node)
        if schema != term_types:
            raise Exception

    def remove_fact(self, tree):
        assert_correct_node(tree, "remove_fact", 2, "relation_name", "const_term_list")
        relation_name_node = tree.children[0]
        term_list_node = tree.children[1]
        term_types = self.__get_term_types_list(term_list_node)
        schema = self.__get_relation_schema(relation_name_node)
        if schema != term_types:
            raise Exception

    def query(self, tree):
        assert_correct_node(tree, "query", 1, "relation")
        relation_node = tree.children[0]
        assert_correct_node(relation_node, "relation", 2, "relation_name", "term_list")
        relation_name_node = relation_node.children[0]
        term_list_node = relation_node.children[1]
        term_types = self.__get_term_types_list(term_list_node, relation_name_node=relation_name_node)
        schema = self.__get_relation_schema(relation_name_node)
        if schema != term_types:
            raise Exception

    def __type_check_rule_body_term_list(self, term_list_node: Tree, correct_types: list,
                                         free_var_to_type: dict):
        """
        checks if a rule body relation is properly typed
        also checks for conflicting free variables
        :param term_list_node: the term list of a rule body relation
        :param correct_types: a list of the types that the terms in the term list should have
        :param free_var_to_type: a mapping of free variables to their type (those that are currently known)
        :return:
        """
        assert term_list_node.data in NODES_OF_RULE_BODY_TERM_LISTS
        assert len(term_list_node.children) == len(correct_types)
        for idx, term_node in enumerate(term_list_node.children):
            correct_type = correct_types[idx]
            if term_node.data == "free_var_name":
                assert_correct_node(term_node, "free_var_name", 1)
                free_var = term_node.children[0]
                if free_var in free_var_to_type:
                    # free var already has a type, make sure there's no conflict with the currently wanted type
                    free_var_type = free_var_to_type[free_var]
                    if free_var_type != correct_type:
                        # found a conflicted free var
                        raise Exception
                else:
                    # free var does not currently have a type, map it to the correct type
                    free_var_to_type[free_var] = correct_type
            else:
                term_type = self.__get_const_term_type(term_node)
                if term_type != correct_type:
                    # term is not properly typed
                    raise Exception

    def rule(self, tree):
        assert_correct_node(tree, "rule", 2, "rule_head", "rule_body")
        assert_correct_node(tree.children[0], "rule_head", 2, "relation_name", "free_var_name_list")
        assert_correct_node(tree.children[1], "rule_body", 1, "rule_body_relation_list")
        rule_head_name_node = tree.children[0].children[0]
        assert rule_head_name_node.children[0] not in self.relation_name_to_schema
        rule_head_term_list_node = tree.children[0].children[1]
        rule_body_relation_list_node = tree.children[1].children[0]
        assert_correct_node(rule_head_name_node, "relation_name", 1)
        assert_correct_node(rule_head_term_list_node, "free_var_name_list")
        assert_correct_node(rule_body_relation_list_node, "rule_body_relation_list")
        rule_body_relations = rule_body_relation_list_node.children
        free_var_to_type = dict()
        # Look for conflicting free variables and improperly typed relations
        for idx, relation_node in enumerate(rule_body_relations):
            if relation_node.data == "relation":
                assert_correct_node(relation_node, "relation", 2, "relation_name", "term_list")
                relation_name_node = relation_node.children[0]
                term_list_node = relation_node.children[1]
                schema = self.__get_relation_schema(relation_name_node)
                self.__type_check_rule_body_term_list(term_list_node, schema, free_var_to_type)
            elif relation_node.data == "func_ie_relation":
                assert_correct_node(relation_node, "func_ie_relation", 3, "function_name", "term_list", "term_list")
                # TODO
            else:
                assert_correct_node(relation_node, "rgx_ie_relation", 3, "term_list", "term_list", "var_name")
                # TODO

        # no issues were found, add the new schema to the schema dict
        rule_head_schema = []
        for rule_head_term_node in rule_head_term_list_node.children:
            assert_correct_node(rule_head_term_node, "free_var_name", 1)
            free_var_name = rule_head_term_node.children[0]
            assert free_var_name in free_var_to_type
            var_type = free_var_to_type[free_var_name]
            rule_head_schema.append(var_type)
        rule_head_name = rule_head_name_node.children[0]
        self.relation_name_to_schema[rule_head_name] = rule_head_schema
