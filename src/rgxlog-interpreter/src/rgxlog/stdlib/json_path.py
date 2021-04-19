from jsonpath_ng import parse
import json
from rgxlog.engine.datatypes.primitive_types import DataTypes


def json_path(json_ds: str, json_query: str):
    json_ds = json.loads(json_ds.replace("'", "\""))                  # covert string to actual json
    jsonpath_expr = parse(json_query)
    for match in jsonpath_expr.find(json_ds):
        json_result = match.value
        if type(json_result) != str:
            json_result = json.dumps(json_result).replace("\"", "'")

        yield [json_result]                        # each json result is a relation


json_path = dict(ie_function=json_path,
                 ie_function_name='JsonPath',
                 in_rel=[DataTypes.string, DataTypes.string],
                 out_rel=[DataTypes.string],
                 )

