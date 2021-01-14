from enum import Enum, auto


class Request(Enum):
    QUERY = auto()
    IE_REGISTRATION = auto()
    CURRENT_STACK = auto()
    SET_STACK = auto()


class Response(Enum):
    SUCCESS = auto()
    FAILURE = auto()
