import pytest

from rgxlog.engine.utils.general_utils import QUERY_RESULT_PREFIX
from tests.utils import run_test


def test_tokenize() -> None:
    commands = """
                    sentence = "Hello world. Hello world again."
                    tokens(X, Y) <- Tokenize(sentence) -> (X, Y)
                    ?tokens(Token, Span)
                """

    expected_result = f"""{QUERY_RESULT_PREFIX}'tokens(Token, Span)':
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

    # run_test(commands, expected_result)


def test_ssplit() -> None:
    commands = """
                sentence = "Hello world. Hello world again."
                sentences(X) <- SSplit(sentence) -> (X)
                ?sentences(Sentences)
                """

    expected_result = f"""{QUERY_RESULT_PREFIX}'sentences(Sentences)':
                          Sentences
                    ---------------------
                     Hello world again .
                        Hello world .
                    """

    # run_test(commands, expected_result)


def test_pos() -> None:
    commands = """
                sentence = "Marie was born in Paris."
                pos(X, Y, Z) <- POS(sentence) -> (X, Y, Z)
                ?pos(Token, POS, Span)
            """

    expected_result = f"""{QUERY_RESULT_PREFIX}'pos(Token, POS, Span)':
                      Token  |  POS  |   Span
                    ---------+-------+----------
                        .    |   .   | [23, 24)
                      Paris  |  NNP  | [18, 23)
                       in    |  IN   | [15, 17)
                      born   |  VBN  | [10, 14)
                       was   |  VBD  |  [6, 9)
                      Marie  |  NNP  |  [0, 5)
                    """

    # run_test(commands, expected_result)


def test_lemma() -> None:
    commands = """
                sentence = "I've been living a lie, there's nothing inside."
                lemma(X, Y, Z) <- Lemma(sentence) -> (X, Y, Z)
                ?lemma(Token, Lemma, Span)
                 """

    expected_result = f"""{QUERY_RESULT_PREFIX}'lemma(Token, Lemma, Span)':
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

    # run_test(commands, expected_result)


@pytest.mark.long
def test_ner() -> None:
    commands = ("""sentence = "While in France, Christine Lagarde discussed short-term stimulus """
                """efforts in a recent interview with the Wall Street Journal."
               ner(X, Y, Z) <- NER(sentence) -> (X, Y, Z)
               ?ner(Token, NER, Span)""")

    expected_result = f"""{QUERY_RESULT_PREFIX}'ner(Token, NER, Span)':
                       Token   |     NER      |    Span
                    -----------+--------------+------------
                      Journal  | ORGANIZATION | [116, 123)
                      Street   | ORGANIZATION | [109, 115)
                       Wall    | ORGANIZATION | [104, 108)
                      Lagarde  |    PERSON    |  [27, 34)
                     Christine |    PERSON    |  [17, 26)
                      France   |   COUNTRY    |  [9, 15)
                    """

    # run_test(commands, expected_result)


@pytest.mark.long
def test_entity_mentions() -> None:
    commands = """sentence = "New York Times newspaper is distributed in California."
            em(X, Y, Z, W, A, B, C, D, E) <- EntityMentions(sentence) -> (X, Y, Z, W, A, B, C, D, E)
            ?em(DocTokenBegin, DocTokenEnd, TokenBegin, TokenEnd, Text, \
            CharacterOffsetBegin, CharacterOffsetEnd, Ner, NerConfidences) """

    expected_result = (f"""{QUERY_RESULT_PREFIX}'em(DocTokenBegin, DocTokenEnd, TokenBegin, TokenEnd, Text,"""
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

    # run_test(commands, expected_result)


def test_parse() -> None:
    commands = """sentence = "the quick brown fox jumps over the lazy dog"
           parse(X) <- Parse(sentence) -> (X)
           ?parse(X)"""

    expected_result = (f"""{QUERY_RESULT_PREFIX}'parse(X)':
                                                                                                    X
                    ----------------------------------------------------------------------------------------"""
                       """-------------------------------------------------------------------------
                     (ROOT<nl>  (S<nl>    (NP (DT the) (JJ quick) (JJ brown) (NN fox))<nl>    (VP (VBZ jumps)<nl>"""
                       """      (PP (IN over)<nl>        (NP (DT the) (JJ lazy) (NN dog))))))""")

    # run_test(commands, expected_result)


@pytest.mark.long
def test_depparse() -> None:
    commands = """sentence = "the quick brown fox jumps over the lazy dog"
                depparse(X, Y, Z, W, U) <- DepParse(sentence) -> (X, Y, Z, W, U)
                ?depparse(Dep, Governor, GovernorGloss, Dependent, DependentGloss)"""

    expected_result = f"""{QUERY_RESULT_PREFIX}'depparse(Dep, Governor, GovernorGloss, Dependent, DependentGloss)':
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

    # run_test(commands, expected_result)


@pytest.mark.long
def test_coref() -> None:
    commands = """sentence = "The atom is a basic unit of matter, \
                    it consists of a dense central nucleus surrounded by a cloud of negatively charged electrons."
            coref(X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12) <- \
            Coref(sentence) -> (X1, X2, X3, X4, X5, X6, X7, X8, X9, X10, X11, X12)
            ?coref(Id, Text, Type, Number, Gender, Animacy, StartIndex, \
            EndIndex, HeadIndex, SentNum, Position, IsRepresentativeMention)"""

    expected_result = (f"""{QUERY_RESULT_PREFIX}'coref(Id, Text, Type, Number, Gender, Animacy, StartIndex,"""
                       """ EndIndex, HeadIndex, SentNum, Position, IsRepresentativeMention)':
                           Id |   Text   |    Type    |  Number  |  Gender  |  Animacy  |   StartIndex |   EndIndex"""
                       """ |   HeadIndex |   SentNum |  Position  |  IsRepresentativeMention
                        ------+----------+------------+----------+----------+-----------+--------------+------------"""
                       """+-------------+-----------+------------+---------------------------
                            3 |    it    | PRONOMINAL | SINGULAR | NEUTRAL  | INANIMATE |           10 |         11"""
                       """ |          10 |         1 |   [1, 4)   |           False
                            0 | The atom |  NOMINAL   | SINGULAR | NEUTRAL  | INANIMATE |            1 |          3"""
                       """ |           2 |         1 |   [1, 1)   |           True""")

    # run_test(commands, expected_result)


