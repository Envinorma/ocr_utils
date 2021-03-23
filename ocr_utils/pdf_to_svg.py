import os
import shutil
import tempfile
from typing import IO, List, Optional, Tuple, Union

import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path
from svgwrite.drawing import Drawing
from tqdm import tqdm

from ocr_utils.alto_to_svg import alto_pages_and_cells_to_svg
from ocr_utils.table import DetectedCell, extract_and_hide_cells


def _decode(content: Union[str, bytes]) -> str:
    return content.decode() if isinstance(content, bytes) else content


def _run_tesseract(page: str, lang: str) -> str:
    return _decode(pytesseract.image_to_alto_xml(page, lang=lang))


_OCROutput = Tuple[str, Optional[List[DetectedCell]]]


def _ocr_on_image_file(file: IO, detect_tables: bool, lang: str) -> _OCROutput:
    with tempfile.NamedTemporaryFile(suffix='.png') as temp_file:
        if detect_tables:
            cells = extract_and_hide_cells(file.name, temp_file.name, lang)
        else:
            shutil.copyfile(file.name, temp_file.name)
            cells = []
        return _run_tesseract(temp_file.name, lang), cells


def _ocr_on_page(path: str, page_nb: int, detect_tables: bool, lang: str) -> _OCROutput:
    with tempfile.NamedTemporaryFile(suffix='.png') as temp_file:
        page = convert_from_path(path, first_page=page_nb + 1, last_page=page_nb + 1)[0]
        page.save(temp_file)
        return _ocr_on_image_file(temp_file, detect_tables, lang)


def _nb_pages_in_pdf(filename: str) -> int:
    return pdfinfo_from_path(filename)['Pages']


def _ocr_pdf(filename: str, detect_tables: bool, lang: str) -> List[_OCROutput]:
    if not os.path.exists(filename):
        raise ValueError(f'Input pdf not found at path {filename}.')
    nb_pages = _nb_pages_in_pdf(filename)
    result: List[_OCROutput] = []
    for page_nb in tqdm(range(nb_pages), 'Performing OCR.', leave=False):
        result.append(_ocr_on_page(filename, page_nb, detect_tables, lang))
    return result


def _unzip_ocr_outputs(ocr_outputs: List[_OCROutput]) -> Tuple[List[str], List[List[DetectedCell]]]:
    if not ocr_outputs:
        return [], []
    if ocr_outputs[0][1] is None:
        return [page for page, _ in ocr_outputs], [[] for _ in range(len(ocr_outputs))]
    pages: List[str] = []
    cells: List[List[DetectedCell]] = []
    for page, cells_ in ocr_outputs:
        pages.append(page)
        assert cells_ is not None, 'Either all cells_ must be None or none'
        cells.append(cells_)
    return pages, cells


def _generate_svg(ocr_outputs: List[_OCROutput]) -> Drawing:
    pages, cells = _unzip_ocr_outputs(ocr_outputs)
    return alto_pages_and_cells_to_svg(pages, cells)


def _generate_and_write_svg(ocr_outputs: List[_OCROutput], output_filename: str) -> None:
    svg = _generate_svg(ocr_outputs)
    svg.saveas(output_filename)


def pdf_to_svg(input_filename: str, output_filename: str, detect_tables: bool, lang: str) -> None:
    ocr_outputs = _ocr_pdf(input_filename, detect_tables, lang)
    _generate_and_write_svg(ocr_outputs, output_filename)
