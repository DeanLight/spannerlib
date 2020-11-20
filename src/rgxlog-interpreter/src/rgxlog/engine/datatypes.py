from enum import Enum


class DataTypes(Enum):
    """
    An enum class that represents the types of RGXLog
    """
    string = 0
    span = 1
    int = 2
    free_var_name = 3

    def to_string(self):
        """
        returns a string representation of a datatype.
        The string is also the same string used as a node type of said datatype in the grammar and passes
        e.g. a node that contains a Datatype.string value is of type "string" in the grammar and passes
        """
        return self.name

    @staticmethod
    def from_string(datatype_string):
        """
        returns a datatype enum representation of a string type.
        The string has to be the same string used as a node type of a datatype in the grammar and passes
        """
        try:
            return DataTypes[datatype_string]
        except Exception:
            # raise this exception instead of the default one as it is simpler to read
            raise Exception(f"invalid datatype string: {datatype_string}")
