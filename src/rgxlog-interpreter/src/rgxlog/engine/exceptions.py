# define Python user-defined exceptions
class CustomException(Exception):
    """Base class for other exceptions"""
    pass


class VariableNotDefinedError(CustomException):
    """Raised when a variable is not defined"""


class RelationNotDefinedError(CustomException):
    """Raised when a relation is not defined"""


class RelationRedefinitionError(CustomException):
    """Raised when a relation is redefined"""


class IncorrectArityError(CustomException):
    """Raised when an incorrect arity is used for relations/ie function calls"""


class RuleNotSafeError(CustomException):
    """Raised when a rule is not safe"""
    pass


class TermsNotProperlyTypedError(CustomException):
    """Raised when a term type in a term sequence does not match the schema's attribute type on the same index"""
    pass


class FreeVariableTypeConflictError(CustomException):
    """Raised when a free variable has more than one type"""
    pass
