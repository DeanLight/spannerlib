from rgxlog.engine.datatypes import DataTypes


def get_term_list_string(term_list, term_types):
    ret = ""
    for idx, term in enumerate(term_list):
        if term_types[idx] == DataTypes.STRING:
            ret += '"' + term + '"'
        else:
            ret += str(term)
        if idx < len(term_list) - 1:
            ret += ", "
    return ret


class Span:
    """A representation of a span"""

    def __init__(self, left_num, right_num):
        self.left_num = left_num
        self.right_num = right_num

    def __str__(self):
        return "[" + str(self.left_num) + ", " + str(self.right_num) + ")"

    def get_pydatalog_string(self):
        # due to pyDatalog limitations, a span is represented in pyDatalog as a normal tuple of length 2
        return "(" + str(self.left_num) + ", " + str(self.right_num) + ")"


class Relation:
    """a representation of a normal relation"""

    def __init__(self, name, terms, term_types):
        assert len(terms) == len(term_types)
        self.name = name
        self.terms = terms
        self.term_types = term_types

    def __str__(self):
        ret = self.name + "(" + get_term_list_string(self.terms, self.term_types) + ")"
        return ret

    def get_pydatalog_string(self):
        ret = self.name + "("
        for idx, term in enumerate(self.terms):
            if self.term_types[idx] == DataTypes.SPAN:
                ret += term.get_pydatalog_string()
            elif self.term_types[idx] == DataTypes.STRING:
                # add the quotes so pyDatalog will read the value as a string, and not as a variable
                ret += '"' + term + '"'
            else:
                ret += str(term)
            if idx < len(self.terms) - 1:
                ret += ", "
        ret += ")"
        return ret


class IERelation:
    """a representation of an information extraction relation"""

    def __init__(self, name, input_terms, output_terms, input_term_types, output_term_types):
        assert len(input_terms) == len(input_term_types)
        assert len(output_terms) == len(output_term_types)
        self.name = name
        self.input_terms = input_terms
        self.output_terms = output_terms
        self.input_term_types = input_term_types
        self.output_term_types = output_term_types

    def __str__(self):
        ret = self.name + "(" + get_term_list_string(self.input_terms, self.input_term_types) + ")" + " -> " \
              + "(" + get_term_list_string(self.output_terms, self.output_term_types) + ")"
        return ret

    # get_pydatalog_string() is not implemented for this class as pyDatalog cannot handle IE relations


class RelationDeclaration:
    """a representation of a relation declaration"""

    def __init__(self, name, schema):
        self.name = name
        self.schema = schema

    def __str__(self):
        ret = self.name + "("
        for idx, term in enumerate(self.schema):
            if term == DataTypes.STRING:
                ret += 'str'
            elif term == DataTypes.SPAN:
                ret += 'spn'
            elif term == DataTypes.INT:
                ret += "int"
            else:
                assert 0
            if idx < len(self.schema) - 1:
                ret += ", "
        ret += ")"
        return ret
