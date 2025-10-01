"""
Core Engine Modules

🔤 Unicode Steganography: Visually identical character substitution (Latin → Cyrillic/Greek)
👻 Invisible Characters: Strategic insertion of zero-width and minimal-width characters
📑 Document Manipulation: Targeted modification of document headers and key sections
📋 Metadata Manipulation: Document properties and hidden content modification
🔍 Detection Analysis: Invisibility verification and detection risk assessment
"""

from .invisible_manipulator import InvisibleManipulator
from .unicode_steganography import UnicodeSteg
from .metadata_manipulator import MetadataManipulator, MetadataOptions
from .detection_analyzer import compare_docx_invisibility

__all__ = [
    'InvisibleManipulator',
    'UnicodeSteg',
    'MetadataManipulator',
    'MetadataOptions',
    'compare_docx_invisibility'
]
