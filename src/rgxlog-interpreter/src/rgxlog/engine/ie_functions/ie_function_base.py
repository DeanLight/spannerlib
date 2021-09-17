from typing import Iterable, Callable, Union, Tuple, List

from rgxlog.engine.datatypes.primitive_types import DataTypes


class IEFunction:
    """
    A class that contains all the functions that provide data
    needed for using a single information extraction function
    """

    def __init__(self, ie_function_def: Callable, in_types: Iterable[DataTypes],
                 out_types: Union[List[DataTypes], Callable[[int], Iterable[DataTypes]]]):
        """
        @param ie_function_def : the user defined ie function implementation.
        @param in_types        : iterable of the input types to the function.
        @param out_types       :  either a function (int->iterable) or an iterable
        """
        self.ie_function_def = ie_function_def
        self.in_types = in_types
        self.out_types = out_types

    def ie_function(self, *args) -> Iterable[Iterable[Union[str, int, Tuple[int, int]]]]:   # Tuple[int, int] represents a Span
        """
        The actual information extraction function that will be used
        the function must return a list of lists/tuples that represents the results, another option is to yield the
        tuples.

        currently the values inside the returned tuples can belong to three datatypes: string, integer and span
        string should be returned as a str instance
        an integer should be returned as an int instance
        a span could be returned either as a tuple of length 2, or as a datatypes.Span instance
        """
        output = self.ie_function_def(*args)
        return output

    def get_input_types(self) -> Iterable[DataTypes]:
        """
        @return: an iterable of the input types to the function
        This function must be defined as it is used for type checking in semantic passes and execution.
        """
        return self.in_types

    def get_output_types(self, output_arity: int) -> List[DataTypes]:
        """
        @return: given an expected output arity returns an iterable of the output types to the function.
        if the ie function cannot return an output of length output_arity, should return None.
        This function must be defined as it is used for type checking in semantic passes and execution.
        """

        if callable(self.out_types):
            return self.out_types(output_arity)

        # output is constant
        if not output_arity == len(list(self.out_types)):
            raise Exception("Output arity doesn't match the declared arity.")
        return self.out_types

    def get_meta_data(self) -> str:
        """
        @return: metadata about the ie function.
        """
        metadata = f"""Input types: {self.in_types}.\nOutput types: {self.out_types}"""
        return metadata
