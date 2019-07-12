"""tests/test_api.py.

Tests to ensure the API object that stores the state of each individual hug_core endpoint works as expected

Copyright (C) 2016 Timothy Edmund Crosley

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

"""
import pytest

import hug_core

api = hug_core.API(__name__)


class TestAPI(object):
    """A collection of tests to ensure the hug_core API object interacts as expected"""

    def test_singleton(self):
        """Test to ensure there can only be one hug_core API per module"""
        assert hug_core.API(__name__) == api

    def test_context(self):
        """Test to ensure the hug_core singleton provides a global modifiable context"""
        assert not hasattr(hug_core.API(__name__), "_context")
        assert hug_core.API(__name__).context == {}
        assert hasattr(hug_core.API(__name__), "_context")

    def test_dynamic(self):
        """Test to ensure it's possible to dynamically create new modules to house APIs based on name alone"""
        new_api = hug_core.API("module_created_on_the_fly")
        assert new_api.module.__name__ == "module_created_on_the_fly"
        import module_created_on_the_fly

        assert module_created_on_the_fly
        assert module_created_on_the_fly.__hug__ == new_api


def test_from_object():
    """Test to ensure it's possible to rechieve an API singleton from an arbitrary object"""
    assert hug_core.api.from_object(TestAPI) == api


def test_api_fixture(hug_core_api):
    """Ensure it's possible to dynamically insert a new hug_core API on demand"""
    assert isinstance(hug_core_api, hug_core.API)
    assert hug_core_api != api


def test_anonymous():
    """Ensure it's possible to create anonymous APIs"""
    assert hug_core.API() != hug_core.API() != api
    assert hug_core.API().module == None
    assert hug_core.API().name == ""
    assert hug_core.API(name="my_name").name == "my_name"
    assert hug_core.API(doc="Custom documentation").doc == "Custom documentation"
