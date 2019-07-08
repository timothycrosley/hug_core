"""hug_core/interface.py

Defines the various interface hug_core provides to expose routes to functions

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

import argparse
import asyncio
import os
import sys
from collections import OrderedDict
from functools import lru_cache, partial, wraps

import falcon
from falcon import HTTP_BAD_REQUEST

import hug_core._empty as empty
import hug_core.api
import hug_core.output_format
import hug_core.types as types
from hug_core import introspect
from hug_core.exceptions import InvalidTypeData
from hug_core.format import parse_content_type
from hug_core.types import (
    MarshmallowInputSchema,
    MarshmallowReturnSchema,
    Multiple,
    OneOf,
    SmartBoolean,
    Text,
    text,
)


def asyncio_call(function, *args, **kwargs):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return function(*args, **kwargs)

    function = asyncio.ensure_future(function(*args, **kwargs), loop=loop)
    loop.run_until_complete(function)
    return function.result()


class Interfaces(object):
    """Defines the per-function singleton applied to hug_coreged functions defining common data needed by all interfaces"""

    def __init__(self, function, args=None):
        self.api = hug_core.api.from_object(function)
        self.spec = getattr(function, "original", function)
        self.arguments = introspect.arguments(function)
        self.name = introspect.name(function)
        self._function = function

        self.is_coroutine = introspect.is_coroutine(self.spec)
        if self.is_coroutine:
            self.spec = getattr(self.spec, "__wrapped__", self.spec)

        self.takes_args = introspect.takes_args(self.spec)
        self.takes_kwargs = introspect.takes_kwargs(self.spec)

        self.parameters = list(introspect.arguments(self.spec, self.takes_kwargs + self.takes_args))
        if self.takes_kwargs:
            self.kwarg = self.parameters.pop(-1)
        if self.takes_args:
            self.arg = self.parameters.pop(-1)
        self.parameters = tuple(self.parameters)
        self.defaults = dict(zip(reversed(self.parameters), reversed(self.spec.__defaults__ or ())))
        self.required = self.parameters[: -(len(self.spec.__defaults__ or ())) or None]
        self.is_method = introspect.is_method(self.spec) or introspect.is_method(function)
        if self.is_method:
            self.required = self.required[1:]
            self.parameters = self.parameters[1:]

        self.all_parameters = set(self.parameters)
        if self.spec is not function:
            self.all_parameters.update(self.arguments)

        if args is not None:
            transformers = args
        else:
            transformers = self.spec.__annotations__

        self.transform = transformers.get("return", None)
        self.directives = {}
        self.input_transformations = {}
        for name, transformer in transformers.items():
            if isinstance(transformer, str):
                continue
            elif hasattr(transformer, "directive"):
                self.directives[name] = transformer
                continue

            if hasattr(transformer, "from_string"):
                transformer = transformer.from_string
            elif hasattr(transformer, "load"):
                transformer = MarshmallowInputSchema(transformer)
            elif hasattr(transformer, "deserialize"):
                transformer = transformer.deserialize

            self.input_transformations[name] = transformer

    def __call__(__hug_core_internal_self, *args, **kwargs):  # noqa: N805
        """"Calls the wrapped function, uses __hug_core_internal_self incase self is passed in as a kwarg from the wrapper"""
        if not __hug_core_internal_self.is_coroutine:
            return __hug_core_internal_self._function(*args, **kwargs)

        return asyncio_call(__hug_core_internal_self._function, *args, **kwargs)


