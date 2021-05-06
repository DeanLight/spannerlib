from rgxlog.engine.session import Session, query_to_string
from tests.utils import compare_strings, run_query_assert_output


def test_introduction():
    session = Session()
    expected_result_intro = """printing results for query 'uncle(X, Y)':
          X  |  Y
        -----+------
         bob | greg
        """

    pre_query = """new uncle(str, str)
                   uncle("bob", "greg")
                   """

    query = "?uncle(X,Y)"

    run_query_assert_output(session, query, expected_result_intro, pre_query)


def test_basic_queries():
    from rgxlog.stdlib.python_regex import PYRGX_STRING
    expected_result = """printing results for query 'enrolled_in_chemistry("jordan")':
        [()]
        
        printing results for query 'enrolled_in_chemistry("gale")':
        []
        
        printing results for query 'enrolled_in_chemistry(X)':
            X
        ---------
         howard
         jordan
         abigail
        
        printing results for query 'enrolled_in_physics_and_chemistry(X)':
           X
        --------
         howard
        
        printing results for query 'lecturer_of(X, "abigail")':
           X
        --------
         linus
         walter
        """

    query = '''
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

    session = Session()
    run_query_assert_output(session, query, expected_result)
    expected_result2 = """printing results for query 'gpa_of_chemistry_students(X, "100")':
        X
    ---------
     abigail
    """

    query2 = (r"""gpa_str = "abigail 100 jordan 80 gale 79 howard 60"
            gpa_of_chemistry_students(Student, Grade) <- RGXString(gpa_str, "(\w+).*?(\d+)")"""
              r"""->(Student, Grade), enrolled_in_chemistry(Student)
            ?gpa_of_chemistry_students(X, "100")""")

    session.register(**PYRGX_STRING)
    run_query_assert_output(session, query2, expected_result2)


def test_recursive():
    expected_result = """printing results for query 'ancestor("Liam", X)':
        X
    ----------
      Mason
      Oliver
     Benjamin
       Noah
    
    printing results for query 'ancestor(X, "Mason")':
        X
    ----------
       Noah
       Liam
     Benjamin
    
    printing results for query 'ancestor("Mason", X)':
    []
    """

    query = '''
        new parent(str, str)
        parent("Liam", "Noah")
        parent("Noah", "Oliver")
        parent("James", "Lucas")
        parent("Noah", "Benjamin")
        parent("Benjamin", "Mason")
        ancestor(X,Y) <- parent(X,Y)
        ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y)
        
        ?ancestor("Liam", X)
        ?ancestor(X, "Mason")
        ?ancestor("Mason", X)
        '''

    session = Session()
    run_query_assert_output(session, query, expected_result)


def test_json_path():
    from rgxlog.stdlib.json_path import JsonPath

    expected_result = """printing results for query 'simple_1(X)':
           X
        -----
           2
           1
        
        printing results for query 'simple_2(X)':
             X
        ------------
         number two
         number one
        
        printing results for query 'advanced(X)':
                         X
        -----------------------------------
         {'foo': [{'baz': 1}, {'baz': 2}]}
                         1
    """

    query = """
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

    session = Session()
    session.register(**JsonPath)

    run_query_assert_output(session, query, expected_result)


def test_remove_rule():
    expected_result = """printing results for query 'ancestor(X, Y)':
      X  |  Y
    -----+-----
     Tom | Avi
    
    printing results for query 'tmp(X, Y)':
        X     |    Y
    ----------+----------
     Benjamin |  Mason
       Noah   | Benjamin
      James   |  Lucas
       Noah   |  Oliver
       Liam   |   Noah
       Tom    |   Avi
    """

    query = """
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

    session = Session()
    session.run_query(query, print_results=False)

    session.remove_rule("ancestor(X,Y) <- parent(X,Y)")
    query = """
            ?ancestor(X, Y)
            ?tmp(X, Y)
          """
    query_result = session.run_query(query, print_results=False)
    query_result_string = query_to_string(query_result)
    assert compare_strings(expected_result, query_result_string), "fail"
