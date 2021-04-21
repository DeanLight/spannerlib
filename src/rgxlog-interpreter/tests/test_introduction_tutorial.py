from typing import Tuple
from rgxlog.engine.session import Session
from rgxlog.engine.datatypes.primitive_types import DataTypes


def compare_relations(actual: list, output:list) -> bool:
    if len(actual) != len(output):
        return False
    for rel in actual:
        if output.count(rel) == 0:
            return False

    return True

def str_relation_to_list(table: str, start: int) -> Tuple[list, int]:
    offset_cnt = 0
    relations = list()
    for rel in table[start:]:
        offset_cnt += 1
        relations.append(rel)
        if rel == "\n":
            break

    return relations, offset_cnt


def compare_strings(actual: str, test_output: str) -> bool:
    actual_lines = actual.splitlines(True)
    output_lines = test_output.splitlines(True)
    actual_lines = [line.strip() for line in actual_lines if len(line.strip()) > 0]
    output_lines = [line.strip() for line in output_lines if len(line.strip()) > 0]
    if len(actual_lines) != len(output_lines):
        return False

    i = 0
    while i < len(actual_lines):
        rng = 3
        if actual_lines[i + 1] in ["[()]\n", "[]\n"]:
            rng = 2
        for j in range(rng):
            if actual_lines[i + j] != output_lines[i + j]:
                return False
        i += rng
        actual_rel, offset = str_relation_to_list(actual_lines, i)
        output_rel, _ = str_relation_to_list(output_lines, i)
        if not compare_relations(actual_rel, output_rel):
            return False
        i += offset

    return True


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
    assert compare_strings(EXPECTED_RESULT_INTRO, query_result), "fail"


def test_basic_queries():
    from rgxlog.stdlib.regex import RGXString
    EXPECTED_RESULT = """printing results for query 'enrolled_in_chemistry("jordan")':
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
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"

    EXPECTED_RESULT_2 = """printing results for query 'gpa_of_chemistry_students(X, "100")':
    X
---------
 abigail
"""

    session.register(**RGXString)

    query = """gpa_str = "abigail 100 jordan 80 gale 79 howard 60"
            gpa_of_chemistry_students(Student, Grade) <- RGXString(gpa_str, "(\w+).*?(\d+)")->(Student, Grade), enrolled_in_chemistry(Student)
            ?gpa_of_chemistry_students(X, "100")"""

    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT_2, query_result), "fail"


def test_entities():
    from rgxlog.stdlib.nlp import Entities

    EXPECTED_RESULT = """printing results for query 'entities(Entity, Classification)':
   Entity    |            Classification
-------------+---------------------------------------
    today    | Absolute or relative dates or periods
 Baudrillard |      People, including fictional
     Neo     |      People, including fictional
"""

    query = '''
                    text = "You've been living in a dream world, Neo.\
                            As in Baudrillard's vision, your whole life has been spent inside the map, not the territory.\
                            This is the world as it exists today.\
                            Welcome to the desert of the real."
                    entities(Entity, Classification) <- Entities(text)->(Entity, Classification)
                    ?entities(Entity, Classification)
                    '''

    session = Session()
    session.register(**Entities)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_recursive():
    EXPECTED_RESULT = """printing results for query 'ancestor("Liam", X)':
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
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_json_path():
    from rgxlog.stdlib.json_path import json_path

    EXPECTED_RESULT = """printing results for query 'simple_1(X)':
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
    session.register(**json_path)

    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_tokenize():
    from rgxlog.stdlib.nlp import Tokenize

    EXPECTED_RESULT = """printing results for query 'tokens(Token, Span)':
  Token  |   Span
---------+----------
    .    | [30, 31)
  again  | [25, 30)
  world  | [19, 24)
  Hello  | [13, 18)
    .    | [11, 12)
  world  | [6, 11)
  Hello  |  [0, 5)
