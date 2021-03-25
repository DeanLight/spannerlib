
"""
Instead of creating a separate class for every user defined ie function we will adjust IEFunctionData class.
Every abstract method will become a class member.
It allows us to use this class for all ie functions by passing different parameters to the init method.
"""

"""
    class IEFunctionData:
        def __init__(self, ie_function : callable(), get_input_types : callable(), get_output_types : callable()):
            pass
"""




"""
this module contains the 'IEFunctionData' class: an abstraction for classes that contain all the
information needed to semantic check and execute an information extraction function
"""

from abc import abstractmethod, ABC


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
        """
        The actual information extraction function that will be used
        the function must return a list of lists/tuples that represents the results, another option is to yield the
        tuples.

        currently the values inside the returned tuples can belong to three datatypes: string, integer and span
        string should be returned as a str instance
        an integer should be returned as an int instance
        a span could be returned either as a tuple of length 2, or as a datatypes.Span instance
        """
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
