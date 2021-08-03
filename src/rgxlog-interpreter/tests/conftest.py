"""
this is the settings file for pytest
"""

import pytest


@pytest.fixture(autouse=True)
def run_on_every_test():
    # this code runs before each test is executed
    pass

    yield
    # this code runs after each test is executed
    pass
