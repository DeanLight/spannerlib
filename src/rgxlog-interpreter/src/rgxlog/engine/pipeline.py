import os

import rgxlog.grammar
from rgxlog.engine.graph_converters import Converter
import rgxlog.engine.graph_converters as graph_converters
import rgxlog.engine.lark_passes as lark_passes
from lark import Lark, Transformer, Visitor
from lark.visitors import Interpreter, Visitor_Recursive
import rgxlog.engine.execution as execution
from rgxlog.engine.execution import ExecutionBase, PydatalogEngine
import rgxlog.engine.netx_passes as netx_passes
from rgxlog.engine.netx_passes import NetxPass
from rgxlog.engine.symbol_table import SymbolTable
from rgxlog.engine.term_graph import NetxTermGraph
import sys
import io

symbol_table = SymbolTable()
term_graph = NetxTermGraph()
pydatalog_engine = PydatalogEngine(debug=False)


def run_passes(tree, pass_list, datalog_engine):
    """
    Runs the passes in pass_list on tree, one after another.
    """
    for cur_pass in pass_list:
        if issubclass(cur_pass, Visitor) or issubclass(cur_pass, Visitor_Recursive) or \
                issubclass(cur_pass, Interpreter):
            cur_pass(symbol_table=symbol_table, term_graph=term_graph).visit(tree)
        elif issubclass(cur_pass, Transformer):
            tree = cur_pass(symbol_table=symbol_table, term_graph=term_graph).transform(tree)
        elif issubclass(cur_pass, Converter):
            tree = cur_pass().convert(tree)
        elif issubclass(cur_pass, NetxPass):
            cur_pass(symbol_table=symbol_table, term_graph=term_graph).visit(tree)
        elif issubclass(cur_pass, ExecutionBase):
            term_graph.transform_graph(cur_pass(datalog_engine, symbol_table))
        else:
            assert 0
    return tree


# TODO put in a publicly accessibly config file and read it from there
passes = [
    lark_passes.RemoveTokensTransformer,
    lark_passes.StringVisitor,
    lark_passes.CheckReferencedVariablesInterpreter,
    lark_passes.CheckFilesInterpreter,
    lark_passes.CheckReservedRelationNames,
    lark_passes.CheckReferencedRelationsInterpreter,
    lark_passes.CheckReferencedIERelationsVisitor,
    lark_passes.CheckRuleSafetyVisitor,
    lark_passes.TypeCheckingInterpreter,
    lark_passes.ReorderRuleBodyVisitor,
    graph_converters.LarkTreeToNetxTreeConverter,
    netx_passes.ResolveVariablesPass,
    netx_passes.SimplifyRelationsPass,
    netx_passes.AddNetxTreeToTermGraphPass,
    execution.NetworkxExecution
]


def lark_pipeline(query_string):
    grammar_path = os.path.dirname(rgxlog.grammar.__file__)
    grammar_file = 'grammar.lark'
    with open(f'{grammar_path}/{grammar_file}', 'r') as grammar:
        parser = Lark(grammar, parser='lalr', debug=True, propagate_positions=True)
        try:
            parse_tree = parser.parse(query_string)
        except Exception as e:
            return "exception during parsing" + "\n" + str(e)
        try:
            original_stdout = sys.stdout
            temp_stdout = io.StringIO()
            sys.stdout = temp_stdout
            run_passes(parse_tree, passes, pydatalog_engine)
        except Exception as e:
            sys.stdout = original_stdout
            return "exception during semantic checks" + "\n" + str(e)
        sys.stdout = original_stdout
        return temp_stdout.getvalue()
        # for child in parse_tree.children:
        #     print(child)
        # leaving this commented for now as it might be useful for debugging
        # non_empty_lines = (line for line in cell.splitlines() if len(line))
        #
        # for line in non_empty_lines:
        #     print(parser.parse(line).pretty())
        #     print(parser.parse(line))
        #     print('-----------------------------------')


if __name__ == "__main__":
    some_input = """
    new A(str)
    A("bob")
    ?A(X)
    """
    lark_pipeline(some_input)
