"""
this module contains implementation of regex ie functions using python's 're' module
"""

import spacy
sp = spacy.load('en_core_web_sm')

from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.ie_functions.ie_function_base import IEFunctionData

class Entities(IEFunctionData):
    def __init__(self):
        super().__init__()

    @staticmethod
    def ie_function(text):
        entities = sp(text).ents
        return (entity.text for entity in entities)

    @staticmethod
    def get_input_types():
        return [DataTypes.string]

    @staticmethod
    def get_output_types(output_arity):
        return tuple([DataTypes.string] * output_arity)


if __name__ == '__main__':
    e = Entities()
    i = e.ie_function(
        '''
        You've been living in a dream world, Neo.
        As in Baudrillard's vision, your whole life has been spent inside the map, not the territory.
        This is the world as it exists today.
        Welcome to the desert of the real.
        '''
    )

    from itertools import tee
    i, t = tee(i)
    maxlen = max(len(e) for e, ex in t)
    for e, ex in i:
        print(f'{e:<{maxlen}} - {ex}')
