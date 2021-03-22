from tqdm import tqdm
import pytesseract
import os
from typing import Any, List, Union
from pdf2image import convert_from_path, pdfinfo_from_path
import tempfile


def _decode(content: Union[str, bytes]) -> str:
    return content.decode() if isinstance(content, bytes) else content


def _run_tesseract(page: Any, lang: str) -> str:
    return _decode(pytesseract.image_to_alto_xml(page, lang=lang))


def _ocr_page(path: str, page_nb: int, lang: str) -> str:
    with tempfile.TemporaryFile() as temp_file:
        page = convert_from_path(path, first_page=page_nb + 1, last_page=page_nb + 1)[0]
        page.save(temp_file)
        page = _run_tesseract(temp_file, lang)
        return page


def _nb_pages_in_pdf(filename: str) -> int:
    return pdfinfo_from_path(filename)['Pages']


def _ocr_pdf(filename: str, lang: str) -> List[str]:
    if not os.path.exists(filename):
        raise ValueError(f'Input pdf not found at path {filename}.')
    nb_pages = _nb_pages_in_pdf(filename)
    result: List[str] = []
    for page_nb in tqdm(range(nb_pages), 'Performing OCR.', leave=False):
        result.append(_ocr_page(filename, page_nb, lang))
    return result


def pdf_to_svg(input_filename: str, output_filename: str, detect_tables: bool, lang: str) -> None:
    return