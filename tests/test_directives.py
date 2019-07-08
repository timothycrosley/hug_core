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
__hug_core__ = __hug_core__  # noqa


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

    @hug_core.get()
    @hug_core.local()
    def timer_tester(hug_core_timer):
        return hug_core_timer

    assert isinstance(hug_core.test.get(api, "timer_tester").data, float)
    assert isinstance(timer_tester(), hug_core.directives.Timer)


def test_module():
    """Test to ensure the module directive automatically includes the current API's module"""

    @hug_core.get()
    def module_tester(hug_core_module):
        return hug_core_module.__name__

    assert hug_core.test.get(api, "module_tester").data == api.module.__name__


def test_api():
    """Ensure the api correctly gets passed onto a hug_core API function based on a directive"""

    @hug_core.get()
    def api_tester(hug_core_api):
        return hug_core_api == api

    assert hug_core.test.get(api, "api_tester").data is True


def test_documentation():
    """Test documentation directive"""
    assert "handlers" in hug_core.directives.documentation(api=api)


def test_api_version():
    """Ensure that it's possible to get the current version of an API based on a directive"""

    @hug_core.get(versions=1)
    def version_tester(hug_core_api_version):
        return hug_core_api_version

    assert hug_core.test.get(api, "v1/version_tester").data == 1


def test_current_api():
    """Ensure that it's possible to retrieve methods from the same version of the API"""

    @hug_core.get(versions=1)
    def first_method():
        return "Success"

    @hug_core.get(versions=1)
    def version_call_tester(hug_core_current_api):
        return hug_core_current_api.first_method()

    assert hug_core.test.get(api, "v1/version_call_tester").data == "Success"

    @hug_core.get()
    def second_method():
        return "Unversioned"

    @hug_core.get(versions=2)  # noqa
    def version_call_tester(hug_core_current_api):
        return hug_core_current_api.second_method()

    assert hug_core.test.get(api, "v2/version_call_tester").data == "Unversioned"

    @hug_core.get(versions=3)  # noqa
    def version_call_tester(hug_core_current_api):
        return hug_core_current_api.first_method()

    with pytest.raises(AttributeError):
        hug_core.test.get(api, "v3/version_call_tester").data


def test_user():
    """Ensure that it's possible to get the current authenticated user based on a directive"""
    user = "test_user"
    password = "super_secret"

    @hug_core.get(requires=hug_core.authentication.basic(hug_core.authentication.verify(user, password)))
    def authenticated_hello(hug_core_user):
        return hug_core_user

    token = b64encode("{0}:{1}".format(user, password).encode("utf8")).decode("utf8")
    assert (
        hug_core.test.get(
            api, "authenticated_hello", headers={"Authorization": "Basic {0}".format(token)}
        ).data
        == user
    )


def test_session_directive():
    """Ensure that it's possible to retrieve the session withing a request using the built-in session directive"""

    @hug_core.request_middleware()
    def add_session(request, response):
        request.context["session"] = {"test": "data"}

    @hug_core.local()
    @hug_core.get()
    def session_data(hug_core_session):
        return hug_core_session

    assert session_data() is None
    assert hug_core.test.get(api, "session_data").data == {"test": "data"}


def test_named_directives():
    """Ensure that it's possible to attach directives to named parameters"""

    @hug_core.get()
    def test(time: hug_core.directives.Timer = 3):
        return time

    assert isinstance(test(1), int)

    test = hug_core.local()(test)
    assert isinstance(test(), hug_core.directives.Timer)


def test_local_named_directives():
    """Ensure that it's possible to attach directives to local function calling"""

    @hug_core.local()
    def test(time: __hug_core__.directive("timer") = 3):
        return time

    assert isinstance(test(), hug_core.directives.Timer)

    @hug_core.local(directives=False)
    def test(time: __hug_core__.directive("timer") = 3):
        return time

    assert isinstance(test(3), int)


def test_named_directives_by_name():
    """Ensure that it's possible to attach directives to named parameters using only the name of the directive"""

    @hug_core.get()
    @hug_core.local()
    def test(time: __hug_core__.directive("timer") = 3):
        return time

    assert isinstance(test(), hug_core.directives.Timer)


def test_per_api_directives():
    """Test to ensure it's easy to define a directive within an API"""

    @hug_core.directive(apply_globally=False)
    def test(default=None, **kwargs):
        return default

    @hug_core.get()
    def my_api_method(hug_core_test="heyyy"):
        return hug_core_test

    assert hug_core.test.get(api, "my_api_method").data == "heyyy"


def test_user_directives():
    """Test the user directives functionality, to ensure it will provide the set user object"""

    @hug_core.get()  # noqa
    def try_user(user: hug_core.directives.user):
        return user

    assert hug_core.test.get(api, "try_user").data is None

    @hug_core.get(
        requires=hug_core.authentication.basic(hug_core.authentication.verify("Tim", "Custom password"))
    )  # noqa
    def try_user(user: hug_core.directives.user):
        return user

    token = b"Basic " + b64encode("{0}:{1}".format("Tim", "Custom password").encode("utf8"))
    assert hug_core.test.get(api, "try_user", headers={"Authorization": token}).data == "Tim"


def test_directives(hug_core_api):
    """Test to ensure cors directive works as expected"""
    assert hug_core.directives.cors("google.com") == "google.com"

    @hug_core.get(api=hug_core_api)
    def cors_supported(cors: hug_core.directives.cors = "*"):
        return True

    assert (
        hug_core.test.get(hug_core_api, "cors_supported").headers_dict["Access-Control-Allow-Origin"] == "*"
    )
