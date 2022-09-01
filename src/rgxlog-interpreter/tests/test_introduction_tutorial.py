from typing import Iterable, Any, Tuple

from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.engine.utils.general_utils import QUERY_RESULT_PREFIX
from tests.utils import run_test


def test_strings_query() -> None:
    commands = """
    new uncle(str, str)
    uncle("bob", "greg")
    ?uncle(X,Y)
    """

    expected_result_intro = f"""{QUERY_RESULT_PREFIX}'uncle(X, Y)':
          X  |  Y
        -----+------
         bob | greg
        """

    run_test(commands, expected_result_intro)


def test_basic_queries() -> None:
    commands = '''
            new lecturer(str, str)
            lecturer("walter", "chemistry")
            lecturer("linus", "operation systems")
            lecturer("rick", "physics")

            new enrolled(str, str)
            enrolled("abigail", "chemistry")
            enrolled("abigail", "operation systems")
            enrolled("jordan", "chemistry")
            enrolled("gale", "operation systems")
            enrolled("howard", "chemistry")
            enrolled("howard", "physics")

            enrolled_in_chemistry(X) <- enrolled(X, "chemistry")
            ?enrolled_in_chemistry("jordan")
            ?enrolled_in_chemistry("gale")
            ?enrolled_in_chemistry(X)

            enrolled_in_physics_and_chemistry(X) <- enrolled(X, "chemistry"), enrolled(X, "physics")
            ?enrolled_in_physics_and_chemistry(X)

            lecturer_of(X, Z) <- lecturer(X, Y), enrolled(Z, Y)
            ?lecturer_of(X, "abigail")
            '''

    expected_result = f"""{QUERY_RESULT_PREFIX}'enrolled_in_chemistry("jordan")':
        [()]

        {QUERY_RESULT_PREFIX}'enrolled_in_chemistry("gale")':
        []

        {QUERY_RESULT_PREFIX}'enrolled_in_chemistry(X)':
            X
        ---------
         howard
         jordan
         abigail

        {QUERY_RESULT_PREFIX}'enrolled_in_physics_and_chemistry(X)':
           X
        --------
         howard

        {QUERY_RESULT_PREFIX}'lecturer_of(X, "abigail")':
           X
        --------
         linus
         walter
        """

    session = run_test(commands, expected_result)

    commands2 = (r"""gpa_str = "abigail 100 jordan 80 gale 79 howard 60"
                gpa_of_chemistry_students(Student, Grade) <- py_rgx_string(gpa_str, "(\w+).*?(\d+)")"""
                 r"""->(Student, Grade), enrolled_in_chemistry(Student)
               ?gpa_of_chemistry_students(X, "100")""")

    expected_result2 = f"""{QUERY_RESULT_PREFIX}'gpa_of_chemistry_students(X, "100")':
            X
        ---------
         abigail
        """

    run_test(commands2, expected_result2, session=session)


def test_json_path() -> None:
    commands = """
                jsonpath_simple_1 = "foo[*].baz"
                json_ds_simple_1  = "{'foo': [{'baz': 1}, {'baz': 2}]}"
                simple_1(X) <- JsonPath(json_ds_simple_1, jsonpath_simple_1) -> (X)
                ?simple_1(X)

                jsonpath_simple_2 = "a.*.b.`parent`.c"
                json_ds_simple_2 = "{'a': {'x': {'b': 1, 'c': 'number one'}, 'y': {'b': 2, 'c': 'number two'}}}"

                simple_2(X) <- JsonPath(json_ds_simple_2, jsonpath_simple_2) -> (X)
                ?simple_2(X)

                json_ds_advanced  = "{'foo': [{'baz': 1}, {'baz': {'foo': [{'baz': 1}, {'baz': 2}]}}]}"
                advanced(X) <- JsonPath(json_ds_advanced, jsonpath_simple_1) -> (X)
                ?advanced(X)
            """

    expected_result = (
        f"""{QUERY_RESULT_PREFIX}'simple_1(X)':
           X
        -----
           2
           1

        {QUERY_RESULT_PREFIX}'simple_2(X)':
             X
        ------------
         number two
         number one

        {QUERY_RESULT_PREFIX}'advanced(X)':"""
        """
                             X
            -----------------------------------
             {'foo': [{'baz': 1}, {'baz': 2}]}
                             1
        """)

    run_test(commands, expected_result)


