"""
Metadata manipulation utilities for DOCX files.

This module centralizes subtle edits to core document properties and
optionally injects invisible content in a controlled, low-risk way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


ZWSP = "\u200B"  # Zero-Width Space (format char)


@dataclass
class MetadataOptions:
	modify_properties: bool = True
	add_invisible_content: bool = True


class MetadataManipulator:
	"""Encapsulates DOCX metadata manipulation strategies."""

	def __init__(self, options: Optional[MetadataOptions] = None) -> None:
		self.options = options or MetadataOptions()

	def apply(self, doc) -> int:
		"""Apply metadata manipulations to a python-docx Document.

		Returns the number of modifications performed.
		"""
		changes = 0

		if self.options.modify_properties:
			changes += self._modify_core_properties(doc)

		if self.options.add_invisible_content:
			changes += self._add_invisible_paragraph(doc)

		return changes

	def _modify_core_properties(self, doc) -> int:
		changes = 0
		try:
			props = doc.core_properties

			# Append a zero-width space to select properties if present to keep changes invisible
			if props.title:
				props.title = f"{props.title}{ZWSP}"
				changes += 1
			if props.subject:
				props.subject = f"{props.subject}{ZWSP}"
				changes += 1
			if props.keywords:
				props.keywords = f"{props.keywords}{ZWSP}"
				changes += 1

			# If empty, safely initialize creator/last_modified_by with an invisible marker
			if not props.creator:
				props.creator = ZWSP
				changes += 1
			if not props.last_modified_by:
				props.last_modified_by = ZWSP
				changes += 1
		except Exception:
			# Be conservative: metadata editing can fail for some files
			return changes

		return changes

	def _add_invisible_paragraph(self, doc) -> int:
		"""Insert a tiny invisible paragraph using zero-width characters.

		Placed at the end of the document to avoid affecting layout.
		"""
		try:
			para = doc.add_paragraph()
			run = para.add_run(ZWSP)
			# Hidden formatting isn't always supported by python-docx at a run level,
			# but zero-width characters are already invisible visually.
			return 1
		except Exception:
			return 0


__all__ = ["MetadataManipulator", "MetadataOptions"]

