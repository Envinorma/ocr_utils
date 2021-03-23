from dataclasses import dataclass
from typing import Callable, List, Tuple, cast
from xml.etree.ElementTree import Element

import alto
from svgwrite.base import BaseElement
from svgwrite.drawing import Drawing

from ocr_utils.table import DetectedCell


@dataclass
class Text:
    content: str
    hpos: float
    vpos: float


Drawable = Callable[[Drawing], None]


def _create_rectangle(x: float, y: float, width: float, height: float) -> Drawable:
    def _func(drawing: Drawing) -> None:
        drawing.add(drawing.rect(insert=(x, y), size=(width, height), fill='white'))

    return _func


def _create_line(x: float, y: float, x_: float, y_: float) -> Drawable:
    def _func(drawing: Drawing) -> None:
        drawing.add(drawing.line((x, y), (x_, y_), stroke="black"))

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
        xml.append(div)
        xml.attrib['x'] = str(self.x)
        xml.attrib['y'] = str(self.y)
        xml.attrib['width'] = str(self.width)
        xml.attrib['height'] = str(self.height)
        return xml


def _create_text(text: str, x: float, y: float, width: int, height: int) -> Drawable:
    def _func(drawing: Drawing) -> None:
        drawing.add(ForeignObject(text, int(x), int(y), int(width), int(height * 2)))

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


def _line_to_component(v_offset: float, line: alto.TextLine) -> Drawable:
    content = ' '.join(line.extract_strings())
    return _create_text(content, line.hpos, line.vpos + v_offset, int(line.width), int(line.height))


def _alto_page_to_drawables(page_number: int, page: alto.Page) -> List[Drawable]:
    return [_line_to_component(page.height * page_number, line) for line in page.extract_lines()]


def _cell_to_drawable(cell: DetectedCell, offset: int) -> Drawable:
    x_0 = cell.contour.x_0
    x_1 = cell.contour.x_1
    y_0 = cell.contour.y_0 + offset
    y_1 = cell.contour.y_1 + offset
    drawables = [
        _create_line(x_0, y_0, x_1, y_0),
        _create_line(x_0, y_1, x_1, y_1),
        _create_line(x_0, y_0, x_0, y_1),
        _create_line(x_1, y_0, x_1, y_1),
        _create_text(cell.text.strip(), x_0, y_0, x_1 - x_0, y_1 - y_0),
    ]
    return _merge_drawables(drawables)


def _page_and_cells_to_drawables(page_number: int, page: alto.Page, cells: List[DetectedCell]) -> List[Drawable]:
    offset = int(page.height * page_number)
    return _alto_page_to_drawables(page_number, page) + [_cell_to_drawable(cell, offset) for cell in cells]


def _image_dimension(pages: List[alto.Page]) -> Tuple[int, int]:
    if not pages:
        raise ValueError('Expecting at least one page to generate SVG')
    nb_pages = len(pages)
    assert len({(page.width, page.height) for page in pages}) == 1, 'Expecting only one page dimension.'
    width = pages[0].width
    height = nb_pages * pages[0].height
    return int(width), int(height)


def _blank_drawing(width: int, height: int) -> Drawing:
    base = Drawing(profile='tiny', debug=False, size=(f'{int(width)}px', f'{int(height)}px'))
    base.add(base.style(content='div {font-size: 25px;}'))
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


def _pages_and_cells_to_svg(pages: List[alto.Page], pages_cells: List[List[DetectedCell]]) -> Drawing:
    assert len(pages) == len(pages_cells), f'Lists have different sizes: {len(pages)} and {len(pages_cells)}'
    width, height = _image_dimension(pages)
    blank_drawing = _blank_drawing(width, height)
    page_borders = _pages_borders(len(pages), width, height)
    elements = [
        element
        for page_number, (page, cells) in enumerate(zip(pages, pages_cells))
        for element in _page_and_cells_to_drawables(page_number, page, cells)
    ]
    return _draw_elements(blank_drawing, page_borders + elements)


def alto_pages_and_cells_to_svg(alto_xml_strings: List[str], pages_cells: List[List[DetectedCell]]) -> Drawing:
    """
    Generates an SVG image made of concatenated pages from alto xml files and table cells

    Parameters
    ----------
    alto_xml_strings
        alto xml strings
    pages_cells
        detected cells on each page

    Returns
    -------
    svgwrite.Drawing
        svg, can be written to file with saveas method
    """
    alto_pages = [_assert_one_page_and_get_it(alto.parse(xml_str)) for xml_str in alto_xml_strings]
    return _pages_and_cells_to_svg(alto_pages, pages_cells)


def _pages_to_svg(pages: List[alto.Page]) -> Drawing:
    return _pages_and_cells_to_svg(pages, [[]] * len(pages))


def _pages_to_svg_file(pages: List[alto.Page], filename: str) -> None:
    drawing = _pages_to_svg(pages)
    drawing.saveas(filename)


def _assert_one_page_and_get_it(file_: alto.Alto) -> alto.Page:
    assert len(file_.layout.pages) == 1, f'Expecting 1 page in alto file, got {len(file_.layout.pages)}'
    return file_.layout.pages[0]


def alto_to_svg(input_filename: str, output_filename: str) -> None:
    """
    Loads alto xml file and generates an SVG image made of concatenated pages.

    Parameters
    ----------
    input_filename: str
        Path of the XML alto file
    output_filename: str
        Path of the output SVG image
    """
    alto_file = alto.Alto.parse_file(input_filename)
    _pages_to_svg_file(alto_file.layout.pages, output_filename)
