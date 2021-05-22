from tests.utils import run_test


# TODO@niv: discovered a bug, that sometimes when running jupyter notebook, and importing
#  chen's project, i get a "Java not found" exception (not sure if jupyter is related, maybe it's a RAM thing)
#  additionally, i've found out that after running the code a few times, i've had ~10 java.exe processes
#  running in the background. looks like chen's process never dies

def test_entities():
    expected_result = """printing results for query 'entities(Entity, Classification)':
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

    run_test(query, expected_result)


def test_tokenize():
    expected_result = """printing results for query 'tokens(Token, Span)':
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

    run_test(query, expected_result)


def test_ssplit():
    expected_result = """printing results for query 'sentences(Sentences)':
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

    run_test(query, expected_result)


def test_pos():
    expected_result = """printing results for query 'pos(Token, POS, Span)':
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

    run_test(query, expected_result)


def test_lemma():
    from rgxlog.stdlib.nlp import Lemma
    expected_result = """printing results for query 'lemma(Token, Lemma, Span)':
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

    run_test(query, expected_result, [Lemma])


def test_ner():
    expected_result = """printing results for query 'ner(Token, NER, Span)':
                       Token   |     NER      |    Span
                    -----------+--------------+------------
                      Journal  | ORGANIZATION | [116, 123)
                      Street   | ORGANIZATION | [109, 115)
                       Wall    | ORGANIZATION | [104, 108)
                      Lagarde  |    PERSON    |  [27, 34)
                     Christine |    PERSON    |  [17, 26)
                      France   |   COUNTRY    |  [9, 15)
                    """

    query = ("""sentence = "While in France, Christine Lagarde discussed short-term stimulus """
             """efforts in a recent interview with the Wall Street Journal."
            ner(X, Y, Z) <- NER(sentence) -> (X, Y, Z)
            ?ner(Token, NER, Span)""")

    run_test(query, expected_result)


# TODO@niv: this sometimes raises `raise RuntimeError('Java not found.')` (inside `spanner-nlp`)
# @reponse: wierd, have you checked why? is it only this test, or only this annotator?
def test_entity_mentions():
    expected_result = ("""printing results for query 'em(DocTokenBegin, DocTokenEnd, TokenBegin, TokenEnd, Text,"""
                       """ CharacterOffsetBegin, CharacterOffsetEnd, Ner, NerConfidences)':
                       DocTokenBegin |   DocTokenEnd |   TokenBegin |   TokenEnd |      Text      |   """
                       """CharacterOffsetBegin |   CharacterOffsetEnd |        Ner        |           NerConfidences
                    -----------------+---------------+--------------+------------+----------------+-----------"""
                       """-------------+----------------------+-------------------+------------------------------------
                                   7 |             8 |            7 |          8 |   California   |             """
                       """        43 |                   53 | STATE_OR_PROVINCE |   {'LOCATION': 0.99823619336706}
                                   0 |             3 |            0 |          3 | New York Times |             """
                       """         0 |                   14 |   ORGANIZATION    | {'ORGANIZATION': 0.98456891831803}
                    """)

    query = """sentence = "New York Times newspaper is distributed in California." 
        em(X, Y, Z, W, A, B, C, D, E) <- EntityMentions(sentence) -> (X, Y, Z, W, A, B, C, D, E) 
        ?em(DocTokenBegin, DocTokenEnd, TokenBegin, TokenEnd, Text, \
        CharacterOffsetBegin, CharacterOffsetEnd, Ner, NerConfidences) """

    run_test(query, expected_result)


def test_parse():
    from rgxlog.stdlib.nlp import Parse
    expected_result = ("""printing results for query 'parse(X)':
                                                                                                    X
                    ----------------------------------------------------------------------------------------"""
                       """-------------------------------------------------------------------------
                     (ROOT<nl>  (S<nl>    (NP (DT the) (JJ quick) (JJ brown) (NN fox))<nl>    (VP (VBZ jumps)<nl>"""
                       """      (PP (IN over)<nl>        (NP (DT the) (JJ lazy) (NN dog))))))""")

    query = """sentence = "the quick brown fox jumps over the lazy dog"
        parse(X) <- Parse(sentence) -> (X)
        ?parse(X)"""

    run_test(query, expected_result, [Parse])


def test_depparse():
    expected_result = """printing results for query 'depparse(Dep, Governor, GovernorGloss, Dependent, DependentGloss)':
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

    run_test(query, expected_result)


# TODO@niv: this test is really slow sometimes
# @response: nlp is slow unfortunatly, I dont remember which test suite you use (maybe pytest)
# but you can annotate it as a special test that only runs when given a slow-test flag or something
def test_coref():
    expected_result = ("""printing results for query 'coref(Id, Text, Type, Number, Gender, Animacy, StartIndex,"""
                       """ EndIndex, HeadIndex, SentNum, Position, IsRepresentativeMention)':
                           Id |   Text   |    Type    |  Number  |  Gender  |  Animacy  |   StartIndex |   EndIndex"""
                       """ |   HeadIndex |   SentNum |  Position  |  IsRepresentativeMention
                        ------+----------+------------+----------+----------+-----------+--------------+------------"""
                       """+-------------+-----------+------------+---------------------------
                            3 |    it    | PRONOMINAL | SINGULAR | NEUTRAL  | INANIMATE |           10 |         11"""
                       """ |          10 |         1 |   [1, 4)   |           False
                            0 | The atom |  NOMINAL   | SINGULAR | NEUTRAL  | INANIMATE |            1 |          3"""
                       """ |           2 |         1 |   [1, 1)   |           True""")

    query = """sentence = "The atom is a basic unit of matter, \
                it consists of a dense central nucleus surrounded by a cloud of negatively charged electrons."
        coref(X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12) <- \
        Coref(sentence) -> (X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12)
        ?coref(Id, Text, Type, Number, Gender, Animacy, StartIndex, \
        EndIndex, HeadIndex, SentNum, Position, IsRepresentativeMention)"""

    run_test(query, expected_result)


