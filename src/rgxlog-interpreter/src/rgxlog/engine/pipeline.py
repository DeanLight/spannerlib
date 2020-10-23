import os

from lark import Lark, Transformer, v_args
from lark.visitors import Interpreter, Visitor_Recursive
import rgxlog.grammar
from rgxlog.engine.graph_converters import Converter
import rgxlog.engine.graph_converters as graph_converters
import rgxlog.engine.lark_passes as lark_passes
from lark import Lark, Transformer, Visitor
from lark.visitors import Interpreter, Visitor_Recursive


def run_passes(tree, pass_list):
    for cur_pass in pass_list:
        if issubclass(cur_pass, Visitor) or issubclass(cur_pass, Visitor_Recursive) \
                or issubclass(cur_pass, Interpreter):
            cur_pass().visit(tree)
        elif issubclass(cur_pass, Transformer):
            tree = cur_pass().transform(tree)
        elif issubclass(cur_pass, Converter):
            tree = cur_pass().convert(tree)
        else:
            assert 0
    return tree


# TODO put in a publicly accessibly config file and read it from there
passes = [
    lark_passes.RemoveTokensTransformer,
    lark_passes.StringVisitor,
    lark_passes.CheckReferencedVariablesInterpreter,
    lark_passes.CheckReferencedRelationsInterpreter,
    lark_passes.CheckRuleSafetyVisitor,
    lark_passes.TypeCheckingInterpreter,
    graph_converters.LarkTreeToNetxTreeConverter
]


def lark_pipeline(query_string):
    grammar_path = os.path.dirname(rgxlog.grammar.__file__)
    grammar_file = 'grammar.lark'
    with open(f'{grammar_path}/{grammar_file}', 'r') as grammar:
        parser = Lark(grammar, parser='lalr', debug=True, propagate_positions=True)
        try:
            parse_tree = parser.parse(query_string)
        except Exception:
            return "exception during parsing"
        try:
            parse_tree = run_passes(parse_tree, passes)
        except Exception:
            return "exception during semantic checks"
        return parse_tree.pretty()
        # for child in parse_tree.children:
        #     print(child)
        # leaving this commented for now as it might be useful for debugging
        # non_empty_lines = (line for line in cell.splitlines() if len(line))
        #
        # for line in non_empty_lines:
        #     print(parser.parse(line).pretty())
        #     print(parser.parse(line))
        #     print('-----------------------------------')
