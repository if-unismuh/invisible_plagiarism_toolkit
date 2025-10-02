"""
Character Analyzer

Inspect Unicode script usage and invisible character density in a DOCX file.
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from collections import Counter
from pathlib import Path

import docx


def extract_text(path: Path) -> str:
	doc = docx.Document(str(path))
	return "\n".join(p.text for p in doc.paragraphs)


def analyze_text(text: str) -> dict:
	scripts = Counter()
	invisible = 0
	total = 0
	for ch in text:
		total += 1
		if unicodedata.category(ch) == "Cf":
			invisible += 1
		if ch.isalpha():
			try:
				script = unicodedata.name(ch).split()[0]
			except Exception:
				script = "UNKNOWN"
			scripts[script] += 1
	return {
		"total_chars": total,
		"invisible_count": invisible,
		"invisible_density": (invisible / total) if total else 0.0,
		"script_counts": dict(scripts),
	}


def main():
	ap = argparse.ArgumentParser(description="Analyze Unicode scripts and invisible chars in DOCX")
	ap.add_argument("--file", required=True, help="Path to DOCX file")
	args = ap.parse_args()

	path = Path(args.file)
	if not path.exists():
		print(f"❌ File not found: {path}")
		return 1

	text = extract_text(path)
	report = analyze_text(text)
	print(json.dumps(report, indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

