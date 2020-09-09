import os
import rgxlog.grammar
from lark import Lark, Transformer, v_args
from IPython.core.magic import register_cell_magic


@v_args(inline=True)
class TestTransformer(Transformer):
    # get rid of "integer" in the tree
    integer = int


# noinspection PyUnusedLocal
@register_cell_magic
def spanner(line, cell):
    grammar_path = os.path.dirname(rgxlog.grammar.__file__)
    with open(f'{grammar_path}/grammar.lark', 'r') as grammar:
        parser = Lark(grammar, parser='earley', debug=False)
        parse_tree = parser.parse(cell)
        parse_tree = TestTransformer().transform(parse_tree)
        print(parse_tree.pretty())
        print(parse_tree)
        # leaving this commented for now as it might be useful for debugging
        # non_empty_lines = (line for line in cell.splitlines() if len(line))
        #
        # for line in non_empty_lines:
        #     print(parser.parse(line).pretty())
        #     print(parser.parse(line))
        #     print('-----------------------------------')

