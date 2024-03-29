"""hug_core/input_formats.py

Defines the built-in Hug input_formatting handlers

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

import re
from cgi import parse_multipart
from urllib.parse import parse_qs as urlencoded_converter

from hug_core.format import content_type, underscore
from hug_core.json_module import json as json_converter


@content_type("text/plain")
def text(body, charset="utf-8", **kwargs):
    """Takes plain text data"""
    return body.read().decode(charset)


@content_type("application/json")
def json(body, charset="utf-8", **kwargs):
    """Takes JSON formatted data, converting it into native Python objects"""
    return json_converter.loads(text(body, charset=charset))


def _underscore_dict(dictionary):
    new_dictionary = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = _underscore_dict(value)
        if isinstance(key, str):
            key = underscore(key)
        new_dictionary[key] = value
    return new_dictionary


def json_underscore(body, charset="utf-8", **kwargs):
    """Converts JSON formatted date to native Python objects.

    The keys in any JSON dict are transformed from camelcase to underscore separated words.
    """
    return _underscore_dict(json(body, charset=charset))
