from rgxlog.engine.session import Session




# TODO add tests
def test_introduction():

    EXPECTED_RESULT_INTRO = """printing results for query 'uncle(X, Y)':
      X  |  Y
    -----+------
     bob | greg
    """

    session = Session()
    session.run_query("new uncle(str, str)")
    session.run_query('uncle("bob", "greg")')
    query_result = session.run_query("?uncle(X,Y)")
    assert query_result == EXPECTED_RESULT_INTRO,"fail"


def test_basic_queries():
    EXPECTED_RESULT = '''
    printing results for query 'enrolled_in_chemistry("jordan")':
    [()]
    
    printing results for query 'enrolled_in_chemistry("gale")':
    []
    
    printing results for query 'enrolled_in_chemistry(X)':
        X
    ---------
     howard
     abigail
     jordan
    
    printing results for query 'enrolled_in_physics_and_chemistry(X)':
       X
    --------
     howard
    '''

    session = Session()
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
       ?enrolled_in_physics_and_chemistry(X)'''
    query_result = session.run_query(query)
    assert query_result == EXPECTED_RESULT, "fail"

def test_string_rgx():
    EXPECTED_RESULT =

    def rgx_string(text, regex_formula):
        import re
        '''
        Args:
            text: The input text for the regex operation
            regex_formula: the formula of the regex operation

        Returns: tuples of strings that represents the results
        '''
        compiled_rgx = re.compile(regex_formula)
        num_groups = compiled_rgx.groups
        for match in re.finditer(compiled_rgx, text):
            if num_groups == 0:
                matched_strings = [match.group()]
            else:
                matched_strings = [group for group in match.groups()]
            yield matched_strings


    def rgx_string_out_types(output_arity):
        return tuple([DataTypes.string] * output_arity)


    rgx_string_in_type = [DataTypes.string, DataTypes.string]


    session = Session()
    session.register(rgx_string, 'MYRGXString', rgx_string_in_type, rgx_string_out_types, False)
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
    
    gpa_str = "abigail 100 jordan 80 gale 79 howard 60"
    gpa_of_chemistry_students(Student, Grade) <- MYRGXString(gpa_str, "(\w+).*?(\d+)")->(Student, Grade), enrolled_in_chemistry(Student)
    ?gpa_of_chemistry_students(X, "100")'''

    query_result = session.run_query(query)
    assert query_result == EXPECTED_RESULT, "fail"
