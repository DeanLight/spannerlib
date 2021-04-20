class IEFunction:
    """
    A class that contains all the functions that provide data
    needed for using a single information extraction function
    """

    """
    Members: 
        ie_function_def : callable() - the user defined ie function implementation. 
        in_types        : iter()     - iterable of the input types to the function.  
        out_types       :            - either a function (int->iterable) or an iterable
    """

    def __init__(self, ie_function_def, in_types, out_types):
        self.ie_function_def = ie_function_def
        self.in_types = in_types
        self.out_types = out_types

    def ie_function(self, *args):
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
        # if not isinstance(output, collections.Iterable):
        #     return (output,)
        return output

    def get_input_types(self):
        """
        returns an iterable of the input types to the function
        This function must be defined as it is used for type checking in semantic passes and execution.
        """
        return self.in_types

    def get_output_types(self, output_arity):
        """
        given an expected output arity returns an iterable of the output types to the function.
        if the ie function cannot return an output of length output_arity, should return None.
        This function must be defined as it is used for type checking in semantic passes and execution.
        """

        if callable(self.out_types):
            return self.out_types(output_arity)

        # output is constant
        if not output_arity == len(self.out_types):
            raise Exception("Output arity doesn't match the declared arity.")
        return self.out_types
