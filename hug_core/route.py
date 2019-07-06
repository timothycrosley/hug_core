"""hug/route.py

Defines user usable routers

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

from functools import partial
from types import FunctionType, MethodType

from falcon import HTTP_METHODS

import hug.api
from hug.routing import CLIRouter as cli  # noqa:  N813
from hug.routing import ExceptionRouter as exception  # noqa:  N813
from hug.routing import LocalRouter as local  # noqa:  N813
from hug.routing import NotFoundRouter as not_found  # noqa:  N813
from hug.routing import SinkRouter as sink  # noqa:  N813
from hug.routing import StaticRouter as static  # noqa:  N813
from hug.routing import URLRouter as http  # noqa:  N813


class Object(http):
    """Defines a router for classes and objects"""

    def __init__(self, urls=None, accept=HTTP_METHODS, output=None, **kwargs):
        super().__init__(urls=urls, accept=accept, output=output, **kwargs)

    def __call__(self, method_or_class=None, **kwargs):
        if not method_or_class and kwargs:
            return self.where(**kwargs)

        if isinstance(method_or_class, (MethodType, FunctionType)):
            routes = getattr(method_or_class, "_hug_http_routes", [])
            routes.append(self.route)
            method_or_class._hug_http_routes = routes
            return method_or_class

        instance = method_or_class
        if isinstance(method_or_class, type):
            instance = method_or_class()

        for argument in dir(instance):
            argument = getattr(instance, argument, None)

            http_routes = getattr(argument, "_hug_http_routes", ())
            for route in http_routes:
                http(**self.where(**route).route)(argument)

            cli_routes = getattr(argument, "_hug_cli_routes", ())
            for route in cli_routes:
                cli(**self.where(**route).route)(argument)

        return method_or_class


object = Object()
