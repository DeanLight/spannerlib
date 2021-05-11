from jsonpath_ng import parse
import json
from rgxlog.engine.datatypes.primitive_types import DataTypes


def json_path(json_document: str, path_expression: str):
    """
    Args:
        json_document: The document on which we will run the path expression
        path_expression: The query to execute.

    Returns: json documents
    """
    # covert string to actual json
    # json library demands the input string to be enclosed in double quotes, therefor we replace...
    json_document = json.loads(json_document.replace("'", "\""))
    jsonpath_expr = parse(path_expression)
    for match in jsonpath_expr.find(json_document):
        json_result = match.value
        if type(json_result) != str:
            # we replace for the same reason as before.
            json_result = json.dumps(json_result).replace("\"", "'")
        # each json result is a relation
        yield json_result,


JsonPath = dict(ie_function=json_path,
                ie_function_name='JsonPath',
                in_rel=[DataTypes.string, DataTypes.string],
                out_rel=[DataTypes.string],
                )