class Interface(object):
    """Defines the basic hug_core interface object, which is responsible for wrapping a user defined function and providing
       all the info requested in the function as well as the route

       A Interface object should be created for every kind of protocal hug_core supports
    """

    __slots__ = (
        "interface",
        "_api",
        "defaults",
        "parameters",
        "required",
        "_outputs",
        "on_invalid",
        "requires",
        "validate_function",
        "transform",
        "examples",
        "output_doc",
        "wrapped",
        "directives",
        "all_parameters",
        "raise_on_invalid",
        "invalid_outputs",
        "map_params",
        "input_transformations",
    )

    def __init__(self, route, function):
        if route.get("api", None):
            self._api = route["api"]
        if "examples" in route:
            self.examples = route["examples"]
        function_args = route.get("args")
        if not hasattr(function, "interface"):
            function.__dict__["interface"] = Interfaces(function, function_args)

        self.interface = function.interface
        self.requires = route.get("requires", ())
        if "validate" in route:
            self.validate_function = route["validate"]
        if "output_invalid" in route:
            self.invalid_outputs = route["output_invalid"]

        if not "parameters" in route:
            self.defaults = self.interface.defaults
            self.parameters = self.interface.parameters
            self.all_parameters = self.interface.all_parameters
            self.required = self.interface.required
        else:
            self.defaults = route.get("defaults", {})
            self.parameters = tuple(route["parameters"])
            self.all_parameters = set(route["parameters"])
            self.required = tuple(
                [parameter for parameter in self.parameters if parameter not in self.defaults]
            )

        if "map_params" in route:
            self.map_params = route["map_params"]
            for interface_name, internal_name in self.map_params.items():
                if internal_name in self.defaults:
                    self.defaults[interface_name] = self.defaults.pop(internal_name)
                if internal_name in self.parameters:
                    self.parameters = [
                        interface_name if param == internal_name else param
                        for param in self.parameters
                    ]
                if internal_name in self.all_parameters:
                    self.all_parameters.remove(internal_name)
                    self.all_parameters.add(interface_name)
                if internal_name in self.required:
                    self.required = tuple(
                        [
                            interface_name if param == internal_name else param
                            for param in self.required
                        ]
                    )

            reverse_mapping = {
                internal: interface for interface, internal in self.map_params.items()
            }
            self.input_transformations = {
                reverse_mapping.get(name, name): transform
                for name, transform in self.interface.input_transformations.items()
            }
        else:
            self.map_params = {}
            self.input_transformations = self.interface.input_transformations

        if "output" in route:
            self.outputs = route["output"]

        self.transform = route.get("transform", None)
        if self.transform is None and not isinstance(self.interface.transform, (str, type(None))):
            self.transform = self.interface.transform

        if hasattr(self.transform, "dump"):
            self.transform = MarshmallowReturnSchema(self.transform)
            self.output_doc = self.transform.__doc__
        elif self.transform or self.interface.transform:
            output_doc = self.transform or self.interface.transform
            self.output_doc = output_doc if type(output_doc) is str else output_doc.__doc__

        self.raise_on_invalid = route.get("raise_on_invalid", False)
        if "on_invalid" in route:
            self.on_invalid = route["on_invalid"]
        elif self.transform:
            self.on_invalid = self.transform

        defined_directives = self.api.directives()
        used_directives = set(self.parameters).intersection(defined_directives)
        self.directives = {
            directive_name: defined_directives[directive_name] for directive_name in used_directives
        }
        self.directives.update(self.interface.directives)

    @property
    def api(self):
        return getattr(self, "_api", self.interface.api)

    @property
    def outputs(self):
        return getattr(self, "_outputs", None)

    @outputs.setter
    def outputs(self, outputs):
        self._outputs = outputs  # pragma: no cover - generally re-implemented by sub classes

    def validate(self, input_parameters, context):
        """Runs all set type transformers / validators against the provided input parameters and returns any errors"""
        errors = {}

        for key, type_handler in self.input_transformations.items():
            if self.raise_on_invalid:
                if key in input_parameters:
                    input_parameters[key] = self.initialize_handler(
                        type_handler, input_parameters[key], context=context
                    )
            else:
                try:
                    if key in input_parameters:
                        input_parameters[key] = self.initialize_handler(
                            type_handler, input_parameters[key], context=context
                        )
                except InvalidTypeData as error:
                    errors[key] = error.reasons or str(error)
                except Exception as error:
                    if hasattr(error, "args") and error.args:
                        errors[key] = error.args[0]
                    else:
                        errors[key] = str(error)
        for require in self.required:
            if not require in input_parameters:
                errors[require] = "Required parameter '{}' not supplied".format(require)
        if not errors and getattr(self, "validate_function", False):
            errors = self.validate_function(input_parameters)
        return errors

    def check_requirements(self, request=None, response=None, context=None):
        """Checks to see if all requirements set pass

           if all requirements pass nothing will be returned
           otherwise, the error reported will be returned
        """
        for requirement in self.requires:
            conclusion = requirement(
                response=response, request=request, context=context, module=self.api.module
            )
            if conclusion and conclusion is not True:
                return conclusion

    def documentation(self, add_to=None):
        """Produces general documentation for the interface"""
        doc = OrderedDict if add_to is None else add_to

        usage = self.interface.spec.__doc__
        if usage:
            doc["usage"] = usage
        if getattr(self, "requires", None):
            doc["requires"] = [
                getattr(requirement, "__doc__", requirement.__name__)
                for requirement in self.requires
            ]
        doc["outputs"] = OrderedDict()
        doc["outputs"]["format"] = self.outputs.__doc__
        doc["outputs"]["content_type"] = self.outputs.content_type
        parameters = [
            param
            for param in self.parameters
            if not param in ("request", "response", "self")
            and not param in ("api_version", "body")
            and not param.startswith("hug_core_")
            and not hasattr(param, "directive")
        ]
        if parameters:
            inputs = doc.setdefault("inputs", OrderedDict())
            types = self.interface.spec.__annotations__
            for argument in parameters:
                kind = types.get(self._remap_entry(argument), text)
                if getattr(kind, "directive", None) is True:
                    continue

                input_definition = inputs.setdefault(argument, OrderedDict())
                input_definition["type"] = kind if isinstance(kind, str) else kind.__doc__
                default = self.defaults.get(argument, None)
                if default is not None:
                    input_definition["default"] = default

        return doc

    def _rewrite_params(self, params):
        for interface_name, internal_name in self.map_params.items():
            if interface_name in params:
                params[internal_name] = params.pop(interface_name)

    def _remap_entry(self, interface_name):
        return self.map_params.get(interface_name, interface_name)

    @staticmethod
    def cleanup_parameters(parameters, exception=None):
        for _parameter, directive in parameters.items():
            if hasattr(directive, "cleanup"):
                directive.cleanup(exception=exception)

    @staticmethod
    def initialize_handler(handler, value, context):
        try:  # It's easier to ask for forgiveness than for permission
            return handler(value, context=context)
        except TypeError:
            return handler(value)


