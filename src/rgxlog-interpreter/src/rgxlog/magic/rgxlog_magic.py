import os
import rgxlog.grammar
from lark import Lark, Transformer, v_args
from IPython.core.magic import register_cell_magic


@v_args(inline=True)
class TestTransformer(Transformer):
    integer = int


# noinspection PyUnusedLocal
@register_cell_magic
def spanner(line, cell):
    grammar_path = os.path.dirname(rgxlog.grammar.__file__)
    with open(f'{grammar_path}/grammar.lark', 'r') as grammar:
        parser = Lark(grammar, parser='lalr', transformer=TestTransformer(), debug=True)

        non_empty_lines = (line for line in cell.splitlines() if len(line))

        for line in non_empty_lines:
            print(parser.parse(line).pretty())
            print(parser.parse(line))
            print('-----------------------------------')
