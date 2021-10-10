from typing import Iterable, Tuple, Any

from jsonpath_ng import parse
import json
from rgxlog.engine.datatypes.primitive_types import DataTypes


def parse_match(match: Any) -> str:
    """
    @param match: a match result of json path query.
    @return: a string that represents the match in string format.
    """
    json_result = match.value
    if type(json_result) != str:
        # we replace for the same reason as in json_path implementation.
        json_result = json.dumps(json_result).replace("\"", "'")
    return json_result


def json_path(json_document: str, path_expression: str) -> Iterable[Tuple]:
    """
    @param json_document: The document on which we will run the path expression.
    @param path_expression: The query to execute.
    @return: json documents.
    """
    # covert string to actual json
    # json library demands the input string to be enclosed in double quotes, therefore we replace...
    json_document = json.loads(json_document.replace("'", "\""))
    jsonpath_expr = parse(path_expression)
    for match in jsonpath_expr.find(json_document):
        # each json result is a relation
        yield parse_match(match),


JsonPath = dict(ie_function=json_path,
                ie_function_name='JsonPath',
                in_rel=[DataTypes.string, DataTypes.string],
                out_rel=[DataTypes.string],
                )


def json_path_full(json_document: str, path_expression: str) -> Iterable[Tuple]:
    """
    @param json_document: The document on which we will run the path expression.
    @param path_expression: The query to execute.
    @return: json documents with the full results paths.
    """

    json_document = json.loads(json_document.replace("'", "\""))
    jsonpath_expr = parse(path_expression)
    for match in jsonpath_expr.find(json_document):
        json_result = str(match.full_path)
        # objects in full path are separated by dots.
        yield *json_result.split("."), parse_match(match)


JsonPathFull = dict(ie_function=json_path_full,
                    ie_function_name='JsonPathFull',
                    in_rel=[DataTypes.string, DataTypes.string],
                    out_rel=lambda arity: [DataTypes.string] * arity,
                    )
