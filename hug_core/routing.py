"""hug_core/routing.py

Defines the chainable classes responsible for defining the routing of Python functions for use with Falcon
and CLIs

Copyright (C) 2016  Timothy Edmund Crosley

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
from __future__ import absolute_import

import os
import re
from collections import OrderedDict
from functools import wraps
from urllib.parse import urljoin

import falcon
from falcon import HTTP_METHODS

import hug_core.api
import hug_core.interface
import hug_core.output_format
from hug_core import introspect
from hug_core.exceptions import InvalidTypeData


class Router(object):
    """The base chainable router object"""

    __slots__ = ("route",)

    def __init__(
        self,
        transform=None,
        output=None,
        validate=None,
        api=None,
        requires=(),
        map_params=None,
        args=None,
        **kwargs
    ):
        self.route = {}
        if transform is not None:
            self.route["transform"] = transform
        if output:
            self.route["output"] = output
        if validate:
            self.route["validate"] = validate
        if api:
            self.route["api"] = api
        if requires:
            self.route["requires"] = (
                (requires,) if not isinstance(requires, (tuple, list)) else requires
            )
        if map_params:
            self.route["map_params"] = map_params
        if args:
            self.route["args"] = args

    def output(self, formatter, **overrides):
        """Sets the output formatter that should be used to render this route"""
        return self.where(output=formatter, **overrides)

    def transform(self, function, **overrides):
        """Sets the function that should be used to transform the returned Python structure into something
           serializable by specified output format
        """
        return self.where(transform=function, **overrides)

    def validate(self, validation_function, **overrides):
        """Sets the secondary validation fucntion to use for this handler"""
        return self.where(validate=validation_function, **overrides)

    def api(self, api, **overrides):
        """Sets the API that should contain this route"""
        return self.where(api=api, **overrides)

    def requires(self, requirements, **overrides):
        """Adds additional requirements to the specified route"""
        return self.where(
            requires=tuple(self.route.get("requires", ())) + tuple(requirements), **overrides
        )

    def doesnt_require(self, requirements, **overrides):
        """Removes individual requirements while keeping all other defined ones within a route"""
        return self.where(
            requires=tuple(
                set(self.route.get("requires", ())).difference(
                    requirements if type(requirements) in (list, tuple) else (requirements,)
                )
            )
        )

    def map_params(self, **map_params):
        """Map interface specific params to an internal name representation"""
        return self.where(map_params=map_params)

    def where(self, **overrides):
        """Creates a new route, based on the current route, with the specified overrided values"""
        route_data = self.route.copy()
        route_data.update(overrides)
        return self.__class__(**route_data)


class InternalValidation(Router):
    """Defines the base route for interfaces that define their own internal validation"""

    __slots__ = ()

    def __init__(self, raise_on_invalid=False, on_invalid=None, output_invalid=None, **kwargs):
        super().__init__(**kwargs)
        if raise_on_invalid:
            self.route["raise_on_invalid"] = raise_on_invalid
        if on_invalid is not None:
            self.route["on_invalid"] = on_invalid
        if output_invalid is not None:
            self.route["output_invalid"] = output_invalid

    def raise_on_invalid(self, setting=True, **overrides):
        """Sets the route to raise validation errors instead of catching them"""
        return self.where(raise_on_invalid=setting, **overrides)

    def on_invalid(self, function, **overrides):
        """Sets a function to use to transform data on validation errors.

        Defaults to the transform function if one is set to ensure no special
        handling occurs for invalid data set to `False`.
        """
        return self.where(on_invalid=function, **overrides)

    def output_invalid(self, output_handler, **overrides):
        """Sets an output handler to be used when handler validation fails.

        Defaults to the output formatter set globally for the route.
        """
        return self.where(output_invalid=output_handler, **overrides)


class LocalRouter(InternalValidation):
    """The LocalRouter defines how interfaces should be handled when accessed locally from within Python code"""

    __slots__ = ()

    def __init__(self, directives=True, validate=True, version=None, **kwargs):
        super().__init__(**kwargs)
        if version is not None:
            self.route["version"] = version
        if not directives:
            self.route["skip_directives"] = True
        if not validate:
            self.route["skip_validation"] = True

    def directives(self, use=True, **kwargs):
        return self.where(directives=use)

    def validate(self, enforce=True, **kwargs):
        return self.where(validate=enforce)

    def version(self, supported, **kwargs):
        return self.where(version=supported)

    def __call__(self, api_function):
        """Enables exposing a hug_core compatible function locally"""
        return hug_core.interface.Local(self.route, api_function)

