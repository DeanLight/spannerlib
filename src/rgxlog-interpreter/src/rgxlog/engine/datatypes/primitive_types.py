"""
this module contains the 'DataTypes' enum that is used to represents the types of variables or terms in the ast,
term graph and symbol table

this module also contains class representations of complex datatypes (e.g. Span which is represented by two numbers)
"""

from enum import Enum
from typing import Union, Any


class DataTypes(Enum):
    """
    An enum class that represents the types of RGXLog
    """
    string = 0
    span = 1
    integer = 2
    free_var_name = 3
    var_name = 4

    def __str__(self) -> str:
        """
        @return: a string representation of a datatype.
        The string is also the same string used as a node type of said datatype in the grammar and passes
        e.g. a node that contains a Datatype.string value is of type "string" in the grammar and passes
        """
        return self.name

    @staticmethod
    def from_string(datatype_string: str) -> "DataTypes":
        """
        @return: a datatype enum representation of a string type.
        The string has to be the same string used as a node type of a datatype in the grammar and passes
        """
        try:
            return DataTypes[datatype_string]
        except Exception:
            # raise this exception instead of the default one as it is simpler to read
            raise Exception(f"invalid datatype string: {datatype_string}")


class Span:
    """A representation of a span"""

    def __init__(self, span_start: int, span_end: int):
        """
        @param span_start: the first (included) index of the span.
        @param span_end: the last (excluded) index of the span.
        """
        if not isinstance(span_start, int) and isinstance(span_end, int):
            raise TypeError("Span's start/end must be integers")
        self.span_start = span_start
        self.span_end = span_end

    def __str__(self) -> str:
        return f"[{self.span_start}, {self.span_end})"

    def __lt__(self, other: "Span") -> bool:
        if self.span_start == other.span_start:
            return self.span_end < other.span_end

        return self.span_start < other.span_start

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Span):
            return False
        return self.span_start == other.span_start and self.span_end == other.span_end

    # used for sorting `Span`s in dataframes
    def __hash__(self) -> int:
        return hash((self.span_start, self.span_end))


class DataTypeMapping:
    string = str
    span = Span
    integer = int
    free_var_name = str
    var_name = str
    term = Union[str, Span, int]