"""

    query = """
                sentence = "Hello world. Hello world again."
                tokens(X, Y) <- Tokenize(sentence) -> (X, Y)
                ?tokens(Token, Span)
            """

    session = Session()
    session.register(**Tokenize)

    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_ssplit():
    from rgxlog.stdlib.nlp import SSplit
    EXPECTED_RESULT = """printing results for query 'sentences(Sentences)':
      Sentences
---------------------
 Hello world again .
    Hello world .
"""

    query = """
                    sentence = "Hello world. Hello world again."
                    sentences(X) <- SSplit(sentence) -> (X)
                    ?sentences(Sentences)
            """

    session = Session()
    session.register(**SSplit)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_pos():
    from rgxlog.stdlib.nlp import POS
    EXPECTED_RESULT = """printing results for query 'pos(Token, POS, Span)':
  Token  |  POS  |   Span
---------+-------+----------
    .    |   .   | [23, 24)
  Paris  |  NNP  | [18, 23)
   in    |  IN   | [15, 17)
  born   |  VBN  | [10, 14)
   was   |  VBD  |  [6, 9)
  Marie  |  NNP  |  [0, 5)
"""

    query = """
                        sentence = "Marie was born in Paris."
                        pos(X, Y, Z) <- POS(sentence) -> (X, Y, Z)
                        ?pos(Token, POS, Span)
                    """

    session = Session()
    session.register(**POS)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_lemma():
    from rgxlog.stdlib.nlp import Lemma
    EXPECTED_RESULT = """printing results for query 'lemma(Token, Lemma, Span)':
  Token  |  Lemma  |   Span
---------+---------+----------
    .    |    .    | [46, 47)
 inside  | inside  | [40, 46)
 nothing | nothing | [32, 39)
   's    |   be    | [29, 31)
  there  |  there  | [24, 29)
    ,    |    ,    | [22, 23)
   lie   |   lie   | [19, 22)
    a    |    a    | [17, 18)
 living  |  live   | [10, 16)
  been   |   be    |  [5, 9)
   've   |  have   |  [1, 4)
    I    |    I    |  [0, 1)
"""

    query = """
            sentence = "I've been living a lie, there's nothing inside."
            lemma(X, Y, Z) <- Lemma(sentence) -> (X, Y, Z)
            ?lemma(Token, Lemma, Span)
             """
    session = Session()
    session.register(**Lemma)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_ner():
    from rgxlog.stdlib.nlp import NER
    EXPECTED_RESULT = """printing results for query 'ner(Token, NER, Span)':
   Token   |     NER      |    Span
-----------+--------------+------------
  Journal  | ORGANIZATION | [116, 123)
  Street   | ORGANIZATION | [109, 115)
   Wall    | ORGANIZATION | [104, 108)
  Lagarde  |    PERSON    |  [27, 34)
 Christine |    PERSON    |  [17, 26)
  France   |   COUNTRY    |  [9, 15)
"""

    query = """
                sentence = "While in France, Christine Lagarde discussed short-term stimulus efforts in a recent interview with the Wall Street Journal."
                ner(X, Y, Z) <- NER(sentence) -> (X, Y, Z)
                ?ner(Token, NER, Span)
            """

    session = Session()
    session.register(**NER)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_entity_mentions():
    from rgxlog.stdlib.nlp import EntityMentions
    EXPECTED_RESULT = """printing results for query 'em(DocTokenBegin, DocTokenEnd, TokenBegin, TokenEnd, Text, CharacterOffsetBegin, CharacterOffsetEnd, Ner, NerConfidences)':
   DocTokenBegin |   DocTokenEnd |   TokenBegin |   TokenEnd |      Text      |   CharacterOffsetBegin |   CharacterOffsetEnd |        Ner        |           NerConfidences
