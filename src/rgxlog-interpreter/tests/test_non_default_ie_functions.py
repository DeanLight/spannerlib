from rgxlog.engine.datatypes.primitive_types import DataTypes, Span
from tests.utils import run_test


def test_range_int_no_tuple():
    def yield_range_int_no_tuple(num):
        for i in range(num):
            yield i

    yield_range_int_no_tuple_in_types = [DataTypes.integer]
    yield_range_int_no_tuple_out_types = [DataTypes.integer]
    yield_range_dict = {"ie_function": yield_range_int_no_tuple,
                        "ie_function_name": "yield_range_int_no_tuple",
                        "in_rel": yield_range_int_no_tuple_in_types,
                        "out_rel": yield_range_int_no_tuple_out_types}

    query = """
        test_range_int_no_tuple(X) <- yield_range_int_no_tuple(5) -> (X)
        ?test_range_int_no_tuple(X)
        """

    expected_result = """printing results for query 'test_range_int_no_tuple(X)':
                            X
                            -----
                            4
                            3
                            2
                            1
                            0"""

    run_test(query, expected_result, functions_to_import=[yield_range_dict])


def test_range_span_no_tuple():
    def yield_range_span_no_tuple(num):
        for i in range(num):
            yield Span(i, i)

    yield_range_span_no_tuple_in_types = [DataTypes.integer]
    yield_range_span_no_tuple_out_types = [DataTypes.span]
    yield_range_span_dict = {"ie_function": yield_range_span_no_tuple,
                             "ie_function_name": "yield_range_span_no_tuple",
                             "in_rel": yield_range_span_no_tuple_in_types,
                             "out_rel": yield_range_span_no_tuple_out_types}

    query = """
        test_range_span_no_tuple(X) <- yield_range_span_no_tuple(5) -> (X)
        ?test_range_span_no_tuple(X)
        """

    expected_result = """printing results for query 'test_range_span_no_tuple(X)':
                           X
                        --------
                         [4, 4)
                         [3, 3)
                         [2, 2)
                         [1, 1)
                         [0, 0)"""

    run_test(query, expected_result, functions_to_import=[yield_range_span_dict])


def test_range_str_no_tuple():
    def yield_range_str_no_tuple(num):
        for i in range(num):
            yield "string" + str(i)

    yield_range_str_no_tuple_in_types = [DataTypes.integer]
    yield_range_str_no_tuple_out_types = [DataTypes.string]
    yield_range_str_dict = {"ie_function": yield_range_str_no_tuple,
                            "ie_function_name": "yield_range_str_no_tuple",
                            "in_rel": yield_range_str_no_tuple_in_types,
                            "out_rel": yield_range_str_no_tuple_out_types}

    query = """
        test_range_str_no_tuple(X) <- yield_range_str_no_tuple(5) -> (X)
        ?test_range_str_no_tuple(X)
        """

    expected_result = """printing results for query 'test_range_str_no_tuple(X)':
                            X
                        ---------
                         string4
                         string3
                         string2
                         string1
                         string0"""

    run_test(query, expected_result, functions_to_import=[yield_range_str_dict])


def test_range_int_with_tuple():
    """
    in this test, a tuple of an integer is treated as an integer
    @return:
    """

    def yield_range_int_with_tuple(num):
        for i in range(num):
            yield (i,)

    yield_range_int_with_tuple_in_types = [DataTypes.integer]
    yield_range_int_with_tuple_out_types = [DataTypes.integer]
    yield_range_dict = {"ie_function": yield_range_int_with_tuple,
                        "ie_function_name": "yield_range_int_with_tuple",
                        "in_rel": yield_range_int_with_tuple_in_types,
                        "out_rel": yield_range_int_with_tuple_out_types}

    query = """
        test_range_int_with_tuple(X) <- yield_range_int_with_tuple(5) -> (X)
        ?test_range_int_with_tuple(X)
        """

    expected_result = """printing results for query 'test_range_int_with_tuple(X)':
                            X
                            -----
                            4
                            3
                            2
                            1
                            0"""

    run_test(query, expected_result, functions_to_import=[yield_range_dict])
