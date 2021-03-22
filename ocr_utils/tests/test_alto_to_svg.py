#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import Counter
from typing import Counter as CounterType
from typing import List
from xml.etree.ElementTree import Element
import alto

import pytest
from svgwrite.drawing import Drawing
from svgwrite.container import Defs
from svgwrite.shapes import Line, Rect
from ocr_utils.alto_to_svg import (
    Drawable,
    _alto_page_to_lines,
    _create_line,
    _create_rectangle,
    _create_text,
    _draw_elements,
    _generate_svg,
    _line_to_component,
    _pages_to_svg,
)


def _extract_xml_tags(element: Element) -> List[str]:
    return [x.tag for x in element.iter()]


def _draw_and_extract_xml_keys(drawables: List[Drawable]) -> CounterType[str]:
    drawing = Drawing(profile='tiny')
    xml_ = _draw_elements(drawing, drawables).get_xml()
    tags = _extract_xml_tags(xml_)
    return Counter(tags)


def test_create_text():
    drawable = _create_text('test', 10, 10, None, 'black', 10)
    assert _draw_and_extract_xml_keys([drawable])['text'] == 1

    drawable = _create_text('test', 10, 10, None)
    assert _draw_and_extract_xml_keys([drawable])['text'] == 1

    drawable = _create_text('tt', 5, 119, None)
    assert _draw_and_extract_xml_keys([drawable, drawable])['text'] == 2


def test_create_rectangle():
    drawable = _create_rectangle(1, 2, 3, 4)
    assert _draw_and_extract_xml_keys([drawable])['rect'] == 1

    drawable = _create_rectangle(1, 10, 1, 4)
    assert _draw_and_extract_xml_keys([drawable])['rect'] == 1

    drawable = _create_rectangle(1, 2, 3, 6)
    assert _draw_and_extract_xml_keys([drawable, drawable])['rect'] == 2


def test_create_line():
    drawable = _create_line(1, 2, 3, 4)
    assert _draw_and_extract_xml_keys([drawable])['line'] == 1

    drawable = _create_line(1, 10, 1, 4)
    assert _draw_and_extract_xml_keys([drawable])['line'] == 1

    drawable = _create_line(1, 2, 3, 6)
    assert _draw_and_extract_xml_keys([drawable, drawable])['line'] == 2


def test_draw_elements():
    res = _draw_elements(Drawing('tiny'), []).elements
    assert len(res) == 1
    assert isinstance(res[0], Defs)

    drawing = _draw_elements(Drawing('tiny'), [_create_line(1, 2, 3, 4)])
    assert len(drawing.elements) == 2
    assert isinstance(drawing.elements[0], Defs)
    assert isinstance(drawing.elements[1], Line)

    res = _draw_elements(drawing, [_create_rectangle(1, 2, 3, 4)]).elements
    assert len(res) == 3
    assert isinstance(res[0], Defs)
    assert isinstance(res[1], Line)
    assert isinstance(res[2], Rect)


def test_generate_svg():
    res = _generate_svg(1, 10, 10, [])
    assert res.attribs['height'] == '10px'
    assert res.attribs['width'] == '10px'
    assert len(res.elements) == 6

    res = _generate_svg(2, 10, 10, [])
    assert res.attribs['height'] == '10px'
    assert res.attribs['width'] == '10px'
    assert len(res.elements) == 7

    res = _generate_svg(4, 10, 5, [])
    assert res.attribs['height'] == '5px'
    assert res.attribs['width'] == '10px'
    assert len(res.elements) == 9

    res = _generate_svg(4, 10, 5, [_create_text('foo', 1, 1, [1.0])])
    assert len(res.elements) == 10


def test_line_to_component():
    res = _line_to_component(1, alto.TextLine('0', 10, 10, 10, 10, []))
    assert _draw_and_extract_xml_keys([res])['text'] == 1

    str_ = alto.String('0', 1, 1, 1, 1, '', 1, [])
    res = _line_to_component(1, alto.TextLine('0', 10, 10, 10, 10, [str_]))
    assert _draw_and_extract_xml_keys([res])['text'] == 1


def test_alto_page_to_lines():
    assert _alto_page_to_lines([]) == []
    page = alto.Page('', 10, 10, 1, 1, [])
    assert _alto_page_to_lines([page]) == []
    line = alto.TextLine('', 1, 1, 1, 1, [alto.String('', 1, 1, 1, 1, 'test', 1, [])])
    block = alto.ComposedBlock('', 1, 1, 1, 1, [alto.TextBlock('', 1, 1, 1, 1, [line])])
    page = alto.Page('', 10, 10, 1, 1, [alto.PrintSpace(1, 1, 1, 1, 1, [block])])
    assert len(_alto_page_to_lines([page])) == 1
    assert len(_alto_page_to_lines([page, page])) == 2


def test_pages_to_svg():
    with pytest.raises(ValueError):
        _pages_to_svg([])
    page = alto.Page('', 10, 10, 1, 1, [])
    res = _pages_to_svg([page])
    assert res.attribs['height'] == '10px'
    assert res.attribs['width'] == '10px'
    assert len(res.elements) == 6

    page = alto.Page('', 20, 10, 1, 1, [])
    res = _pages_to_svg([page])
    assert res.attribs['height'] == '20px'
    assert res.attribs['width'] == '10px'
    assert len(res.elements) == 6

    page = alto.Page('', 20, 10, 1, 1, [])
    res = _pages_to_svg([page, page])
    assert res.attribs['height'] == '40px'
    assert res.attribs['width'] == '10px'
    assert len(res.elements) == 7

    line = alto.TextLine('', 1, 1, 1, 1, [alto.String('', 1, 1, 1, 1, 'test', 1, [])])
    block = alto.ComposedBlock('', 1, 1, 1, 1, [alto.TextBlock('', 1, 1, 1, 1, [line])])
    page = alto.Page('', 10, 10, 1, 1, [alto.PrintSpace(1, 1, 1, 1, 1, [block])])
    res = _pages_to_svg([page])
    assert res.attribs['height'] == '10px'
    assert res.attribs['width'] == '10px'
    assert len(res.elements) == 7

    with pytest.raises(AssertionError):
        page = alto.Page('', 20, 10, 1, 1, [])
        page_ = alto.Page('', 10, 20, 1, 1, [])
        res = _pages_to_svg([page, page_])

    with pytest.raises(AssertionError):
        page = alto.Page('', 20, 20, 1, 1, [])
        page_ = alto.Page('', 10, 20, 1, 1, [])
        res = _pages_to_svg([page, page_])

    with pytest.raises(AssertionError):
        page = alto.Page('', 20, 20, 1, 1, [])
        page_ = alto.Page('', 20, 10, 1, 1, [])
        res = _pages_to_svg([page, page_])
