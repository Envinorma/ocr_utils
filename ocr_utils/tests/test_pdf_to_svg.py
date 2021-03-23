import os
import tempfile
import pytest
from ocr_utils.table import Contour, DetectedCell
from ocr_utils.pdf_to_svg import _unzip_ocr_outputs, pdf_to_svg


def test_unzip_ocr_outputs():
    assert _unzip_ocr_outputs([]) == ([], [])

    assert _unzip_ocr_outputs([('', [])]) == ([''], [[]])

    assert _unzip_ocr_outputs([('', None)]) == ([''], [[]])

    assert _unzip_ocr_outputs([('', None), ('', None)]) == (['', ''], [[], []])

    cell = DetectedCell('a', Contour(1, 2, 3, 4))
    cell_ = DetectedCell('b', Contour(1, 2, 3, 4))
    assert _unzip_ocr_outputs([('', [cell, cell_]), ('', [])]) == (['', ''], [[cell, cell_], []])
    assert _unzip_ocr_outputs([('', [cell]), ('', [cell_])]) == (['', ''], [[cell], [cell_]])
    with pytest.raises(AssertionError):
        _unzip_ocr_outputs([('', [cell]), ('', None)]) == (['', ''], [[], []])


def _get_test_data_file() -> str:
    to_replace = 'test_pdf_to_svg.py'
    if not __file__.endswith(to_replace):
        raise ValueError(f'Expecting __file__ to end with {to_replace}, got {__file__}')
    file_ = __file__.replace(to_replace, 'data/example_with_table_sm.pdf')
    if not os.path.exists(file_):
        raise ValueError('Expecting file {file_} to exist.')
    return file_


def test_pdf_to_svg():
    input_filename = _get_test_data_file()
    with tempfile.NamedTemporaryFile() as temp_file:
        pdf_to_svg(input_filename, temp_file.name, False, 'fra')

    with tempfile.NamedTemporaryFile() as temp_file:
        pdf_to_svg(input_filename, temp_file.name, True, 'fra')
