import os
import rgxlog.grammar
from lark import Lark, Transformer, v_args
from lark.visitors import Interpreter, Visitor_Recursive
from IPython.core.magic import register_cell_magic


class MultilineStringToStringVisitor(Visitor_Recursive):

    def __init__(self):
        super().__init__()

    def multiline_string(self, tree):
        assert_correct_node(tree, "multiline_string")
        result = ""
        for child_string in tree.children:
            result += child_string
        # redefine the node to be a regular string node
        tree.data = "string"
        tree.children = [result]


@v_args(inline=False)
class RemoveTokensTransformer(Transformer):
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


class CheckReferencedVariablesInterpreter(Interpreter):

    def __init__(self):
        super().__init__()
        self.vars = set()

    def assign_literal_string(self, tree):
        assert_correct_node(tree, "assign_literal_string", 2, "var_name", "string")
        var_name = tree.children[0].children[0]
        self.vars.add(var_name)

    def assign_string_from_file_string_param(self, tree):
        assert_correct_node(tree, "assign_string_from_file_string_param", 2, "var_name", "string")
        var_name = tree.children[0].children[0]
        self.vars.add(var_name)

    def assign_string_from_file_var_param(self, tree):
        assert_correct_node(tree, "assign_string_from_file_var_param", 2, "var_name", "var_name")
        right_var_name = tree.children[1].children[0]
        if right_var_name not in self.vars:
            raise NameError("variable " + right_var_name + " is not defined")
        left_var_name = tree.children[0].children[0]
        self.vars.add(left_var_name)

    def assign_span(self, tree):
        assert_correct_node(tree, "assign_span", 2, "var_name", "span")
        var_name = tree.children[0].children[0]
        self.vars.add(var_name)

    def assign_var(self, tree):
        assert_correct_node(tree, "assign_var", 2, "var_name", "var_name")
        right_var_name = tree.children[1].children[0]
        if right_var_name not in self.vars:
            raise NameError("variable " + right_var_name + " is not defined")
        left_var_name = tree.children[0].children[0]
        self.vars.add(left_var_name)

    # TODO after we decide what to do with free variables:
    # TODO relation
    # TODO rgx_relation
    def rgx_ie_relation(self, tree):
        assert_correct_node(tree, "rgx_ie_relation", 3, "term_list", "term_list", "var_name")
        var_name = tree.children[-1].children[0]
        if var_name not in self.vars:
            raise NameError("variable " + var_name + " is not defined")
    # TODO ie relation


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


# noinspection PyUnusedLocal
@register_cell_magic
def spanner(line, cell):
    grammar_path = os.path.dirname(rgxlog.grammar.__file__)
    grammar_file = 'grammar.lark'  # TODO: make it overrideable to end users?
    with open(f'{grammar_path}/{grammar_file}', 'r') as grammar:
        parser = Lark(grammar, parser='earley', debug=False)
        parse_tree = parser.parse(cell)
        parse_tree = RemoveTokensTransformer().transform(parse_tree)
        parse_tree = MultilineStringToStringVisitor().visit(parse_tree)
        CheckReferencedVariablesInterpreter().visit(parse_tree)
        print(parse_tree.pretty())
        # for child in parse_tree.children:
        #     print(child)
        # leaving this commented for now as it might be useful for debugging
        # non_empty_lines = (line for line in cell.splitlines() if len(line))
        #
        # for line in non_empty_lines:
        #     print(parser.parse(line).pretty())
        #     print(parser.parse(line))
        #     print('-----------------------------------')
