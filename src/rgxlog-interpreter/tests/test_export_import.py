import os
import tempfile
from os.path import dirname, abspath

import pytest
from pandas import DataFrame

from rgxlog.engine.session import Session
from tests.utils import run_test


TEMP_FILE_NAME = "temp"


@pytest.fixture(scope="module")
def im_ex_session():
    # pay attention - we use a single session per module because it's more efficient
    # be careful not to redefine symbols between tests
    return Session()


def test_import_csv1(im_ex_session: Session):
    example_relation = (
        '"aoi";[0,3);8\n'
        '"aoi";[1,2);16\n'
        '"ano sora";[42,69);24\n')

    expected_result_string = """printing results for query \'csv_rel(X, Y, Z)\':
                                        X     |    Y     |   Z
                                    ----------+----------+-----
                                     ano sora | [42, 69) |  24
                                       aoi    |  [1, 2)  |  16
                                       aoi    |  [0, 3)  |   8
                                    """

    with tempfile.TemporaryDirectory() as temp_dir:
        example_relation_csv = os.path.join(temp_dir, TEMP_FILE_NAME)
        with open(example_relation_csv, "w") as f:
            f.write(example_relation)

        im_ex_session.import_relation_from_csv(example_relation_csv, relation_name="csv_rel")
        query = "?csv_rel(X,Y,Z)"
        run_test(query, expected_result_string, _session=im_ex_session)


def test_import_csv2(im_ex_session: Session):
    example_relation_two = (
        "a\n"
        "b\n"
        "c\n")

    with tempfile.TemporaryDirectory() as temp_dir:
        example_relation2_csv = os.path.join(temp_dir, TEMP_FILE_NAME)
        with open(example_relation2_csv, "w") as f:
            f.write(example_relation_two)

        im_ex_session.import_relation_from_csv(example_relation2_csv, relation_name="csv_rel2")

        expected_result_string = """printing results for query \'csv_rel2(X)\':
                                      X
                                    -----
                                      c
                                      b
                                      a
                                    """

        query = "?csv_rel2(X)"
        run_test(query, expected_result_string, _session=im_ex_session)


def test_import_df(im_ex_session: Session):
    df = DataFrame(["a", "b", "c"])

    expected_result_string = """printing results for query \'df_rel(X)\':
                              X
                            -----
                              c
                              b
                              a
                            """
    query = "?df_rel(X)"

    im_ex_session.import_relation_from_df(df, "df_rel")
    run_test(query, expected_result_string, _session=im_ex_session)


def test_query_into_csv_basic(im_ex_session: Session):
    query_rel = (
        "X\n"
        "valley\n"
        "stardew\n")

    # create new relation
    query = """new basic_rel(str)
        basic_rel("stardew")
        basic_rel("valley")"""
    im_ex_session.run_query(query, print_results=False)

    # query into csv and compare with old file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_csv = os.path.join(temp_dir, TEMP_FILE_NAME)

        im_ex_session.query_into_csv('?basic_rel(X)', temp_csv)
        assert os.path.isfile(temp_csv), "file was not created"

        with open(temp_csv) as f_temp:
            assert f_temp.read().strip() == query_rel.strip(), "file was not written properly"

        os.remove(temp_csv)
        assert not os.path.isfile(temp_csv), "file could not be deleted"


def test_query_into_csv_long(im_ex_session: Session):
    query_longrel = (
        "X;Y;Z\n"
        "aoi;[0, 3);8\n"
        "aoi;[1, 2);16\n"
        "ano sora;[42, 69);24\n")

    # create new relation
    # TODO@niv: dean, why not change spn into span? much more readable/intuitive
    query = """new longrel(str,spn,int)
        longrel("ano sora",[42, 69),24)
        longrel("aoi",[1, 2),16)
        longrel("aoi",[0, 3),8)"""
    im_ex_session.run_query(query, print_results=False)

    # query into csv and compare with old file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_csv = os.path.join(temp_dir, TEMP_FILE_NAME)
        im_ex_session.query_into_csv("?longrel(X,Y,Z)", temp_csv)
        assert os.path.isfile(temp_csv), "file was not created"

        with open(temp_csv) as f_temp:
            assert f_temp.read().strip() == query_longrel.strip(), "file was not written properly"

        os.remove(temp_csv)
        assert not os.path.isfile(temp_csv), "file could not be deleted"


def test_query_into_df(im_ex_session: Session):
    test_df = DataFrame(["king", "jump"], columns=["X"])
    # create new relation
    query = """
        new df_query_rel(str)
        df_query_rel("jump")
        df_query_rel("king")"""

    im_ex_session.run_query(query, print_results=False)

    # query into df and compare
    temp_df = im_ex_session.query_into_df("?df_query_rel(X)")
    assert temp_df.equals(test_df)
