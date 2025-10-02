"""
Document Comparer

Compute a simple paragraph-level diff between two DOCX files and save a JSON report.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import unicodedata

import docx


def load_paragraphs(path: Path) -> list[str]:
	doc = docx.Document(str(path))
	return [p.text for p in doc.paragraphs]


def compare_paragraphs(orig: list[str], mod: list[str]) -> dict:
	diffs = []
	for idx, (o, m) in enumerate(zip(orig, mod)):
		if o != m:
			o_vis = "".join(c for c in o if unicodedata.category(c) != "Cf")
			m_vis = "".join(c for c in m if unicodedata.category(c) != "Cf")
			diffs.append(
				{
					"index": idx,
					"original": o,
					"modified": m,
					"visible_equal": o_vis == m_vis,
					"char_delta": len(m) - len(o),
				}
			)

	# Include tail if lengths differ
	tail = []
	if len(orig) != len(mod):
		longer, which = (orig, "original") if len(orig) > len(mod) else (mod, "modified")
		for i in range(min(len(orig), len(mod)), len(longer)):
			tail.append({"index": i, "side": which, "text": longer[i]})

	return {"diffs": diffs, "tail": tail}


def main():
	ap = argparse.ArgumentParser(description="Compare two DOCX files and output a JSON diff report")
	ap.add_argument("--original", required=True, help="Path to original/backup DOCX")
	ap.add_argument("--modified", required=True, help="Path to modified/processed DOCX")
	args = ap.parse_args()

	orig_path = Path(args.original)
	mod_path = Path(args.modified)

	if not orig_path.exists() or not mod_path.exists():
		print("❌ Both --original and --modified must exist")
		return 1

	orig = load_paragraphs(orig_path)
	mod = load_paragraphs(mod_path)
	diff = compare_paragraphs(orig, mod)

	out_dir = Path("output/comparison_files")
	out_dir.mkdir(parents=True, exist_ok=True)
	ts = datetime.now().strftime("%Y%m%d_%H%M%S")
	report_file = out_dir / f"doc_diff_{ts}.json"
	with open(report_file, "w", encoding="utf-8") as f:
		json.dump(
			{
				"meta": {
					"original": str(orig_path),
					"modified": str(mod_path),
					"generated_at": datetime.now().isoformat(),
				},
				"result": diff,
			},
			f,
			ensure_ascii=False,
			indent=2,
		)

	print(f"✅ Diff report saved: {report_file}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