class Local(Interface):
    """Defines the Interface responsible for exposing functions locally"""

    __slots__ = ("skip_directives", "skip_validation", "version")

    def __init__(self, route, function):
        super().__init__(route, function)
        self.version = route.get("version", None)
        if "skip_directives" in route:
            self.skip_directives = True
        if "skip_validation" in route:
            self.skip_validation = True

        self.interface.local = self

    def __get__(self, instance, kind):
        """Support instance methods"""
        return partial(self.__call__, instance) if instance else self.__call__

    @property
    def __name__(self):
        return self.interface.spec.__name__

    @property
    def __module__(self):
        return self.interface.spec.__module__

    def __call__(self, *args, **kwargs):
        context = self.api.context_factory(api=self.api, api_version=self.version, interface=self)
        """Defines how calling the function locally should be handled"""

        for _requirement in self.requires:
            lacks_requirement = self.check_requirements(context=context)
            if lacks_requirement:
                self.api.delete_context(context, lacks_requirement=lacks_requirement)
                return self.outputs(lacks_requirement) if self.outputs else lacks_requirement

        for index, argument in enumerate(args):
            kwargs[self.parameters[index]] = argument

        if not getattr(self, "skip_directives", False):
            for parameter, directive in self.directives.items():
                if parameter in kwargs:
                    continue
                arguments = (self.defaults[parameter],) if parameter in self.defaults else ()
                kwargs[parameter] = directive(
                    *arguments,
                    api=self.api,
                    api_version=self.version,
                    interface=self,
                    context=context
                )

        if not getattr(self, "skip_validation", False):
            errors = self.validate(kwargs, context)
            if errors:
                errors = {"errors": errors}
                if getattr(self, "on_invalid", False):
                    errors = self.on_invalid(errors)
                outputs = getattr(self, "invalid_outputs", self.outputs)
                self.api.delete_context(context, errors=errors)
                return outputs(errors) if outputs else errors

        self._rewrite_params(kwargs)
        try:
            result = self.interface(**kwargs)
            if self.transform:
                if hasattr(self.transform, "context"):
                    self.transform.context = context
                result = self.transform(result)
        except Exception as exception:
            self.cleanup_parameters(kwargs, exception=exception)
            self.api.delete_context(context, exception=exception)
            raise exception
        self.cleanup_parameters(kwargs)
        self.api.delete_context(context)
        return self.outputs(result) if self.outputs else result