def test_remove_rule() -> None:
    commands = """
           new parent(str, str)
           new grandparent(str, str)
           parent("Liam", "Noah")
           parent("Noah", "Oliver")
           parent("James", "Lucas")
           parent("Noah", "Benjamin")
           parent("Benjamin", "Mason")
           grandparent("Tom", "Avi")
           ancestor(X,Y) <- parent(X,Y)
           ancestor(X,Y) <- grandparent(X,Y)
           ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y)

           tmp(X, Y) <- ancestor(X,Y)
           tmp(X, Y) <- parent(X,Y)
           """

    session = run_test(commands)

    session.remove_rule("ancestor(X, Y) <- parent(X, Y)")
    commands = """
            ?ancestor(X, Y)
            ?tmp(X, Y)
          """

    expected_result = f"""{QUERY_RESULT_PREFIX}'ancestor(X, Y)':
              X  |  Y
            -----+-----
             Tom | Avi

            {QUERY_RESULT_PREFIX}'tmp(X, Y)':
                X     |    Y
            ----------+----------
             Benjamin |  Mason
               Noah   | Benjamin
              James   |  Lucas
               Noah   |  Oliver
               Liam   |   Noah
               Tom    |   Avi
            """

    run_test(commands, expected_result, session=session)


def test_issue_80_len() -> None:
    def length(string: str) -> int:
        # here we append the input to the output inside the ie function!
        yield len(string)

    length_dict = dict(ie_function=length,
                       ie_function_name='Length',
                       in_rel=[DataTypes.string],
                       out_rel=[DataTypes.integer, DataTypes.string])

    commands = """new string(str)
            string("a")
            string("d")
            string("a")
            string("ab")
            string("abc")
            string("abcd")

            string_length(Str, Len) <- string(Str), Length(Str) -> (Len)
            ?string_length(Str, Len)
            """

    expected_result = f"""{QUERY_RESULT_PREFIX}'string_length(Str, Len)':
          Str  |   Len
        -------+-------
           a   |     1
           d   |     1
          ab   |     2
          abc  |     3
         abcd  |     4
        """

    run_test(commands, expected_result, [length_dict])


def test_neq() -> None:
    def neq(x: Any, y: Any) -> Iterable:
        if x == y:
            # return false
            yield tuple()
        else:
            # return true
            yield x, y

    in_out_types = [DataTypes.string, DataTypes.string]
    neq_dict = dict(ie_function=neq,
                    ie_function_name='NEQ',
                    in_rel=in_out_types,
                    out_rel=in_out_types)
    commands = """new pair(str, str)
                pair("Dan", "Tom")
                pair("Cat", "Dog")
                pair("Apple", "Apple")
                pair("Cow", "Cow")
                pair("123", "321")

                unique_pair(X, Y) <- pair(First, Second), NEQ(First, Second) -> (X, Y)
                ?unique_pair(X, Y)
                """

    expected_result = f"""{QUERY_RESULT_PREFIX}'unique_pair(X, Y)':
          X  |  Y
        -----+-----
         Dan | Tom
         Cat | Dog
         123 | 321
        """

    run_test(commands, expected_result, [neq_dict])


def test_span_constant() -> None:
    commands = '''
            new verb(str, span)
            verb("Ron eats quickly.", [4,8))
            verb("You write neatly.", [4,9))
            ?verb(X,[4,9)) # returns "You write neatly."
            '''

    expected_result = f"""{QUERY_RESULT_PREFIX}'verb(X, [4, 9))':
                                 X
                        -------------------
                         You write neatly."""

    run_test(commands, expected_result)
