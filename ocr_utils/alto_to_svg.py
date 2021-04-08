from dataclasses import dataclass
from typing import Callable, List, Tuple, cast
from xml.etree.ElementTree import Element

import alto
from svgwrite.base import BaseElement
from svgwrite.drawing import Drawing

from ocr_utils.commons import assert_one_page_and_get_it
from ocr_utils.table import DetectedCell


@dataclass
class Text:
    content: str
    hpos: float
    vpos: float


@dataclass
class FontSize:
    default: int
    guess: bool
    max_value: int


Drawable = Callable[[Drawing], None]


def _create_rectangle(x: float, y: float, width: float, height: float) -> Drawable:
    def _func(drawing: Drawing) -> None:
        drawing.add(drawing.rect(insert=(x, y), size=(width, height), fill='white'))

    return _func


def _create_line(x: float, y: float, x_: float, y_: float) -> Drawable:
    def _func(drawing: Drawing) -> None:
        drawing.add(drawing.line((x, y), (x_, y_), stroke='black'))

    return _func


class ForeignObject(BaseElement):
    elementname = 'foreignObject'

    def __init__(self, text: str, x: int, y: int, width: int, height: int, **extra):
        super(ForeignObject, self).__init__(**extra)
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def get_xml(self):
        xml = cast(Element, super(ForeignObject, self).get_xml())
        div = Element('div')
        div.text = self.text
        div.attrib['xmlns'] = 'http://www.w3.org/1999/xhtml'
        div.attrib['class'] = 'svg-ocr'
        xml.append(div)
        xml.attrib['x'] = str(self.x)
        xml.attrib['y'] = str(self.y)
        xml.attrib['width'] = str(self.width)
        xml.attrib['height'] = str(self.height)
        return xml


def _create_text(text: str, x: int, y: int, size: int) -> Drawable:
    assert size >= 0

    def _func(drawing: Drawing) -> None:
        drawing.add(drawing.text(text, (x, y), font_size=size))

    return _func


def _merge_drawables(drawables: List[Drawable]) -> Drawable:
    def _func(drawing: Drawing) -> None:
        for drawable in drawables:
            drawable(drawing)

    return _func


def _draw_elements(drawing: Drawing, drawables: List[Drawable]) -> Drawing:
    drawing = drawing.copy()
    for drawable in drawables:
        drawable(drawing)
    return drawing


def _extract_strings_width_sum(line: alto.TextLine) -> float:
    return sum([str_.width for str_ in line.strings if isinstance(str_, alto.String)])


def _guess_font_size(line: alto.TextLine) -> int:
    strings_width = _extract_strings_width_sum(line)
    nb_chars = sum([len(x) for x in line.extract_strings()])
    return int(strings_width / (nb_chars or 1)) * 2


def _line_to_component(h_offset: float, v_offset: float, line: alto.TextLine, font_size: FontSize) -> Drawable:
    content = ' '.join(line.extract_strings())
    size = min(font_size.max_value, _guess_font_size(line)) if font_size.guess else font_size.default
    return _create_text(content, int(line.hpos + h_offset), int(line.vpos + v_offset + size), size)


def _alto_page_to_drawables(page_number: int, page: alto.Page, font_size: FontSize) -> List[Drawable]:
    return [_line_to_component(0, page.height * page_number, line, font_size) for line in page.extract_lines()]


def _cell_to_drawable(cell: DetectedCell, offset: int, font_size: FontSize) -> Drawable:
    x_0 = cell.contour.x_0
    x_1 = cell.contour.x_1
    y_0 = cell.contour.y_0 + offset
    y_1 = cell.contour.y_1 + offset
    text_lines = [_line_to_component(x_0, y_0, line, font_size) for line in cell.lines]
    drawables = [
        _create_line(x_0, y_0, x_1, y_0),
        _create_line(x_0, y_1, x_1, y_1),
        _create_line(x_0, y_0, x_0, y_1),
        _create_line(x_1, y_0, x_1, y_1),
        *text_lines,
    ]
    return _merge_drawables(drawables)


def _page_and_cells_to_drawables(
    page_number: int, page: alto.Page, cells: List[DetectedCell], font_size: FontSize
) -> List[Drawable]:
    offset = int(page.height * page_number)
    svg_pages = _alto_page_to_drawables(page_number, page, font_size)
    svg_cells = [_cell_to_drawable(cell, offset, font_size) for cell in cells]
    return svg_pages + svg_cells


