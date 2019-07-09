"""Defines fixtures that can be used to streamline tests and / or define dependencies"""
from collections import namedtuple
from random import randint

import pytest

import hug_core

Routers = namedtuple("Routers", ["http", "local", "cli"])


class TestAPI(hug_core.API):
    pass


@pytest.fixture
def hug_core_api():
    """Defines a dependency for and then includes a uniquely identified hug_core API for a single test case"""
    api = TestAPI("fake_api_{}".format(randint(0, 1000000)))
    api.route = Routers(
        hug_core.routing.LocalRouter().api(api),
    )
    return api


@pytest.fixture
def hug_core_api_error_exit_codes_enabled():
    """
    Defines a dependency for and then includes a uniquely identified hug_core API
    for a single test case with error exit codes enabled.
    """
    return TestAPI("fake_api_{}".format(randint(0, 1000000)), cli_error_exit_codes=True)
