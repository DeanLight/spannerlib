import re
from abc import abstractmethod, ABC
from rgxlog.engine.datatypes import DataTypes


class IEFunctionData(ABC):
    """
    A class that contains all the functions that provide data
    needed for using a single information extraction function
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    @abstractmethod
    def ie_function(*args):
        """The actual ie function that will be used"""
        pass

    @staticmethod
    @abstractmethod
    def get_input_types():
        """
        returns an iterable of the input types to the function
        This function must be defined as it is used for type checking in semantic passes and execution.
        """
        pass

    @staticmethod
    @abstractmethod
    def get_output_types(output_arity):
        """
        given an expected output arity returns an iterable of the output types to the function.
        if the ie function cannot return an output of length output_arity, should return None.
        This function must be defined as it is used for type checking in semantic passes and execution.
        """
        """
        TODO instead of making the user implement this function, allow the user to use a regular expression
        to define this function. The semantic pass will use said regex and the expected output arity to get the
        expected output types.
        for example for the RGX ie function, the output types regex will be spn*.
        Then, for the call RGX(s1,s2)->(X,Y,Z,W), the semantic pass / execution will use the regex spn* to determine
        the expected output types to be [spn,spn,spn,spn]
        """
        pass


class RGX(IEFunctionData):
    """
    Performs a regex information extraction.
    Results are tuples of spans
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    def ie_function(text, regex_formula):
        """
        Args:
            text: The input text for the regex operation
            regex_formula: the formula of the regex operation

        Returns: tuples of spans that represents the results
        """
        compiled_rgx = re.compile(regex_formula)
        num_groups = compiled_rgx.groups
        for match in re.finditer(compiled_rgx, text):
            if num_groups == 0:
                matched_spans = [match.span()]
            else:
                matched_spans = [match.span(i) for i in range(1, num_groups + 1)]
            yield matched_spans

    @staticmethod
    def get_input_types():
        return DataTypes.STRING, DataTypes.STRING

    @staticmethod
    def get_output_types(output_arity):
        return tuple([DataTypes.SPAN] * output_arity)


class RGXString(IEFunctionData):
    """
    Performs a regex information extraction.
    Results are tuples of strings
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    def ie_function(text, regex_formula):
        """
        Args:
            text: The input text for the regex operation
            regex_formula: the formula of the regex operation

        Returns: tuples of strings that represents the results
        """
        compiled_rgx = re.compile(regex_formula)
        num_groups = compiled_rgx.groups
        for match in re.finditer(compiled_rgx, text):
            if num_groups == 0:
                matched_strings = [match.group()]
            else:
                matched_strings = [group for group in match.groups()]
            yield matched_strings

    @staticmethod
    def get_input_types():
        return DataTypes.STRING, DataTypes.STRING

    @staticmethod
    def get_output_types(output_arity):
        return tuple([DataTypes.STRING] * output_arity)
