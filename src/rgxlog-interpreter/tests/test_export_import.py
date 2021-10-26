import tempfile
from pathlib import Path

import pytest
from pandas import DataFrame

from rgxlog.engine.datatypes.primitive_types import Span
from rgxlog.engine.execution import FREE_VAR_PREFIX
from rgxlog.engine.session import Session
from rgxlog.engine.utils.general_utils import QUERY_RESULT_PREFIX
from tests.utils import (run_test, is_equal_stripped_sorted_tables, is_equal_dataframes_ignore_order, run_commands_into_csv_test, TEMP_FILE_NAME)


@pytest.fixture(scope="module")
def im_ex_session() -> Session:
    # pay attention - we use a single session per module because it's more efficient
    # be careful not to redefine symbols between tests
    return Session()


def test_import_csv1(im_ex_session: Session) -> None:
    example_relation = (
        '"aoi";[0,3);8\n'
        '"aoi";[1,2);16\n'
        '"ano sora";[42,69);24\n')

    expected_result_string = f"""{QUERY_RESULT_PREFIX}'csv_rel(X, Y, Z)':
                                        X     |    Y     |   Z
                                    ----------+----------+-----
                                     ano sora | [42, 69) |  24
                                       aoi    |  [1, 2)  |  16
                                       aoi    |  [0, 3)  |   8
                                    """

    with tempfile.TemporaryDirectory() as temp_dir:
        example_relation_csv = Path(temp_dir) / TEMP_FILE_NAME
        with open(example_relation_csv, "w") as f:
            f.write(example_relation)

        im_ex_session.import_relation_from_csv(example_relation_csv, relation_name="csv_rel")
        query = "?csv_rel(X,Y,Z)"
        run_test(query, expected_result_string, session=im_ex_session)


def test_import_csv2(im_ex_session: Session) -> None:
    example_relation_two = (
        "a\n"
        "b\n"
        "c\n")

    with tempfile.TemporaryDirectory() as temp_dir:
        example_relation2_csv = Path(temp_dir) / TEMP_FILE_NAME
        with open(example_relation2_csv, "w") as f:
            f.write(example_relation_two)

        im_ex_session.import_relation_from_csv(example_relation2_csv, relation_name="csv_rel2")

        expected_result_string = f"""{QUERY_RESULT_PREFIX}'csv_rel2(X)':
                                      X
                                    -----
                                      c
                                      b
                                      a
                                    """

        query = "?csv_rel2(X)"
        run_test(query, expected_result_string, session=im_ex_session)


def test_import_df(im_ex_session: Session) -> None:
    df = DataFrame([["a", "[1,2)"], ["b", Span(6, 8)], ["c", "[2,10)"]], columns=["str", "span"])

    query = "?df_rel(X,Y)"

    expected_result_string = f"""{QUERY_RESULT_PREFIX}'df_rel(X, Y)':
          X  |    Y
        -----+---------
          c  | [2, 10)
          b  | [6, 8)
          a  | [1, 2)"""

    im_ex_session.import_relation_from_df(df, "df_rel")
    run_test(query, expected_result_string, session=im_ex_session)


def test_commands_into_csv_basic(im_ex_session: Session) -> None:
    commands = """new basic_rel(str)
            basic_rel("stardew")
            basic_rel("valley")"""

    expected_rel = (
        "X\n"
        "valley\n"
        "stardew\n")

    query_for_csv = '?basic_rel(X)'

    run_commands_into_csv_test(expected_rel, im_ex_session, commands, query_for_csv)


def test_commands_into_csv_long(im_ex_session: Session) -> None:
    commands = """new longrel(str,span,int)
            longrel("ano sora",[42, 69),24)
            longrel("aoi",[1, 2),16)
            longrel("aoi",[0, 3),8)"""

    expected_longrel = (
        "X;Y;Z\n"
        "aoi;[0, 3);8\n"
        "aoi;[1, 2);16\n"
        "ano sora;[42, 69);24\n")

    query_for_csv = "?longrel(X,Y,Z)"

    run_commands_into_csv_test(expected_longrel, im_ex_session, commands, query_for_csv)


def test_export_relation_into_csv(im_ex_session: Session) -> None:
    relation_name = "hotdoge"
    commands = f"""
            new {relation_name}(str, int)
            {relation_name}("wow",42)
            {relation_name}("such summer", 420)
            {relation_name}("much heat", 42)"""

    expected_export_rel = f"""
        {FREE_VAR_PREFIX}0:{FREE_VAR_PREFIX}1
        wow:42
        such summer:420
        much heat:42"""

    im_ex_session.run_commands(commands, print_results=False)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_csv = Path(temp_dir) / TEMP_FILE_NAME
        im_ex_session.export_relation_into_csv(temp_csv, relation_name, delimiter=":")
        assert Path(temp_csv).is_file(), "file was not created"

        with open(temp_csv) as f_temp:
            assert is_equal_stripped_sorted_tables(f_temp.read(), expected_export_rel), "file was not written properly"


def test_commands_into_df(im_ex_session: Session) -> None:
    test_df = DataFrame(["king", "jump"], columns=["X"])
    # create new relation
    commands = """
        new df_query_rel(str)
        df_query_rel("jump")
        df_query_rel("king")"""

    im_ex_session.run_commands(commands, print_results=False)

    query_for_df = "?df_query_rel(X)"

    # send commands into df and compare
    temp_df = im_ex_session.send_commands_result_into_df(query_for_df)
    assert is_equal_dataframes_ignore_order(temp_df, test_df), "the dataframes are not equal"


def test_export_relation_into_df(im_ex_session: Session) -> None:
    column_names = [f"{FREE_VAR_PREFIX}0", f"{FREE_VAR_PREFIX}1"]

    relation_name = "export_df_rel"
    commands = f"""
        new {relation_name}(span, str)
        {relation_name}([1,3), "aa")
        {relation_name}([2,4), "bb")"""

    expected_df = DataFrame([[Span(1, 3), "aa"], [Span(2, 4), "bb"]], columns=column_names)

    im_ex_session.run_commands(commands)
    result_df = im_ex_session.export_relation_into_df(relation_name)

    assert is_equal_dataframes_ignore_order(result_df, expected_df)
