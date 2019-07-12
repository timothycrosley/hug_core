"""tests/test_directives.py.

Tests to ensure that directives interact in the anticipated manner

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
from base64 import b64encode

import pytest

import hug_core

api = hug_core.API(__name__)

# Fix flake8 undefined names (F821)
__hug__ = __hug__  # noqa


def test_timer():
    """Tests that the timer directive outputs the correct format, and automatically attaches itself to an API"""
    timer = hug_core.directives.Timer()
    assert isinstance(timer.start, float)
    assert isinstance(float(timer), float)
    assert isinstance(int(timer), int)

    timer = hug_core.directives.Timer(3)
    assert isinstance(timer.start, float)
    assert isinstance(float(timer), float)
    assert isinstance(int(timer), int)
    assert isinstance(str(timer), str)
    assert isinstance(repr(timer), str)
    assert float(timer) < timer.start

    @hug_core.local()
    def timer_tester(hug_timer):
        return hug_timer

    assert isinstance(timer_tester(), hug_core.directives.Timer)


def test_module():
    """Test to ensure the module directive automatically includes the current API's module"""

    @hug_core.local()
    def module_tester(hug_module):
        return hug_module.__name__

    assert module_tester() == api.module.__name__


def test_api():
    """Ensure the api correctly gets passed onto a hug_core API function based on a directive"""

    @hug_core.local()
    def api_tester(hug_api):
        return hug_api == api

    assert api_tester() is True


def test_documentation():
    """Test documentation directive"""
    assert "handlers" in hug_core.directives.documentation(api=api)


#def test_api_version():
    #"""Ensure that it's possible to get the current version of an API based on a directive"""

    #@hug_core.local(versions=1)
    #def version_tester(hug_api_version):
        #return hug_api_version

    #assert version_tester() == 1


def test_current_api():
    """Ensure that it's possible to retrieve methods from the same version of the API"""

    @hug_core.local(versions=1)
    def first_method():
        return "Success"

    @hug_core.local(versions=1)
    def version_call_tester(hug_current_api):
        return hug_current_api.first_method()

    assert version_call_tester() == "Success"

    @hug_core.local()
    def second_method():
        return "Unversioned"

    @hug_core.local(versions=2)  # noqa
    def version_call_tester(hug_current_api):
        return hug_current_api.second_method()

    assert version_call_tester() == "Unversioned"

    @hug_core.local(versions=3)  # noqa
    def version_call_tester3(hug_current_api):
        return hug_current_api.first_method()

    with pytest.raises(AttributeError):
        version_call_tester3()


def test_named_directives():
    """Ensure that it's possible to attach directives to named parameters"""

    @hug_core.local()
    def test(time: hug_core.directives.Timer = 3):
        return time

    assert isinstance(test(1), int)

    test = hug_core.local()(test)
    assert isinstance(test(), hug_core.directives.Timer)


def test_local_named_directives():
    """Ensure that it's possible to attach directives to local function calling"""

    @hug_core.local()
    def test(time: __hug__.directive("timer") = 3):
        return time

    assert isinstance(test(), hug_core.directives.Timer)

    @hug_core.local(directives=False)
    def test(time: __hug__.directive("timer") = 3):
        return time

    assert isinstance(test(3), int)


def test_named_directives_by_name():
    """Ensure that it's possible to attach directives to named parameters using only the name of the directive"""

    @hug_core.local()
    @hug_core.local()
    def test(time: __hug__.directive("timer") = 3):
        return time

    assert isinstance(test(), hug_core.directives.Timer)


def test_per_api_directives():
    """Test to ensure it's easy to define a directive within an API"""

    @hug_core.directive(apply_globally=False)
    def test(default=None, **kwargs):
        return default

    @hug_core.local()
    def my_api_method(hug_test="heyyy"):
        return hug_test

    assert my_api_method() == "heyyy"

