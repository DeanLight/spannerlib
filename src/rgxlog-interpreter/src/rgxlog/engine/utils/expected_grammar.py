"""
This module contains structures that will help the developer assert that the ast he received matches the grammar
that he expects to work with.

These asserts are useful as a general safety check, and also for finding places in the code that need to change
should the rgxlog grammar be changed.
"""
from typing import Sequence, Dict

"""
for every node in the ast, the following structure contains a list of its expected children nodes names.

note that some nodes can have multiple kinds of children (e.g. assignment), for this reason each node is mapped
to a list of lists, where each of the internal lists is a valid list of children names for the node. this means
that in order to check if a node has an expected children list, one needs to check that this children list
matches one of the lists for this type of node in this structure.

note that some nodes in rgxlog can have varying lengths of children lists and therefore are not included in this
structure (e.g. term_list).

##############
#a proposed strategy for making changes to the rgxlog grammar:
##############
1. in your code, wherever you expect to receive an ast rgxlog node that still retains its original structure,
assert that it has the correct structure using this dict.

2. make a change to the grammar

3. run some rgxlog program, try to make it varied so it contains many different statements, and see where your
program crashes because of a failed expected node structure assertion.
wherever the program crashes, make changes to the code if any are needed so the code will work
using your new grammar, and temporarily comment the assertion for the correct node structure. repeat this step
until the program no longer crashes.

4. uncomment the assertion that you commented in step 3

5. change the 'rgxlog_expected_children_names_lists' to match your new grammar

for an example on how to use this structure, see lark_passes_utils.assert_expected_node_structure.
"""
rgxlog_expected_children_names_lists: Dict[str, Sequence] = {

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
