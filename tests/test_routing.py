"""tests/test_output_format.py

Tests that the hug_core routing functionality works as expected

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
import hug_core
from hug_core.routing import (
    LocalRouter,
    InternalValidation,
    Router,
)

api = hug_core.API(__name__)


class TestRouter(object):
    """A collection of tests to ensure the base Router object works as expected"""

    route = Router(transform="transform", output="output")

    def test_init(self):
        """Test to ensure the route instanciates as expected"""
        assert self.route.route["transform"] == "transform"
        assert self.route.route["output"] == "output"
        assert "api" not in self.route.route

    def test_output(self):
        """Test to ensure modifying the output argument has the desired effect"""
        new_route = self.route.output("test data", transform="transformed")
        assert new_route != self.route
        assert new_route.route["output"] == "test data"
        assert new_route.route["transform"] == "transformed"

    def test_transform(self):
        """Test to ensure changing the transformation on the fly works as expected"""
        new_route = self.route.transform("transformed")
        assert new_route != self.route
        assert new_route.route["transform"] == "transformed"

    def test_validate(self):
        """Test to ensure overriding the secondary validation method works as expected"""
        assert self.route.validate(str).route["validate"] == str

    def test_api(self):
        """Test to ensure changing the API associated with the route works as expected"""
        new_route = self.route.api("new")
        assert new_route != self.route
        assert new_route.route["api"] == "new"

    def test_requires(self):
        """Test to ensure requirements can be added on the fly"""
        assert self.route.requires(("values",)).route["requires"] == ("values",)

    def test_map_params(self):
        """Test to ensure it is possible to set param mappings on the routing object"""
        assert self.route.map_params(id="user_id").route["map_params"] == {"id": "user_id"}

    def test_where(self):
        """Test to ensure `where` can be used to replace all arguments on the fly"""
        new_route = self.route.where(transform="transformer", output="outputter")
        assert new_route != self.route
        assert new_route.route["output"] == "outputter"
        assert new_route.route["transform"] == "transformer"


class TestInternalValidation(TestRouter):
    """Collection of tests to ensure the base Router for routes that define internal validation work as expected"""

    route = InternalValidation(name="cli", doc="Hi there!", transform="transform", output="output")

    def test_raise_on_invalid(self):
        """Test to ensure it's possible to set a raise on invalid handler per route"""
        assert "raise_on_invalid" not in self.route.route
        assert self.route.raise_on_invalid().route["raise_on_invalid"]

    def test_on_invalid(self):
        """Test to ensure on_invalid handler can be changed on the fly"""
        assert self.route.on_invalid(str).route["on_invalid"] == str

    def test_output_invalid(self):
        """Test to ensure output_invalid handler can be changed on the fly"""
        assert (
            self.route.output_invalid(hug_core.output_format.json).route["output_invalid"]
            == hug_core.output_format.json
        )


class TestLocalRouter(TestInternalValidation):
    """A collection of tests to ensure the LocalRouter object works as expected"""

    route = LocalRouter(name="cli", doc="Hi there!", transform="transform", output="output")

    def test_validate(self):
        """Test to ensure changing wether a local route should validate or not works as expected"""
        assert "skip_validation" not in self.route.route

        route = self.route.validate()
        assert "skip_validation" not in route.route

        route = self.route.validate(False)
        assert "skip_validation" in route.route

    def test_directives(self):
        """Test to ensure changing wether a local route should supply directives or not works as expected"""
        assert "skip_directives" not in self.route.route

        route = self.route.directives()
        assert "skip_directives" not in route.route

        route = self.route.directives(False)
        assert "skip_directives" in route.route

    def test_version(self):
        """Test to ensure changing the version of a LocalRoute on the fly works"""
        assert "version" not in self.route.route

        route = self.route.version(2)
        assert "version" in route.route
        assert route.route["version"] == 2
