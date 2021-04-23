import os
from os.path import dirname, abspath
import pytest
from pandas import DataFrame
from rgxlog.engine.session import Session, query_to_string


# csv filenames
TESTS_DIR = dirname(abspath(__file__))
LONGREL_CSV = os.path.join(TESTS_DIR, "query_longrel.csv")
REL_CSV = os.path.join(TESTS_DIR, "query_rel.csv")
EXAMPLE_RELATION_CSV = os.path.join(TESTS_DIR, "example_relation.csv")
EXAMPLE_RELATION_TWO_CSV = os.path.join(TESTS_DIR, "example_relation_two.csv")
TEMP_CSV = os.path.join(TESTS_DIR, "temp.csv")


@pytest.fixture(scope="module")
def im_ex_session():
    # pay attention - we use a single session per module because it's more efficient
    # be careful not to redefine symbols between tests
    return Session()


def test_import_csv1(im_ex_session: Session):
    im_ex_session.import_relation_from_csv(
        EXAMPLE_RELATION_CSV,
        relation_name="csv_rel")

    expected_result_string = """printing results for query \'csv_rel(X, Y, Z)\':
    X     |    Y     |   Z
----------+----------+-----
 ano sora | [42, 69) |  24
   aoi    |  [1, 2)  |  16
   aoi    |  [0, 3)  |   8
"""

    query_result = im_ex_session.run_query("?csv_rel(X,Y,Z)", print_results=False)
    query_result_string = query_to_string(query_result)
    assert query_result_string == expected_result_string


def test_import_csv2(im_ex_session: Session):
    im_ex_session.import_relation_from_csv(
        EXAMPLE_RELATION_TWO_CSV,
        relation_name="csv_rel2")

    expected_result_string = """printing results for query \'csv_rel2(X)\':
  X
-----
  c
  b
  a
"""

    query_result = im_ex_session.run_query("?csv_rel2(X)", print_results=False)
    query_result_string = query_to_string(query_result)
    assert query_result_string == expected_result_string


def test_import_df(im_ex_session: Session):
    df = DataFrame(["a", "b", "c"])

    expected_result_string = """printing results for query \'df_rel(X)\':
  X
-----
  c
  b
  a
"""

    im_ex_session.import_relation_from_df(df, "df_rel")
    query_result = im_ex_session.run_query("?df_rel(X)", print_results=False)
    query_result_string = query_to_string(query_result)
    assert query_result_string == expected_result_string


def test_query_into_csv_basic(im_ex_session: Session):
    # create new relation
    im_ex_session.run_query("new basic_rel(str)", print_results=False)
    im_ex_session.run_query('basic_rel("stardew")', print_results=False)
    im_ex_session.run_query('basic_rel("valley")', print_results=False)

    # query into csv and compare with old file
    im_ex_session.query_into_csv('?basic_rel(X)', TEMP_CSV)
    assert os.path.isfile(TEMP_CSV), "file was not created"

    with open(TEMP_CSV) as f_temp:
        with open(REL_CSV) as f_test:
            assert f_temp.read() == f_test.read(), "files are not equal"

    os.remove(TEMP_CSV)
    assert not os.path.isfile(TEMP_CSV), "file could not be deleted"


def test_query_into_csv_long(im_ex_session: Session):
    # create new relation
    im_ex_session.run_query("new longrel(str,spn,int)",
                            print_results=False)  # TODO why not change it into span? much more readable
    im_ex_session.run_query('longrel("ano sora",[42, 69),24)', print_results=False)
    im_ex_session.run_query('longrel("aoi",[1, 2),16)', print_results=False)
    im_ex_session.run_query('longrel("aoi",[0, 3),8)', print_results=False)

    # query into csv and compare with old file
    im_ex_session.query_into_csv("?longrel(X,Y,Z)", TEMP_CSV)
    assert os.path.isfile(TEMP_CSV), "file was not created"

    with open(TEMP_CSV) as f_temp:
        with open(LONGREL_CSV) as f_test:
            assert f_temp.read() == f_test.read(), "files are not equal"

    os.remove(TEMP_CSV)
    assert not os.path.isfile(TEMP_CSV), "file could not be deleted"


def test_query_into_df(im_ex_session: Session):
    test_df = DataFrame(["king", "jump"], columns=["X"])
    # create new relation
    im_ex_session.run_query("new df_query_rel(str)", print_results=False)
    im_ex_session.run_query('df_query_rel("jump")', print_results=False)
    im_ex_session.run_query('df_query_rel("king")', print_results=False)

    # query into df and compare
    temp_df = im_ex_session.query_into_df("?df_query_rel(X)")
    assert temp_df.equals(test_df)