-----------------+---------------+--------------+------------+----------------+------------------------+----------------------+-------------------+------------------------------------
               7 |             8 |            7 |          8 |   California   |                     43 |                   53 | STATE_OR_PROVINCE |   {'LOCATION': 0.99823619336706}
               0 |             3 |            0 |          3 | New York Times |                      0 |                   14 |   ORGANIZATION    | {'ORGANIZATION': 0.98456891831803}
"""

    query = """sentence = "New York Times newspaper is distributed in California." 
        em(X, Y, Z, W, A, B, C, D, E) <- EntityMentions(sentence) -> (X, Y, Z, W, A, B, C, D, E) 
        ?em(DocTokenBegin, DocTokenEnd, TokenBegin, TokenEnd, Text, \
        CharacterOffsetBegin, CharacterOffsetEnd, Ner, NerConfidences) """

    session = Session()
    session.register(**EntityMentions)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_parse():
    from rgxlog.stdlib.nlp import Parse
    EXPECTED_RESULT = """printing results for query 'parse(X)':
                                                                                  X
----------------------------------------------------------------------------------------------------------------------------------------------------------------------
 (ROOT<nl>)  (S<nl>)    (NP (DT the) (JJ quick) (JJ brown) (NN fox))<nl>)    (VP (VBZ jumps)<nl>)      (PP (IN over)<nl>)        (NP (DT the) (JJ lazy) (NN dog))))))
"""

    query = """sentence = "the quick brown fox jumps over the lazy dog"
        parse(X) <- Parse(sentence) -> (X)
        ?parse(X)"""

    session = Session()
    session.register(**Parse)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_depparse():
    from rgxlog.stdlib.nlp import DepParse

    EXPECTED_RESULT = """printing results for query 'depparse(Dep, Governor, GovernorGloss, Dependent, DependentGloss)':
  Dep  |   Governor |  GovernorGloss  |   Dependent |  DependentGloss
-------+------------+-----------------+-------------+------------------
  obl  |          5 |      jumps      |           9 |       dog
 amod  |          9 |       dog       |           8 |       lazy
  det  |          9 |       dog       |           7 |       the
 case  |          9 |       dog       |           6 |       over
 nsubj |          5 |      jumps      |           4 |       fox
 amod  |          4 |       fox       |           3 |      brown
 amod  |          4 |       fox       |           2 |      quick
  det  |          4 |       fox       |           1 |       the
 ROOT  |          0 |      ROOT       |           5 |      jumps
 """

    query = """sentence = "the quick brown fox jumps over the lazy dog"
            depparse(X, Y, Z, W, U) <- DepParse(sentence) -> (X, Y, Z, W, U)
            ?depparse(Dep, Governor, GovernorGloss, Dependent, DependentGloss)"""

    session = Session()
    session.register(**DepParse)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_coref():
    from rgxlog.stdlib.nlp import Coref
    EXPECTED_RESULT = """printing results for query 'coref(Id, Text, Type, Number, Gender, Animacy, StartIndex, EndIndex, HeadIndex, SentNum, Position, IsRepresentativeMention)':
   Id |   Text   |    Type    |  Number  |  Gender  |  Animacy  |   StartIndex |   EndIndex |   HeadIndex |   SentNum |  Position  |  IsRepresentativeMention
------+----------+------------+----------+----------+-----------+--------------+------------+-------------+-----------+------------+---------------------------
    3 |    it    | PRONOMINAL | SINGULAR | NEUTRAL  | INANIMATE |           10 |         11 |          10 |         1 |   [1, 4)   |           False
    0 | The atom |  NOMINAL   | SINGULAR | NEUTRAL  | INANIMATE |            1 |          3 |           2 |         1 |   [1, 1)   |           True
"""

    query = """sentence = "The atom is a basic unit of matter, \
                it consists of a dense central nucleus surrounded by a cloud of negatively charged electrons."
        coref(X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12) <- \
        Coref(sentence) -> (X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12)
        ?coref(Id, Text, Type, Number, Gender, Animacy, StartIndex, \
        EndIndex, HeadIndex, SentNum, Position, IsRepresentativeMention)"""

    session = Session()
    session.register(**Coref)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_openie():
    from rgxlog.stdlib.nlp import OpenIE
    EXPECTED_RESULT = """printing results for query 'openie(Subject, SubjectSpan, Relation, RelationSpan, Object, ObjectSpan)':
     Subject     |  SubjectSpan  |  Relation  |  RelationSpan  |  Object  |  ObjectSpan
