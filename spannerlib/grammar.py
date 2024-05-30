# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00c_spannerlog_grammar.ipynb.

# %% auto 0
__all__ = ['logger', 'SpannerlogGrammar', 'spannerlog_expected_children_names_lists', 'parse_spannerlog', 'lark_to_nx_aux',
           'lark_to_nx']

# %% ../nbs/00c_spannerlog_grammar.ipynb 4
from typing import no_type_check, Set, Sequence, Any, Callable
#from spannerlib.graphs import GraphBase, EvalState
from typing import Sequence, Dict
from lark import Lark,Token, Tree, Transformer
import yaml

import logging
logger = logging.getLogger(__name__)
from graph_rewrite import rewrite,rewrite_iter,draw

from .utils import checkLogs, uniq_id


# %% ../nbs/00c_spannerlog_grammar.ipynb 6
SpannerlogGrammar = r"""
start: (_NEWLINE)* (statement (_NEWLINE)+)* (statement)?

?statement: relation_declaration
          | add_fact
          | remove_fact
          | rule
          | query
          | assignment

assignment: var_name "=" string
          | var_name "=" span
          | var_name "=" int
          | var_name "=" var_name
          | var_name "=" "read" "(" string ")" -> read_assignment
          | var_name "=" "read" "(" var_name ")" -> read_assignment

relation_declaration: "new" _SEPARATOR relation_name "(" decl_term_list ")"

decl_term_list: decl_term ("," decl_term)*

?decl_term: "str" -> decl_string
          | "span" -> decl_span
          | "int" -> decl_int

rule: rule_head "<-" rule_body_relation_list

rule_head: relation_name "(" free_var_name_list ")"

rule_body_relation_list: rule_body_relation ("," rule_body_relation)*

?rule_body_relation: relation
                   | ie_relation

relation: relation_name "(" term_list ")"

ie_relation: relation_name "(" term_list ")" "->" "(" term_list ")"

query: "?" relation_name "(" term_list ")"

term_list: term ("," term)*

?term: const_term
     | free_var_name

add_fact: relation_name "(" const_term_list ")"
        | relation_name "(" const_term_list ")" "<-" _TRUE

remove_fact: relation_name "(" const_term_list ")" "<-" _FALSE

const_term_list: const_term ("," const_term)*

?const_term: span
          | string
          | int
          | var_name

span: "[" int "," int ")"

int: INT -> integer

string: STRING

free_var_name_list: free_var_name ("," free_var_name)*

relation_name: LOWER_CASE_NAME
             | UPPER_CASE_NAME

var_name: LOWER_CASE_NAME

free_var_name : UPPER_CASE_NAME

_TRUE: "True"
_FALSE: "False"

LOWER_CASE_NAME: ("_"|LCASE_LETTER) ("_"|LETTER|DIGIT)*
UPPER_CASE_NAME: UCASE_LETTER ("_"|LETTER|DIGIT)*

_COMMENT: "#" /[^\n]*/

_SEPARATOR: (_WS_INLINE | _LINE_OVERFLOW_ESCAPE)+

STRING: "\"" (_STRING_INTERNAL (_LINE_OVERFLOW_ESCAPE)+)* _STRING_INTERNAL "\""

_LINE_OVERFLOW_ESCAPE: "\\" _NEWLINE

_NEWLINE: CR? LF
CR : /\r/
LF : /\n/

LCASE_LETTER: "a".."z"
UCASE_LETTER: "A".."Z"
LETTER: UCASE_LETTER | LCASE_LETTER
DIGIT: "0".."9"
_WS_INLINE: (" "|/\t/)+
%ignore _WS_INLINE
_STRING_INTERNAL: /.*?/ /(?<!\\)(\\\\)*?/
INT: DIGIT+
%ignore _LINE_OVERFLOW_ESCAPE
%ignore _COMMENT
"""

# %% ../nbs/00c_spannerlog_grammar.ipynb 8
def parse_spannerlog(spannerlog_code: str,start='start',as_string=False):
    parser = Lark(SpannerlogGrammar, parser='lalr',start=start)
    tree = parser.parse(spannerlog_code)
    if as_string:
        return tree.pretty()
    return tree


# %% ../nbs/00c_spannerlog_grammar.ipynb 15
import networkx as nx
def lark_to_nx_aux(tree,node_id,g):
    if isinstance(tree, Token):
        g.add_node(node_id,val=tree.value,type=tree.type)
    elif isinstance(tree, Tree):
        g.add_node(node_id,val=tree.data,type=tree.type)
        for i,child in enumerate(tree.children):
            child_id = uniq_id()
            g.add_edge(node_id,child_id)
            lark_to_nx_aux(child,child_id,g)
            


def lark_to_nx(t):
    g = nx.DiGraph()
    lark_to_nx_aux(t,uniq_id(),g)
    return g
    




# %% ../nbs/00c_spannerlog_grammar.ipynb 19
spannerlog_expected_children_names_lists: Dict[str, Sequence] = {

    'assignment': [
        ['var_name', 'string'],
        ['var_name', 'integer'],
        ['var_name', 'span'],
        ['var_name', 'var_name'],
    ],

    'read_assignment': [
        ['var_name', 'string'],
        ['var_name', 'var_name']
    ],

    'relation_declaration': [['relation_name', 'decl_term_list']],

    'rule': [['rule_head', 'rule_body_relation_list']],

    'rule_head': [['relation_name', 'free_var_name_list']],

    'relation': [['relation_name', 'term_list']],

    'ie_relation': [['relation_name', 'term_list', 'term_list']],

    'query': [['relation_name', 'term_list']],

    'add_fact': [['relation_name', 'const_term_list']],

    'remove_fact': [['relation_name', 'const_term_list']],

    'span': [
        ['integer', 'integer'],
        []  # allow empty list to support spans that were converted a datatypes.Span instance
    ],

    'integer': [[]],

    'string': [[]],

    'relation_name': [[]],

    'var_name': [[]],

    'free_var_name': [[]]
}
