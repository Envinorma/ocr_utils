from collections import Counter
from typing import Counter as CounterType
from typing import List
from xml.etree.ElementTree import Element

import alto
import pytest
from svgwrite.container import Defs
from svgwrite.drawing import Drawing
from svgwrite.shapes import Line, Rect

from ocr_utils.alto_to_svg import (
    Drawable,
    FontSize,
    _alto_page_to_drawables,
    _create_line,
    _create_rectangle,
    _create_text,
    _draw_elements,
    _guess_font_size,
    _line_to_component,
    _pages_and_cells_to_svg,
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
    drawable = _create_text('test', 10, 20, 10)
    assert _draw_and_extract_xml_keys([drawable])['text'] == 1

    drawable = _create_text('test', 10, 10, 10)
    assert _draw_and_extract_xml_keys([drawable])['text'] == 1

    drawable = _create_text('tt', 5, 119, 10)
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


def test_pages_and_cells_to_svg():
    with pytest.raises(ValueError):
        res = _pages_and_cells_to_svg([], [], FontSize(50, True, 60))
    with pytest.raises(AssertionError):
        page = alto.Page('', 10, 10, 1, 1, [])
        res = _pages_and_cells_to_svg([page], [], FontSize(50, True, 60))

    page = alto.Page('', 20, 10, 1, 1, [])
    res = _pages_and_cells_to_svg([page], [[]], FontSize(50, True, 60))
    assert res.attribs['viewBox'] == '0 0 10 20'
    assert len(res.elements) == 6

    page = alto.Page('', 20, 10, 1, 1, [])
    res = _pages_and_cells_to_svg([page] * 2, [[]] * 2, FontSize(50, True, 60))
    assert res.attribs['viewBox'] == '0 0 10 40'
    assert len(res.elements) == 7

    page = alto.Page('', 20, 10, 1, 1, [])
    res = _pages_and_cells_to_svg([page] * 4, [[]] * 4, FontSize(50, True, 60))
    assert res.attribs['viewBox'] == '0 0 10 80'
    assert len(res.elements) == 9


def test_guess_font_size():
    assert _guess_font_size(alto.TextLine('0', 10, 10, 10, 10, [])) == 0
    size = _guess_font_size(alto.TextLine('0', 10, 10, 10, 10, [alto.String('', 5, 20, 0, 0, 'text', 1, [])]))
    assert size == 10


def test_line_to_component():
    res = _line_to_component(0, 1, alto.TextLine('0', 10, 10, 10, 10, []), FontSize(50, True, 60))
    assert _draw_and_extract_xml_keys([res])['text'] == 1

    str_ = alto.String('0', 1, 1, 1, 1, 'content', 1, [])
    res = _line_to_component(0, 1, alto.TextLine('0', 10, 10, 10, 10, [str_]), FontSize(50, True, 60))
    assert _draw_and_extract_xml_keys([res])['text'] == 1

    str_ = alto.String('0', 1, 1, 1, 1, 'content', 1, [])
    res = _line_to_component(0, 1, alto.TextLine('0', 10, 10, 10, 10, [str_]), FontSize(50, True, 60))
    assert _draw_and_extract_xml_keys([res])['text'] == 1


def test_alto_page_to_drawables():
    page = alto.Page('', 10, 10, 1, 1, [])
    assert _alto_page_to_drawables(0, page, FontSize(50, True, 60)) == []
    line = alto.TextLine('', 1, 1, 1, 1, [alto.String('', 1, 1, 1, 1, 'test', 1, [])])
    block = alto.ComposedBlock('', 1, 1, 1, 1, [alto.TextBlock('', 1, 1, 1, 1, [line])])
    page = alto.Page('', 10, 10, 1, 1, [alto.PrintSpace(1, 1, 1, 1, 1, [block])])
    assert len(_alto_page_to_drawables(0, page, FontSize(50, True, 60))) == 1


def test_pages_to_svg():
    with pytest.raises(ValueError):
        _pages_to_svg([], FontSize(50, True, 60))
    page = alto.Page('', 10, 10, 1, 1, [])
    res = _pages_to_svg([page], FontSize(50, True, 60))
    assert res.attribs['viewBox'] == '0 0 10 10'
    assert len(res.elements) == 6

    page = alto.Page('', 20, 10, 1, 1, [])
    res = _pages_to_svg([page], FontSize(50, True, 60))
    assert res.attribs['viewBox'] == '0 0 10 20'
    assert len(res.elements) == 6

    page = alto.Page('', 20, 10, 1, 1, [])
    res = _pages_to_svg([page, page], FontSize(50, True, 60))
    assert res.attribs['viewBox'] == '0 0 10 40'
    assert len(res.elements) == 7

    line = alto.TextLine('', 1, 1, 1, 1, [alto.String('', 1, 1, 1, 1, 'test', 1, [])])
    block = alto.ComposedBlock('', 1, 1, 1, 1, [alto.TextBlock('', 1, 1, 1, 1, [line])])
    page = alto.Page('', 10, 10, 1, 1, [alto.PrintSpace(1, 1, 1, 1, 1, [block])])
    res = _pages_to_svg([page], FontSize(50, True, 60))
    assert res.attribs['viewBox'] == '0 0 10 10'
    assert len(res.elements) == 7

    with pytest.raises(AssertionError):
        page = alto.Page('', 20, 10, 1, 1, [])
        page_ = alto.Page('', 10, 20, 1, 1, [])
        res = _pages_to_svg([page, page_], FontSize(50, True, 60))

    with pytest.raises(AssertionError):
        page = alto.Page('', 20, 20, 1, 1, [])
        page_ = alto.Page('', 10, 20, 1, 1, [])
        res = _pages_to_svg([page, page_], FontSize(50, True, 60))

    with pytest.raises(AssertionError):
        page = alto.Page('', 20, 20, 1, 1, [])
        page_ = alto.Page('', 20, 10, 1, 1, [])
        res = _pages_to_svg([page, page_], FontSize(50, True, 60))
