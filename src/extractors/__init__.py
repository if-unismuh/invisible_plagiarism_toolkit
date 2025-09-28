"""
Text and Document Extractors

PDF analysis and highlight extraction tools.
"""

from .pdf_colored_ocr_extractor import extract_colored_regions, hsv_to_name

__all__ = [
    'extract_colored_regions',
    'hsv_to_name'
]