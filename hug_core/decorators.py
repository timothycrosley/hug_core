"""hug_core/decorators.py

Defines the method decorators at the core of Hug's approach to creating HTTP APIs

- Decorators for exposing python method as HTTP methods (get, post, etc)
- Decorators for setting the default output and input formats used throughout an API using the framework
- Decorator for registering a new directive method
- Decorator for including another API modules handlers into the current one, with opitonal prefix route

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

import functools
from collections import namedtuple

import hug_core.api
import hug_core.defaults
import hug_core.output_format
from hug_core import introspect
from hug_core.format import underscore


def default_output_format(
    content_type="application/json", apply_globally=False, api=None, cli=False, http=True
):
    """A decorator that allows you to override the default output format for an API"""

    def decorator(formatter):
        formatter = hug_core.output_format.content_type(content_type)(formatter)
        if apply_globally:
            if http:
                hug_core.defaults.output_format = formatter
            if cli:
                hug_core.defaults.cli_output_format = formatter
        else:
            apply_to_api = hug_core.API(api) if api else hug_core.api.from_object(formatter)
            if http:
                apply_to_api.http.output_format = formatter
            if cli:
                apply_to_api.cli.output_format = formatter
        return formatter

    return decorator


def default_input_format(content_type="application/json", apply_globally=False, api=None):
    """A decorator that allows you to override the default output format for an API"""

    def decorator(formatter):
        formatter = hug_core.output_format.content_type(content_type)(formatter)
        if apply_globally:
            hug_core.defaults.input_format[content_type] = formatter
        else:
            apply_to_api = hug_core.API(api) if api else hug_core.api.from_object(formatter)
            apply_to_api.http.set_input_format(content_type, formatter)
        return formatter

    return decorator


def directive(apply_globally=False, api=None):
    """A decorator that registers a single hug_core directive"""

    def decorator(directive_method):
        if apply_globally:
            hug_core.defaults.directives[underscore(directive_method.__name__)] = directive_method
        else:
            apply_to_api = hug_core.API(api) if api else hug_core.api.from_object(directive_method)
            apply_to_api.add_directive(directive_method)
        directive_method.directive = True
        return directive_method

    return decorator


def context_factory(apply_globally=False, api=None):
    """A decorator that registers a single hug_core context factory"""

    def decorator(context_factory_):
        if apply_globally:
            hug_core.defaults.context_factory = context_factory_
        else:
            apply_to_api = hug_core.API(api) if api else hug_core.api.from_object(context_factory_)
            apply_to_api.context_factory = context_factory_
        return context_factory_

    return decorator


def delete_context(apply_globally=False, api=None):
    """A decorator that registers a single hug_core delete context function"""

    def decorator(delete_context_):
        if apply_globally:
            hug_core.defaults.delete_context = delete_context_
        else:
            apply_to_api = hug_core.API(api) if api else hug_core.api.from_object(delete_context_)
            apply_to_api.delete_context = delete_context_
        return delete_context_

    return decorator


def startup(api=None):
    """Runs the provided function on startup, passing in an instance of the api"""

    def startup_wrapper(startup_function):
        apply_to_api = hug_core.API(api) if api else hug_core.api.from_object(startup_function)
        apply_to_api.add_startup_handler(startup_function)
        return startup_function

    return startup_wrapper


def extend_api(route="", api=None, base_url="", **kwargs):
    """Extends the current api, with handlers from an imported api. Optionally provide a route that prefixes access"""

    def decorator(extend_with):
        apply_to_api = hug_core.API(api) if api else hug_core.api.from_object(extend_with)
        for extended_api in extend_with():
            apply_to_api.extend(extended_api, route, base_url, **kwargs)
        return extend_with

    return decorator


def wraps(function):
    """Enables building decorators around functions used for hug routes without changing their function signature"""

    def wrap(decorator):
        decorator = functools.wraps(function)(decorator)
        if not hasattr(function, "original"):
            decorator.original = function
        else:
            decorator.original = function.original
            delattr(function, "original")
        return decorator

    return wrap


def auto_kwargs(function):
    """Modifies the provided function to support kwargs by only passing along kwargs for parameters it accepts"""
    supported = introspect.arguments(function)

    @wraps(function)
    def call_function(*args, **kwargs):
        return function(*args, **{key: value for key, value in kwargs.items() if key in supported})

    return call_function
