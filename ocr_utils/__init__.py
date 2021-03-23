# -*- coding: utf-8 -*-

"""Top-level package for OCR utils."""

__author__ = "Rémi Delbouys"
__email__ = "remi.delbouys@laposte.net"
# Do not edit this string manually, always use bumpversion
# Details in CONTRIBUTING.md
__version__ = "0.0.3"


def get_module_version():
    return __version__


from .alto_to_svg import alto_pages_and_cells_to_svg, alto_to_svg  # noqa: F401
from .pdf_to_svg import pdf_to_svg  # noqa: F401
from .table import (  # noqa: F401
    Cell,
    LocatedTable,
    Row,
    Table,
    extract_and_hide_cells,
    extract_and_hide_tables,
    extract_and_hide_tables_from_image,
    extract_tables,
    extract_tables_from_image,
)
