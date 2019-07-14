"""tests/test_output_format.py.

Tests the output format handlers included with Hug

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
import os
from collections import namedtuple
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from uuid import UUID

import numpy
import pytest

import hug_core

from .constants import BASE_DIRECTORY


def test_text():
    """Ensure that it's possible to output a Hug API method as text"""
    hug_core.output_format.text("Hello World!") == "Hello World!"
    hug_core.output_format.text(str(1)) == "1"


def test_html(hug_core_api):
    """Ensure that it's possible to output a Hug API method as HTML"""
    hug_core.output_format.html("<html>Hello World!</html>") == "<html>Hello World!</html>"
    hug_core.output_format.html(str(1)) == "1"
    with open(os.path.join(BASE_DIRECTORY, "README.md"), "rb") as html_file:
        assert hasattr(hug_core.output_format.html(html_file), "read")

    class FakeHTMLWithRender:
        def render(self):
            return "test"

    assert hug_core.output_format.html(FakeHTMLWithRender()) == b"test"

    @hug_core.local(output=hug_core.output_format.html, api=hug_core_api)
    def get_html(**kwargs):
        """
        Returns command help document when no command is specified
        """
        with open(os.path.join(BASE_DIRECTORY, "examples/document.html"), "rb") as html_file:
            return html_file.read()

    assert b"<html>" in get_html()


def test_json():
    """Ensure that it's possible to output a Hug API method as JSON"""
    now = datetime.now()
    one_day = timedelta(days=1)
    test_data = {"text": "text", "datetime": now, "bytes": b"bytes", "delta": one_day}
    output = hug_core.output_format.json(test_data).decode("utf8")
    assert "text" in output
    assert "bytes" in output
    assert str(one_day.total_seconds()) in output
    assert now.isoformat() in output

    class NewObject(object):
        pass

    test_data["non_serializable"] = NewObject()
    with pytest.raises(TypeError):
        hug_core.output_format.json(test_data).decode("utf8")

    class NamedTupleObject(namedtuple("BaseTuple", ("name", "value"))):
        pass

    data = NamedTupleObject("name", "value")
    converted = hug_core.input_format.json(BytesIO(hug_core.output_format.json(data)))
    assert converted == {"name": "name", "value": "value"}

    data = set((1, 2, 3, 3))
    assert hug_core.input_format.json(BytesIO(hug_core.output_format.json(data))) == [1, 2, 3]

    data = (number for number in range(1, 4))
    assert hug_core.input_format.json(BytesIO(hug_core.output_format.json(data))) == [1, 2, 3]

    data = [Decimal(1.5), Decimal("155.23"), Decimal("1234.25")]
    assert hug_core.input_format.json(BytesIO(hug_core.output_format.json(data))) == [
        "1.5",
        "155.23",
        "1234.25",
    ]

    with open(os.path.join(BASE_DIRECTORY, "README.md"), "rb") as json_file:
        assert hasattr(hug_core.output_format.json(json_file), "read")

    assert hug_core.input_format.json(BytesIO(hug_core.output_format.json(b"\x9c"))) == "nA=="

    class MyCrazyObject(object):
        pass

    @hug_core.output_format.json_convert(MyCrazyObject)
    def convert(instance):
        return "Like anyone could convert this"

    assert (
        hug_core.input_format.json(BytesIO(hug_core.output_format.json(MyCrazyObject())))
        == "Like anyone could convert this"
    )
    assert hug_core.input_format.json(
        BytesIO(hug_core.output_format.json({"data": ["Τη γλώσσα μου έδωσαν ελληνική"]}))
    ) == {"data": ["Τη γλώσσα μου έδωσαν ελληνική"]}


def test_pretty_json():
    """Ensure that it's possible to output a Hug API method as prettified and indented JSON"""
    test_data = {"text": "text"}
    assert hug_core.output_format.pretty_json(test_data).decode("utf8") == (
        "{\n" '    "text": "text"\n' "}"
    )


def test_json_camelcase():
    """Ensure that it's possible to output a Hug API method as camelCased JSON"""
    test_data = {
        "under_score": "values_can",
        "be_converted": [{"to_camelcase": "value"}, "wont_be_convert"],
    }
    output = hug_core.output_format.json_camelcase(test_data).decode("utf8")
    assert "underScore" in output
    assert "values_can" in output
    assert "beConverted" in output
    assert "toCamelcase" in output
    assert "value" in output
    assert "wont_be_convert" in output


def test_json_converter_numpy_types():
    """Ensure that numpy-specific data types (array, int, float) are properly supported in JSON output."""
    ex_int = numpy.int_(9)
    ex_np_array = numpy.array([1, 2, 3, 4, 5])
    ex_np_int_array = numpy.int_([5, 4, 3])
    ex_np_float = numpy.float(0.5)

    assert 9 is hug_core.output_format._json_converter(ex_int)
    assert [1, 2, 3, 4, 5] == hug_core.output_format._json_converter(ex_np_array)
    assert [5, 4, 3] == hug_core.output_format._json_converter(ex_np_int_array)
    assert 0.5 == hug_core.output_format._json_converter(ex_np_float)

    # Some type names are merely shorthands.
    # The following shorthands for built-in types are excluded: numpy.bool, numpy.int, numpy.float.
    np_bool_types = [numpy.bool_, numpy.bool8]
    np_int_types = [
        numpy.int_,
        numpy.byte,
        numpy.ubyte,
        numpy.intc,
        numpy.uintc,
        numpy.intp,
        numpy.uintp,
        numpy.int8,
        numpy.uint8,
        numpy.int16,
        numpy.uint16,
        numpy.int32,
        numpy.uint32,
        numpy.int64,
        numpy.uint64,
        numpy.longlong,
        numpy.ulonglong,
        numpy.short,
        numpy.ushort,
    ]
    np_float_types = [
        numpy.float_,
        numpy.float32,
        numpy.float64,
        numpy.half,
        numpy.single,
        numpy.longfloat,
    ]
    np_unicode_types = [numpy.unicode_]
    np_bytes_types = [numpy.bytes_]

    for np_type in np_bool_types:
        assert True == hug_core.output_format._json_converter(np_type(True))
    for np_type in np_int_types:
        assert 1 is hug_core.output_format._json_converter(np_type(1))
    for np_type in np_float_types:
        assert 0.5 == hug_core.output_format._json_converter(np_type(0.5))
    for np_type in np_unicode_types:
        assert "a" == hug_core.output_format._json_converter(np_type("a"))
    for np_type in np_bytes_types:
        assert "a" == hug_core.output_format._json_converter(np_type("a"))


def test_json_converter_uuid():
    """Ensure that uuid data type is properly supported in JSON output."""
    uuidstr = "8ae4d8c1-e2d7-5cd0-8407-6baf16dfbca4"
    assert uuidstr == hug_core.output_format._json_converter(UUID(uuidstr))


def test_output_format_with_no_docstring():
    """Ensure it is safe to use formatters with no docstring"""

    @hug_core.format.content_type("test/fmt")
    def test_fmt(data, request=None, response=None):
        return str(data).encode("utf8")

    assert test_fmt("hi") == b"hi"
