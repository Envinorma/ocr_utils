from dataclasses import dataclass
from typing import Callable, List, Optional

import alto
from svgwrite.drawing import Drawing


@dataclass
class Text:
    content: str
    hpos: float
    vpos: float


Drawable = Callable[[Drawing], None]


def _create_text(
    text: str, x: float, y: float, rotate: Optional[List[float]] = None, fill: str = 'black', font_size: int = 32
) -> Drawable:
    kwargs = {'font-size': font_size}

    def _func(drawing: Drawing) -> None:
        drawing.add(drawing.text(text, insert=(int(x), int(y)), rotate=rotate, fill=fill, **kwargs))

    return _func


def _create_rectangle(x: float, y: float, width: float, height: float) -> Drawable:
    def _func(drawing: Drawing) -> None:
        drawing.add(drawing.rect(insert=(x, y), size=(width, height), fill='white'))

    return _func


def _create_line(x: float, y: float, x_: float, y_: float) -> Drawable:
    def _func(drawing: Drawing) -> None:
        drawing.add(drawing.line((x, y), (x_, y_), stroke="black"))

    return _func


def _draw_elements(drawing: Drawing, drawables: List[Drawable]) -> Drawing:
    drawing = drawing.copy()
    for drawable in drawables:
        drawable(drawing)
    return drawing


def _generate_svg(nb_pages: int, width: float, height: float, elements: List[Drawable]) -> Drawing:
    background = _create_rectangle(0, 0, width, height)
    lines = [
        _create_line(0, 0, 0, height),
        _create_line(width, 0, width, height),
        *[_create_line(0, height / nb_pages * i, width, height / nb_pages * i) for i in range(nb_pages + 1)],
    ]
    blank_drawing = Drawing(profile='tiny', debug=False, size=(f'{int(width)}px', f'{int(height)}px'))
    return _draw_elements(blank_drawing, [background] + elements + lines)


def _line_to_component(v_offset: float, line: alto.TextLine) -> Drawable:
    content = ' '.join(line.extract_strings())
    return _create_text(content, line.hpos, line.vpos + v_offset)


def _alto_page_to_lines(pages: List[alto.Page]) -> List[Drawable]:
    return [
        _line_to_component(page.height * page_number, line)
        for page_number, page in enumerate(pages)
        for line in page.extract_lines()
    ]


def _pages_to_svg(pages: List[alto.Page]) -> Drawing:
    if not pages:
        raise ValueError('Expecting at least one page to generate SVG')
    nb_pages = len(pages)
    assert len({(page.width, page.height) for page in pages}) == 1, 'Expecting only one page dimension.'
    return _generate_svg(nb_pages, pages[0].width, nb_pages * pages[0].height, _alto_page_to_lines(pages))


def _pages_to_svg_file(pages: List[alto.Page], filename: str) -> None:
    drawing = _pages_to_svg(pages)
    drawing.saveas(filename)


def alto_xml_strings_to_svg(alto_xml_strings: List[str], filename: str) -> None:
    alto_pages = [page for xml_str in alto_xml_strings for page in alto.parse(xml_str).layout.pages]
    _pages_to_svg_file(alto_pages, filename)


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
