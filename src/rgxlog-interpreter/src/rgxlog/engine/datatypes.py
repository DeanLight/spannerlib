from enum import Enum


class DataTypes(Enum):
    STRING = 0
    SPAN = 1
    INT = 2
    FREE_VAR = 3


def get_datatype_string(datatype_enum):
    """
    returns a string representation of a datatype.
    The string is also the same string used as a node type of said datatype in the grammar and passes
    e.g. a node that contains a Datatype.STRING value is of type "string" in the grammar and passes
    """
    if datatype_enum == DataTypes.STRING:
        return "string"
    elif datatype_enum == DataTypes.SPAN:
        return "span"
    elif datatype_enum == DataTypes.INT:
        return "integer"
    elif datatype_enum == DataTypes.FREE_VAR:
        return "free_var_name"
    else:
        assert 0


def get_datatype_enum(datatype_string):
    """
    returns a datatype enum representation of a string type.
    The string has to be the same string used as a node type of a datatype in the grammar and passes
    """
    if datatype_string == "string":
        return DataTypes.STRING
    elif datatype_string == "span":
        return DataTypes.SPAN
    elif datatype_string == "integer":
        return DataTypes.INT
    elif datatype_string == "free_var_name":
        return DataTypes.FREE_VAR
    else:
        assert 0