-----------------+---------------+------------+----------------+----------+--------------
    brown fox    |    [2, 4)     | jumps over |     [4, 6)     | lazy dog |    [7, 9)
       fox       |    [3, 4)     | jumps over |     [4, 6)     | lazy dog |    [7, 9)
    quick fox    |    [1, 4)     | jumps over |     [4, 6)     | lazy dog |    [7, 9)
    quick fox    |    [1, 4)     | jumps over |     [4, 6)     |   dog    |    [8, 9)
 quick brown fox |    [1, 4)     | jumps over |     [4, 6)     |   dog    |    [8, 9)
    brown fox    |    [2, 4)     | jumps over |     [4, 6)     |   dog    |    [8, 9)
       fox       |    [3, 4)     | jumps over |     [4, 6)     |   dog    |    [8, 9)
 quick brown fox |    [1, 4)     | jumps over |     [4, 6)     | lazy dog |    [7, 9)
"""

    query = """sentence = "the quick brown fox jumps over the lazy dog"
           openie(X1, X2, X3, X4, X5, X6) <- OpenIE(sentence) -> (X1, X2, X3, X4, X5, X6)
           ?openie(Subject, SubjectSpan, Relation, RelationSpan, Object, ObjectSpan)"""

    session = Session()
    session.register(**OpenIE)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_kbp():
    from rgxlog.stdlib.nlp import KBP
    EXPECTED_RESULT = """printing results for query 'kbp(Subject, SubjectSpan, Relation, RelationSpan, Object, ObjectSpan)':
  Subject  |  SubjectSpan  |           Relation           |  RelationSpan  |  Object  |  ObjectSpan
-----------+---------------+------------------------------+----------------+----------+--------------
 Joe Smith |    [0, 2)     | per:stateorprovince_of_birth |    [-2, -1)    |  Oregon  |    [5, 6)
"""

    query = """sentence = "Joe Smith was born in Oregon."
           kbp(X1, X2, X3, X4, X5, X6) <- KBP(sentence) -> (X1, X2, X3, X4, X5, X6)
           ?kbp(Subject, SubjectSpan, Relation, RelationSpan, Object, ObjectSpan)"""

    session = Session()
    session.register(**KBP)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_sentiment():
    from rgxlog.stdlib.nlp import Sentiment

    EXPECTED_RESULT = """printing results for query 'sentiment(SentimentValue, Sentiment, SentimentDistribution)':
   SentimentValue |  Sentiment  |                                   SentimentDistribution
------------------+-------------+--------------------------------------------------------------------------------------------
                1 |  Negative   | [0.38530939547592, 0.40530204971517, 0.15108253421994, 0.0344418112832, 0.02386420930578]
                1 |  Negative   | [0.12830923590495, 0.37878858881094, 0.30518256399302, 0.1718067054989, 0.01591290579219]
                2 |   Neutral   |  [4.32842857e-06, 0.00178165446312, 0.99514483788581, 0.00300054886868, 6.863035382e-05]
                2 |   Neutral   | [0.05362880533407, 0.34651236390176, 0.49340993668151, 0.10427916689283, 0.00216972718983]
                2 |   Neutral   | [0.02439193942712, 0.30967820316829, 0.58893236904834, 0.0763362330424, 0.00066125531385]
                2 |   Neutral   | [0.01782223769627, 0.29955831565507, 0.61735992863662, 0.06487534397678, 0.00038417403527]
                1 |  Negative   | [0.12830922491145, 0.37878858297753, 0.30518256852813, 0.17180671895586, 0.01591290462702]
                1 |  Negative   | [0.10061981563996, 0.47061477615492, 0.34369414180068, 0.0811364260425, 0.00393484036195]