def _image_dimension(pages: List[alto.Page]) -> Tuple[int, int]:
    if not pages:
        raise ValueError('Expecting at least one page to generate SVG')
    nb_pages = len(pages)
    assert len({(page.width, page.height) for page in pages}) == 1, 'Expecting only one page dimension.'
    width = pages[0].width
    height = nb_pages * pages[0].height
    return int(width), int(height)


def _blank_drawing(width: int, height: int) -> Drawing:
    base = Drawing(viewBox=f'0 0 {int(width)} {int(height)}', size=(None, None), debug=False, profile='tiny')
    return base


def _pages_borders(nb_pages: int, img_width: int, img_height: int) -> List[Drawable]:
    background = _create_rectangle(0, 0, img_width, img_height)
    lines = [
        _create_line(0, 0, 0, img_height),
        _create_line(img_width, 0, img_width, img_height),
        *[
            _create_line(0, img_height / nb_pages * i, img_width, img_height / nb_pages * i)
            for i in range(nb_pages + 1)
        ],
    ]
    return [background] + lines


def _pages_and_cells_to_svg(
    pages: List[alto.Page], pages_cells: List[List[DetectedCell]], font_size: FontSize
) -> Drawing:
    assert len(pages) == len(pages_cells), f'Lists have different sizes: {len(pages)} and {len(pages_cells)}'
    width, height = _image_dimension(pages)
    blank_drawing = _blank_drawing(width, height)
    page_borders = _pages_borders(len(pages), width, height)
    elements = [
        element
        for page_number, (page, cells) in enumerate(zip(pages, pages_cells))
        for element in _page_and_cells_to_drawables(page_number, page, cells, font_size)
    ]
    return _draw_elements(blank_drawing, page_borders + elements)


def alto_pages_and_cells_to_svg(
    alto_xml_strings: List[str],
    pages_cells: List[List[DetectedCell]],
    default_font_size: int = 40,
    guess_font_size: bool = True,
    max_font_size: int = 50,
) -> Drawing:
    """
    Generates an SVG image made of concatenated pages from alto xml files and table cells

    Parameters
    ----------
    alto_xml_strings
        alto xml strings
    pages_cells
        detected cells on each page
    default_font_size: int
        size of font in output svg
    guess_font_size: bool
        if True, font size is automatically deduced from block width when possible (to handle varying font sizes)
    max_font_size: int
        when guess_font_size is True, maximal possible font size is set to max_font_size (to avoid huge font size
        in edge cases)

    Returns
    -------
    svgwrite.Drawing
        svg, can be written to file with saveas method
    """
    alto_pages = [assert_one_page_and_get_it(alto.parse(xml_str)) for xml_str in alto_xml_strings]
    font_size = FontSize(default_font_size, guess_font_size, max_font_size)
    return _pages_and_cells_to_svg(alto_pages, pages_cells, font_size)


def _pages_to_svg(pages: List[alto.Page], font_size: FontSize) -> Drawing:
    return _pages_and_cells_to_svg(pages, [[]] * len(pages), font_size)


def _pages_to_svg_file(pages: List[alto.Page], filename: str, font_size: FontSize) -> None:
    drawing = _pages_to_svg(pages, font_size)
    drawing.saveas(filename)


def alto_to_svg(
    input_filename: str,
    output_filename: str,
    default_font_size: int = 40,
    guess_font_size: bool = True,
    max_font_size: int = 50,
) -> None:
    """
    Loads alto xml file and generates an SVG image made of concatenated pages.

    Parameters
    ----------
    input_filename: str
        Path of the XML alto file
    output_filename: str
        Path of the output SVG image
    default_font_size: int
        size of font in output svg
    guess_font_size: bool
        if True, font size is automatically deduced from block width when possible (to handle varying font sizes)
    max_font_size: int
        when guess_font_size is True, maximal possible font size is set to max_font_size (to avoid huge font size
        in edge cases)
    """
    alto_file = alto.Alto.parse_file(input_filename)
    font_size = FontSize(default_font_size, guess_font_size, max_font_size)
    _pages_to_svg_file(alto_file.layout.pages, output_filename, font_size)