def test_openie():
    expected_result = ("""printing results for query 'openie(Subject, SubjectSpan, Relation, RelationSpan,"""
                       """ Object, ObjectSpan)':
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
                        """)

    query = """sentence = "the quick brown fox jumps over the lazy dog"
           openie(X1, X2, X3, X4, X5, X6) <- OpenIE(sentence) -> (X1, X2, X3, X4, X5, X6)
           ?openie(Subject, SubjectSpan, Relation, RelationSpan, Object, ObjectSpan)"""

    run_test(query, expected_result)


# TODO@niv: this used ~3GB RAM for me, is this normal?
# @ response:
# yes, see this: https://stanfordnlp.github.io/CoreNLP/memory-time.html
# there is a way to limit memory usage in java https://stackoverflow.com/a/1493951/14571960
# which i think will cause the engine to crash if the mem footprint of the annotator is too large
def test_kbp():
    expected_result = ("""printing results for query 'kbp(Subject, SubjectSpan, Relation, RelationSpan, Object,"""
                       """ ObjectSpan)':
                          Subject  |  SubjectSpan  |           Relation           |  RelationSpan  |  Object  |"""
                       """  ObjectSpan
                        -----------+---------------+------------------------------+----------------+----------+---"""
                       """-----------
                         Joe Smith |    [0, 2)     | per:stateorprovince_of_birth |    [-2, -1)    |  Oregon  |    """
                       """[5, 6)""")

    query = """sentence = "Joe Smith was born in Oregon."
           kbp(X1, X2, X3, X4, X5, X6) <- KBP(sentence) -> (X1, X2, X3, X4, X5, X6)
           ?kbp(Subject, SubjectSpan, Relation, RelationSpan, Object, ObjectSpan)"""

    run_test(query, expected_result)


def test_sentiment():
    expected_result = ("""printing results for query 'sentiment(SentimentValue, Sentiment, SentimentDistribution)':
                           SentimentValue |  Sentiment  |                                   SentimentDistribution
                        ------------------+-------------+-------------------------------------------------------"""
                       """-------------------------------------
                                        1 |  Negative   | [0.38530939547592, 0.40530204971517, 0.15108253421994, """
                       """0.0344418112832, 0.02386420930578]
                                        1 |  Negative   | [0.12830923590495, 0.37878858881094, 0.30518256399302,"""
                       """ 0.1718067054989, 0.01591290579219]
                                        2 |   Neutral   |  [4.32842857e-06, 0.00178165446312, 0.99514483788581,"""
                       """ 0.00300054886868, 6.863035382e-05]
                                        2 |   Neutral   | [0.05362880533407, 0.34651236390176, 0.49340993668151,"""
                       """ 0.10427916689283, 0.00216972718983]
                                        2 |   Neutral   | [0.02439193942712, 0.30967820316829, 0.58893236904834,"""
                       """ 0.0763362330424, 0.00066125531385]
                                        2 |   Neutral   | [0.01782223769627, 0.29955831565507, 0.61735992863662,"""
                       """ 0.06487534397678, 0.00038417403527]
                                        1 |  Negative   | [0.12830922491145, 0.37878858297753, 0.30518256852813,"""
                       """ 0.17180671895586, 0.01591290462702]
                                        1 |  Negative   | [0.10061981563996, 0.47061477615492, 0.34369414180068,"""
                       """ 0.0811364260425, 0.00393484036195]
                        """)

    query = """sentence = "But I do not want to go among mad people, Alice remarked.\
            Oh, you can not help that, said the Cat: we are all mad here. I am mad. You are mad.\
            How do you know I am mad? said Alice.\
            You must be, said the Cat, or you would not have come here. This is awful, bad, disgusting"
           sentiment(X, Y, Z) <- Sentiment(sentence) -> (X, Y, Z)
           ?sentiment(SentimentValue, Sentiment, SentimentDistribution)"""

    run_test(query, expected_result)


def test_truecase():
    expected_result = """printing results for query 'truecase(Token, Span, Truecase, TruecaseText)':
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

    run_test(query, expected_result)


def test_clean_xml():
    expected_result = ("""printing results for query 'clean_xml(Index, Word, OriginalText, CharacterOffsetBegin,"""
                       """ CharacterOffsetEnd)':
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
                        """)

    query = """sentence = "<xml><to>Tove</to>\
       <from>Jani</Ffrom>\
       <heading>Reminder</heading>\
       <body>Don't forget me this weekend!</body></xml>"
           clean_xml(X, Y, Z, W, U) <- CleanXML(sentence) -> (X, Y, Z, W, U)
           ?clean_xml(Index, Word, OriginalText, CharacterOffsetBegin, CharacterOffsetEnd)"""

    run_test(query, expected_result)
