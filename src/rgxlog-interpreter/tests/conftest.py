"""
this is the settings file for pytest
use `pytest --log_level=INFO` to set the logging level to INFO
use `pytest -s -m "not long"` to run all short tests, and print outputs to screen
"""
from typing import Iterable

import pytest


@pytest.fixture(autouse=True)
def run_on_every_test() -> Iterable:
    # this code runs before each test is executed
    pass

    yield
    # this code runs after each test is executed
    pass
