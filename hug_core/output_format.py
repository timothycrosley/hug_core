"""hug/output_format.py

Defines Hug's built-in output formatting methods

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

import base64
import mimetypes
import os
import re
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import wraps
from io import BytesIO
from operator import itemgetter
from uuid import UUID

from hug import introspect
from hug.format import camelcase, content_type
from hug.json_module import json as json_converter

try:
    import numpy
except ImportError:
    numpy = False

json_converters = {}
stream = tempfile.NamedTemporaryFile if "UWSGI_ORIGINAL_PROC_NAME" in os.environ else BytesIO


def _json_converter(item):
    if hasattr(item, "__native_types__"):
        return item.__native_types__()

    for kind, transformer in json_converters.items():
        if isinstance(item, kind):
            return transformer(item)

    if isinstance(item, (date, datetime)):
        return item.isoformat()
    elif isinstance(item, bytes):
        try:
            return item.decode("utf8")
        except UnicodeDecodeError:
            return base64.b64encode(item)
    elif hasattr(item, "__iter__"):
        return list(item)
    elif isinstance(item, (Decimal, UUID)):
        return str(item)
    elif isinstance(item, timedelta):
        return item.total_seconds()
    raise TypeError("Type not serializable")


def json_convert(*kinds):
    """Registers the wrapped method as a JSON converter for the provided types.

    NOTE: custom converters are always globally applied
    """

    def register_json_converter(function):
        for kind in kinds:
            json_converters[kind] = function
        return function

    return register_json_converter


if numpy:

    @json_convert(numpy.ndarray)
    def numpy_listable(item):
        return item.tolist()

    @json_convert(str, numpy.unicode_)
    def numpy_stringable(item):
        return str(item)

    @json_convert(numpy.bytes_)
    def numpy_byte_decodeable(item):
        return item.decode()

    @json_convert(numpy.bool_)
    def numpy_boolable(item):
        return bool(item)

    @json_convert(numpy.integer)
    def numpy_integerable(item):
        return int(item)

    @json_convert(float, numpy.floating)
    def numpy_floatable(item):
        return float(item)


@content_type("application/json; charset=utf-8")
def json(content, request=None, response=None, ensure_ascii=False, **kwargs):
    """JSON (Javascript Serialized Object Notation)"""
    if hasattr(content, "read"):
        return content

    if isinstance(content, tuple) and getattr(content, "_fields", None):
        content = {field: getattr(content, field) for field in content._fields}
    return json_converter.dumps(
        content, default=_json_converter, ensure_ascii=ensure_ascii, **kwargs
    ).encode("utf8")


def on_valid(valid_content_type, on_invalid=json):
    """Renders as the specified content type only if no errors are found in the provided data object"""
    invalid_kwargs = introspect.generate_accepted_kwargs(on_invalid, "request", "response")
    invalid_takes_response = introspect.takes_all_arguments(on_invalid, "response")

    def wrapper(function):
        valid_kwargs = introspect.generate_accepted_kwargs(function, "request", "response")
        valid_takes_response = introspect.takes_all_arguments(function, "response")

        @content_type(valid_content_type)
        @wraps(function)
        def output_content(content, response, **kwargs):
            if type(content) == dict and "errors" in content:
                response.content_type = on_invalid.content_type
                if invalid_takes_response:
                    kwargs["response"] = response
                return on_invalid(content, **invalid_kwargs(kwargs))

            if valid_takes_response:
                kwargs["response"] = response
            return function(content, **valid_kwargs(kwargs))

        return output_content

    return wrapper


@content_type("text/plain; charset=utf-8")
def text(content, **kwargs):
    """Free form UTF-8 text"""
    if hasattr(content, "read"):
        return content

    return str(content).encode("utf8")


@content_type("text/html; charset=utf-8")
def html(content, **kwargs):
    """HTML (Hypertext Markup Language)"""
    if hasattr(content, "read"):
        return content
    elif hasattr(content, "render"):
        return content.render().encode("utf8")

    return str(content).encode("utf8")


def _camelcase(content):
    if isinstance(content, dict):
        new_dictionary = {}
        for key, value in content.items():
            if isinstance(key, str):
                key = camelcase(key)
            new_dictionary[key] = _camelcase(value)
        return new_dictionary
    elif isinstance(content, list):
        new_list = []
        for element in content:
            new_list.append(_camelcase(element))
        return new_list
    else:
        return content


@content_type("application/json; charset=utf-8")
def json_camelcase(content, **kwargs):
    """JSON (Javascript Serialized Object Notation) with all keys camelCased"""
    return json(_camelcase(content), **kwargs)


@content_type("application/json; charset=utf-8")
def pretty_json(content, **kwargs):
    """JSON (Javascript Serialized Object Notion) pretty printed and indented"""
    return json(content, indent=4, separators=(",", ": "), **kwargs)