"""

    query = """sentence = "But I do not want to go among mad people, Alice remarked.\
            Oh, you can not help that, said the Cat: we are all mad here. I am mad. You are mad.\
            How do you know I am mad? said Alice.\
            You must be, said the Cat, or you would not have come here. This is awful, bad, disgusting"
           sentiment(X, Y, Z) <- Sentiment(sentence) -> (X, Y, Z)
           ?sentiment(SentimentValue, Sentiment, SentimentDistribution)"""

    session = Session()
    session.register(**Sentiment)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_truecase():
    from rgxlog.stdlib.nlp import TrueCase

    EXPECTED_RESULT = """printing results for query 'truecase(Token, Span, Truecase, TruecaseText)':
  Token  |   Span   |  Truecase  |  TruecaseText
---------+----------+------------+----------------
    .    | [57, 58) |     O      |       .
  game   | [53, 57) |   LOWER    |      game
 lakers  | [46, 52) | INIT_UPPER |     Lakers
   the   | [42, 45) |   LOWER    |      the
  after  | [36, 41) |   LOWER    |     after
 bryant  | [29, 35) | INIT_UPPER |     Bryant
  kobe   | [24, 28) | INIT_UPPER |      Kobe
  about  | [18, 23) |   LOWER    |     about
 talked  | [11, 17) |   LOWER    |     talked
  ball   | [6, 10)  | INIT_UPPER |      Ball
  lonzo  |  [0, 5)  | INIT_UPPER |     Lonzo
"""

    query = """sentence = "lonzo ball talked about kobe bryant after the lakers game."
           truecase(X, Y, Z, W) <- TrueCase(sentence) -> (X, Y, Z, W)
           ?truecase(Token, Span, Truecase, TruecaseText)"""

    session = Session()
    session.register(**TrueCase)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_clean_xml():
    from rgxlog.stdlib.nlp import CleanXML

    EXPECTED_RESULT = """printing results for query 'clean_xml(Index, Word, OriginalText, CharacterOffsetBegin, CharacterOffsetEnd)':
   Index |   Word   |  OriginalText  |   CharacterOffsetBegin |   CharacterOffsetEnd
---------+----------+----------------+------------------------+----------------------
      -1 |    !     |       !        |                    118 |                  119
      -1 | weekend  |    weekend     |                    111 |                  118
      -1 |   this   |      this      |                    106 |                  110
      -1 |    me    |       me       |                    103 |                  105
      -1 |  forget  |     forget     |                     96 |                  102
      -1 |   n't    |      n't       |                     92 |                   95
      -1 |    Do    |       Do       |                     90 |                   92
      -1 | Reminder |    Reminder    |                     59 |                   67
      -1 |   Jani   |      Jani      |                     31 |                   35
      -1 |   Tove   |      Tove      |                      9 |                   13
"""

    query = """sentence = "<xml><to>Tove</to>\
       <from>Jani</Ffrom>\
       <heading>Reminder</heading>\
       <body>Don't forget me this weekend!</body></xml>"
           clean_xml(X, Y, Z, W, U) <- CleanXML(sentence) -> (X, Y, Z, W, U)
           ?clean_xml(Index, Word, OriginalText, CharacterOffsetBegin, CharacterOffsetEnd)"""

    session = Session()
    session.register(**CleanXML)
    query_result = session.run_query(query)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


def test_remove_rule():
    EXPECTED_RESULT = """printing results for query 'ancestor(X, Y)':
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
    session.run_query(query)

    session.remove_rule("ancestor(X,Y) <- parent(X,Y)")
    query_result = session.run_query("""
                    ?ancestor(X, Y)
                    ?tmp(X, Y)
                    """)
    assert compare_strings(EXPECTED_RESULT, query_result), "fail"


