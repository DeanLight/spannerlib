import os
from lark import Lark, Transformer, v_args
from IPython.core.magic import register_cell_magic


@v_args(inline=True)
class CalculateTree(Transformer):
    # noinspection PyUnresolvedReferences
    from operator import add, sub, mul, truediv as div, neg
    number = float

    def __init__(self):
        super().__init__()
        self.vars = {}

    def assign_var(self, name, value):
        self.vars[name] = value
        return value

    def var(self, name):
        return self.vars[name]


# noinspection PyUnusedLocal
@register_cell_magic
def lark(line, cell):
    # TODO delete this func
    print('%%lark is deprecated, please use %%rgx from now on')
    rgx(line, cell)


# noinspection PyUnusedLocal
@register_cell_magic
def rgx(line, cell):
    rgxlog_interpreter_dir_path = os.path.dirname(os.path.abspath(__file__))
    with open(f'{rgxlog_interpreter_dir_path}/grammar.lark', 'r') as grammar:
        # for now, plug the whole "cell" string into the parser
        # line by line made sense for calc, not so much for query / queries
        # as far as i can tell, at least at this present moment
        pass
        # parser = Lark(grammar, parser='lalr', transformer=CalculateTree())
        #
        # non_empty_lines = (line for line in cell.splitlines() if len(line))
        #
        # for line in non_empty_lines:
        #     print(parser.parse(line))