@pytest.mark.long
def test_openie() -> None:
    commands = """sentence = "the quick brown fox jumps over the lazy dog"
               openie(X1, X2, X3, X4, X5, X6) <- OpenIE(sentence) -> (X1, X2, X3, X4, X5, X6)
               ?openie(Subject, SubjectSpan, Relation, RelationSpan, Object, ObjectSpan)"""

    expected_result = (f"""{QUERY_RESULT_PREFIX}'openie(Subject, SubjectSpan, Relation, RelationSpan,"""
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

    # run_test(commands, expected_result)


# note: this test uses 3+ GB of RAM
@pytest.mark.long
def test_kbp() -> None:
    commands = """sentence = "Joe Smith was born in Oregon."
              kbp(X1, X2, X3, X4, X5, X6) <- KBP(sentence) -> (X1, X2, X3, X4, X5, X6)
              ?kbp(Subject, SubjectSpan, Relation, RelationSpan, Object, ObjectSpan)"""

    expected_result = (f"""{QUERY_RESULT_PREFIX}'kbp(Subject, SubjectSpan, Relation, RelationSpan, Object,"""
                       """ ObjectSpan)':
                          Subject  |  SubjectSpan  |           Relation           |  RelationSpan  |  Object  |"""
                       """  ObjectSpan
                        -----------+---------------+------------------------------+----------------+----------+---"""
                       """-----------
                         Joe Smith |    [0, 2)     | per:stateorprovince_of_birth |    [-2, -1)    |  Oregon  |    """
                       """[5, 6)""")

    # run_test(commands, expected_result)


def test_sentiment() -> None:
    commands = """sentence = "But I do not want to go among mad people, Alice remarked.\
                Oh, you can not help that, said the Cat: we are all mad here. I am mad. You are mad.\
                How do you know I am mad? said Alice.\
                You must be, said the Cat, or you would not have come here. This is awful, bad, disgusting"
               sentiment(X, Y, Z) <- Sentiment(sentence) -> (X, Y, Z)
               ?sentiment(SentimentValue, Sentiment, SentimentDistribution)"""

    expected_result = (f"""{QUERY_RESULT_PREFIX}'sentiment(SentimentValue, Sentiment, SentimentDistribution)':
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

    # run_test(commands, expected_result)


@pytest.mark.long
def test_truecase() -> None:
    commands = """sentence = "lonzo ball talked about kobe bryant after the lakers game."
              truecase(X, Y, Z, W) <- TrueCase(sentence) -> (X, Y, Z, W)
              ?truecase(Token, Span, Truecase, TruecaseText)"""

    expected_result = f"""{QUERY_RESULT_PREFIX}'truecase(Token, Span, Truecase, TruecaseText)':
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

    # run_test(commands, expected_result)


def test_clean_xml() -> None:
    commands = """sentence = "<xml><to>Tove</to>\
       <from>Jani</Ffrom>\
       <heading>Reminder</heading>\
       <body>Don't forget me this weekend!</body></xml>"
           clean_xml(X, Y, Z, W, U) <- CleanXML(sentence) -> (X, Y, Z, W, U)
           ?clean_xml(Index, Word, OriginalText, CharacterOffsetBegin, CharacterOffsetEnd)"""

    expected_result = (f"""{QUERY_RESULT_PREFIX}'clean_xml(Index, Word, OriginalText, CharacterOffsetBegin,"""
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

    # run_test(commands, expected_result)


@pytest.mark.long
def test_quote() -> None:
    quoted_phrase = r'''\"I'm going to Hawaii.\"'''
    commands = f"""sentence = "In the summer Joe Smith decided to go on vacation.  He said, {quoted_phrase}. That July, vacationer Joe went to Hawaii."
               cool_quote(A,S,D,F,G,H,J,K,L,P) <- Quote(sentence) -> (A,S,D,F,G,H,J,K,L,P)
               ?cool_quote(A,S,D,F,G,H,J,K,L,P)"""

    expected_result = (fr"""{QUERY_RESULT_PREFIX}'cool_quote(A, S, D, F, G, H, J, K, L, P)':
                       A |           S           |   D |   F |   G |   H |   J |   K |     L     |     P
                    -----+-----------------------+-----+-----+-----+-----+-----+-----+-----------+-----------
                       0 | I'm going to Hawaii.\ |  62 |  85 |  15 |  23 |   1 |   2 | Joe Smith | Joe Smith
                       """)

    # run_test(commands, expected_result)
