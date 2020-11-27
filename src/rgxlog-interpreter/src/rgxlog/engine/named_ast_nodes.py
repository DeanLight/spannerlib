"""
TODO
for each statement node in the grammar, this module contains a matching named tuple that will represent
that statement in the semantic c
"""

from collections import namedtuple

# TODO short description for every named tuple

RelationDeclarationNode = namedtuple('RelationDeclarationNode', ['relation_name', 'type_list'])

AddFactNode = namedtuple('AddFactNode', ['relation_name', 'term_list', 'type_list'])

RemoveFactNode = namedtuple('RemoveFactNode', ['relation_name', 'term_list', 'type_list'])

QueryNode = namedtuple('QueryNode', ['relation_name', 'term_list', 'type_list'])

AssignmentNode = namedtuple("AssignmentNode", ['var_name', 'value', 'value_type'])

ReadAssignmentNode = namedtuple("ReadAssignmentNode", ['var_name', 'value', 'value_type'])

RuleNode = namedtuple('RuleNode', ['head_relation', 'body_relation_list', 'body_relation_type_list'])

RelationNode = namedtuple('RelationNode', ['relation_name', 'term_list', 'type_list'])

IERelationNode = namedtuple('IERelationNode', ['relation_name', 'input_term_list', 'input_type_list',
                                                       'output_term_list', 'output_type_list'])
