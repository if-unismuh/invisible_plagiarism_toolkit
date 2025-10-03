#!/usr/bin/env python3
"""Flag Detection Tester

Utility script to exercise the highlight extraction + selection pipeline.

Highlights:
  * Extract native Turnitin annotations before OCR fallback.
  * Apply confidence/distance thresholds and report retained flags.
  * Optionally match highlights to DOCX paragraphs to inspect targeting.

Run example:

    python web/tools/flag_detection_tester.py \
        --pdf workspace/input/turnitin/sample.pdf \
        --docx workspace/input/original/sample.docx \
        --mode balanced \
        --sample 5

The script prints summary statistics and dumps optional JSON snapshots for
further inspection.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project modules are importable when running standalone
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from extractors.pdf_colored_ocr_extractor import extract_colored_regions
from processors.flagged_selection_builder import build_selection
from processors.targeted_text_matcher import match_highlights_to_docx


def summarize_highlights(highlights: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate quick metrics on extracted highlights."""
    summary: Dict[str, Any] = {
        "total_segments": len(highlights),
        "by_source": {},
        "colors": {},
        "avg_confidence": 0.0,
    }

    if not highlights:
        return summary

    total_conf = 0.0
    conf_count = 0

    for segment in highlights:
        source = segment.get("source", "unknown")
        summary["by_source"][source] = summary["by_source"].get(source, 0) + 1

        color = (segment.get("color") or "unknown").lower()
        summary["colors"][color] = summary["colors"].get(color, 0) + 1

        confidence = segment.get("color_confidence")
        if isinstance(confidence, (float, int)):
            total_conf += float(confidence)
            conf_count += 1

    if conf_count:
        summary["avg_confidence"] = total_conf / conf_count

    return summary


def print_sample(label: str, items: List[Dict[str, Any]], limit: int) -> None:
    """Pretty-print a few sample entries."""
    print(f"\n🔎 {label} (showing {min(limit, len(items))}/{len(items)}):")
    for idx, item in enumerate(items[:limit], start=1):
        text = (item.get("text") or "").replace("\n", " ")
        snippet = (text[:110] + "…") if len(text) > 110 else text
        confidence = item.get("color_confidence")
        if isinstance(confidence, (int, float)):
            conf_display = f"{confidence:.2f}"
        else:
            conf_display = "∅"
        page = item.get("page_number", item.get("page", "?"))
        color = item.get("color", "unknown")
        print(f"  {idx:02d}. p{page} [{color} | conf={conf_display}] {snippet}")


def run_pipeline(args: argparse.Namespace) -> None:
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"❌ PDF not found: {pdf_path}")

    print(f"📥 Loading PDF: {pdf_path}")
    highlights = extract_colored_regions(
        pdf_path,
        min_area=args.min_area,
        aggressive=args.aggressive,
        max_coverage=args.max_coverage,
        merge=not args.no_merge,
        ocr_lang=args.lang,
    )

    print(f"✅ Extracted {len(highlights)} raw segments")
    raw_summary = summarize_highlights(highlights)
    print(f"   Sources: {raw_summary['by_source']}")
    print(f"   Colors : {raw_summary['colors']}")
    print(f"   Avg confidence: {raw_summary['avg_confidence']:.3f}")

    if args.sample:
        print_sample("Raw highlights", highlights, args.sample)

    include_colors = set(c.strip().lower() for c in args.include.split(",") if c.strip())
    exclude_colors = set(c.strip().lower() for c in args.exclude.split(",") if c.strip())

    selection = build_selection(
        highlights,
        min_length=args.min_length,
        include=include_colors,
        exclude=exclude_colors,
        dedupe=args.dedupe,
        min_confidence=args.min_confidence,
        max_color_distance=args.max_color_distance,
    )

    print(
        f"\n🎯 Selection after filters: {len(selection)} segments "
        f"(min_length={args.min_length}, min_conf={args.min_confidence}, max_dist={args.max_color_distance})"
    )
    if args.sample:
        print_sample("Filtered selection", selection, args.sample)

    if args.selection_output:
        Path(args.selection_output).write_text(
            json.dumps(selection, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"💾 Saved selection JSON to {args.selection_output}")

    if args.docx:
        docx_path = Path(args.docx)
        if not docx_path.exists():
            raise SystemExit(f"❌ DOCX not found: {docx_path}")

        print(f"\n📄 Matching highlights to DOCX paragraphs: {docx_path}")
        matches = match_highlights_to_docx(
            str(docx_path),
            highlights,
            min_similarity=args.min_similarity,
        )
        print(f"   ↳ Found {len(matches)} paragraph matches (threshold {args.min_similarity:.2f})")
        if args.sample:
            print_sample("Matches", matches, args.sample)

        if args.matches_output:
            Path(args.matches_output).write_text(
                json.dumps(matches, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"💾 Saved matches JSON to {args.matches_output}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Flag detection pipeline tester")

    parser.add_argument("--pdf", required=True, help="Path to Turnitin PDF report")
    parser.add_argument("--docx", help="Optional DOCX to run paragraph matching")
    parser.add_argument("--mode", choices=["stealth", "balanced", "aggressive"], default="balanced",
                        help="Logical processing mode (used for defaults)")

    parser.add_argument("--min-area", type=int, default=1200, help="Minimum highlight contour area")
    parser.add_argument("--max-coverage", type=float, default=0.50, help="Maximum bbox/page coverage ratio")
    parser.add_argument("--aggressive", action="store_true", help="Enable pastel detection during OCR fallback")
    parser.add_argument("--no-merge", action="store_true", help="Disable contour merge step")
    parser.add_argument("--lang", default="ind+eng", help="Tesseract language hint")

    parser.add_argument("--min-length", type=int, help="Minimum highlight text length after extraction")
    parser.add_argument("--include", default="", help="Comma-separated list of colors to include explicitly")
    parser.add_argument("--exclude", default="", help="Comma-separated list of colors to exclude")
    parser.add_argument("--dedupe", action="store_true", help="Enable text deduplication in selection")
    parser.add_argument("--min-confidence", type=float, help="Filter highlights below this confidence")
    parser.add_argument("--max-color-distance", type=float, help="Filter highlights above this LAB distance")

    parser.add_argument("--min-similarity", type=float, default=0.8,
                        help="Minimum similarity ratio for DOCX paragraph matching")

    parser.add_argument("--sample", type=int, default=0, help="Print N sample entries for each stage")
    parser.add_argument("--selection-output", help="Optional path to dump selection JSON")
    parser.add_argument("--matches-output", help="Optional path to dump matches JSON")

    args = parser.parse_args(argv)

    # Apply mode defaults when user did not override
    if args.min_length is None:
        args.min_length = {"stealth": 15, "balanced": 10, "aggressive": 6}[args.mode]
    if args.min_confidence is None:
        args.min_confidence = {"stealth": 0.45, "balanced": 0.35, "aggressive": 0.25}[args.mode]
    if args.max_color_distance is None:
        args.max_color_distance = {"stealth": 65.0, "balanced": 75.0, "aggressive": 85.0}[args.mode]

    return args


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    run_pipeline(args)


if __name__ == "__main__":
    main()
