from lark import Lark, Transformer, v_args


def load_ipython_extension(ipython):
    ipython.register_magic_function(lark, 'cell')


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
def lark(line, cell):
    with open('grammar.lark', 'r') as grammar:
        parser = Lark(grammar, parser='lalr', transformer=CalculateTree())

        non_empty_lines = (line for line in cell.splitlines() if len(line))

        for line in non_empty_lines:
            print(parser.parse(line))
