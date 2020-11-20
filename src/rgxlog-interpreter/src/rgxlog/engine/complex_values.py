from rgxlog.engine.datatypes import DataTypes


def get_term_list_string(term_list, type_list):
    """
    returns a string representation of the term list.
    quotes are added to string terms so they will not be confused with variables.
    """
    terms_with_quoted_strings = [f"\"{term}\"" if term_type is DataTypes.string
                                 else str(term)
                                 for term, term_type in zip(term_list, type_list)]
    term_list_string = ', '.join(terms_with_quoted_strings)
    return term_list_string


class Span:
    """A representation of a span"""

    def __init__(self, span_start, span_end):
        """
        Args:
            span_start: the first (included) index of the span
            span_end: the last (excluded) index of the span
        """
        self.span_start = span_start
        self.span_end = span_end

    def __str__(self):
        return f"[{self.span_start}, {self.span_end})"

    def get_pydatalog_string(self):
        """
        the pyDatalog execution engine receives instructions via strings.
        return a string representation of a span term in pyDatalog.
        since there's no built in representation of a span in pyDatalog, and custom classes do not seem to work
        as intended in pyDatalog, we represent a span using a tuple of length 2.
        """
        return f"({self.span_start}, {self.span_end})"


class Relation:
    """a representation of a normal relation"""

    def __init__(self, name, term_list, type_list):
        """
        Args:
            name: the name of the relation
            term_list: a list of the relation terms. must be either literal values or free variables
            type_list: a list of the relation term types.
        """
        if len(term_list) != len(type_list):
            raise Exception(f"received different lengths of term_list ({len(term_list)}) "
                            f"and type_list ({len(type_list)})")
        self.name = name
        self.term_list = term_list
        self.type_list = type_list

    def __str__(self):
        term_list_string = get_term_list_string(self.term_list, self.type_list)
        relation_string = f"{self.name}({term_list_string})"
        return relation_string

    def get_pydatalog_string(self):
        """
        the pyDatalog execution engine receives instructions via strings.
        return a relation representation of a span term in pyDatalog.
        quotes are added to string terms so pyDatalog will not be confused between strings and variables.
        spans are represented as tuples of length 2 (see get_pydatalog_string() of the Span class)
        """
        pydatalog_string_terms = \
            [f"\"{term}\"" if term_type is DataTypes.string
             else term.get_pydatalog_string() if term_type is DataTypes.span
             else str(term)
             for term, term_type in zip(self.term_list, self.type_list)]
        term_list_pydatalog_string = ', '.join(pydatalog_string_terms)
        relation_pydatalog_string = f"{self.name}({term_list_pydatalog_string})"
        return relation_pydatalog_string


class IERelation:
    """
    a representation of an information extraction (ie) relation.
    An information extraction relation is different than a normal relation as it is constructed from
    the results of a call to an information extraction function.

    The ie relation instructs us on how to construct it:
    * its name is the ie function we need to call
    * its input term list represents a relation where each tuple is an argument list to call the ie function with.
    * its output term list represents a relation that filters the tuples that are returned from the ie function
    calls, and matches the values inside the tuples to free variables.
    """

    def __init__(self, name, input_term_list, output_term_list, input_type_list, output_type_list):
        """
        Args:
            name: the name of the information extraction relation
            input_term_list: a list of the input terms for the ie function.
            must be either literal values or free variables
            output_term_list: a list of the output terms for the ie function.
            must be either literal values or free variables
            input_type_list: a list of the term types in input_term_list
            output_type_list: a list of the term types in output_term_list
        """
        if len(input_term_list) != len(input_type_list):
            raise Exception(f"received different lengths of input_term_list ({len(input_term_list)}) "
                            f"and input_type_list ({len(input_type_list)})")
        if len(output_term_list) != len(output_type_list):
            raise Exception(f"received different lengths of output_term_list ({len(output_term_list)}) "
                            f"and output_type_list ({len(output_type_list)})")
        self.name = name
        self.input_term_list = input_term_list
        self.output_term_list = output_term_list
        self.input_type_list = input_type_list
        self.output_type_list = output_type_list

    def __str__(self):
        input_term_list_string = get_term_list_string(self.input_term_list, self.input_type_list)
        output_term_list_string = get_term_list_string(self.output_term_list, self.output_type_list)
        ie_relation_string = f"{self.name}({input_term_list_string}) -> ({output_term_list_string})"
        return ie_relation_string

    # get_pydatalog_string() is not implemented for this class as pyDatalog cannot handle IE relations


class RelationDeclaration:
    """a representation of a relation declaration"""

    def __init__(self, name, type_list):
        """
        Args:
            name: the name of the relation
            type_list: a list of the types of the terms in the relation's tuples
        """
        self.name = name
        self.type_list = type_list

    def __str__(self):
        type_strings = []
        for term_type in self.type_list:
            if term_type is DataTypes.string:
                type_strings.append('str')
            elif term_type is DataTypes.span:
                type_strings.append('spn')
            elif term_type is DataTypes.integer:
                type_strings.append('int')
            else:
                raise Exception(f"invalid term type ({term_type})")
        type_list_string = ', '.join(type_strings)
        relation_declaration_string = f"{self.name}({type_list_string})"
        return relation_declaration_string

    # get_pydatalog_string() is not implemented for this class as relations are not declared in pyDatalog
    # we use a different workaround in pydatalog which is adding and removing a made up tuple in order to create
    # an empty relation.
