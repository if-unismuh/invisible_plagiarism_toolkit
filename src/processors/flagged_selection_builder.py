#!/usr/bin/env python3
"""
flagged_selection_builder.py

Purpose:
  Mempersiapkan daftar teks hasil ekstraksi highlight/warna (misal dari colored_ocr.json)
  menjadi file seleksi (flagged_selection.json) yang bisa ditinjau dan diedit
  sebelum proses invisible manipulation dijalankan.

Fitur:
  - Filter berdasarkan panjang minimum teks
  - Filter warna include / exclude
  - Deduplikasi teks identik (opsional)
  - Penandaan default 'selected': true
  - Penentuan rekomendasi teknik (recommended_techniques) sederhana:
       * pendek (<= 25 chars) -> zero_width
       * menengah (<= 120 chars) -> unicode_substitution + zero_width
       * panjang -> unicode_substitution
  - Output JSON dengan struktur:
      [
        {
          "id": 1,
          "page": 5,
          "color": "green",
          "length": 42,
          "selected": true,
          "recommended_techniques": ["unicode_substitution","zero_width"],
          "text": "Isi teks..."
        }
      ]

Contoh pakai:
  python flagged_selection_builder.py \
      --input colored_ocr.json \
      --output flagged_selection.json \
      --min-length 6 \
      --include-colors green,yellow,blue \
      --dedupe

Setelah file flagged_selection.json dibuat, user bisa manual edit 'selected': false
untuk teks yang tidak ingin dimanipulasi.

Langkah berikut (opsional, belum dibuat di skrip ini):
  - Skrip penerapan targeted invisibility yang hanya memproses entri selected.

Author: Auto-generated helper
"""
from __future__ import annotations
import json
import argparse
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set, Optional


def hash_text(t: str) -> str:
    return hashlib.sha1(t.strip().encode('utf-8')).hexdigest()


def recommend_techniques(length: int) -> List[str]:
    if length <= 25:
        return ["zero_width", "spacing_variant"]
    if length <= 120:
        return ["unicode_substitution", "zero_width", "paraphrase", "spacing_variant"]
    return ["unicode_substitution", "paraphrase", "spacing_variant"]


def load_segments(path: Path) -> List[Dict[str, Any]]:
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Input JSON harus berupa list")
    return data


def build_selection(
    segments: List[Dict[str, Any]],
    min_length: int,
    include: Set[str],
    exclude: Set[str],
    dedupe: bool,
    min_confidence: float = 0.0,
    max_color_distance: Optional[float] = None,
) -> List[Dict[str, Any]]:
    seen_hashes = set()
    output = []
    idx = 1

    for seg in segments:
        text = (seg.get('text') or '').strip()
        color = seg.get('color') or 'unknown'
        page = seg.get('page_number') or seg.get('page') or 0
        if not text:
            continue
        if len(text) < min_length:
            continue
        if include and color not in include:
            continue
        if exclude and color in exclude:
            continue
        confidence = seg.get('color_confidence')
        if min_confidence > 0.0 and confidence is not None and confidence < min_confidence:
            continue
        distance = seg.get('color_distance')
        if max_color_distance is not None and distance is not None and distance > max_color_distance:
            continue
        h = hash_text(text) if dedupe else None
        if dedupe and h in seen_hashes:
            continue
        if dedupe and h:
            seen_hashes.add(h)
        entry = {
            'id': idx,
            'page': page,
            'color': color,
            'length': len(text),
            'color_confidence': seg.get('color_confidence'),
            'turnitin_flag': seg.get('turnitin_flag'),
            'flag_priority': seg.get('flag_priority'),
            'flag_priority_score': seg.get('flag_priority_score'),
            'flag_confidence': seg.get('flag_confidence'),
            'flag_notes': seg.get('flag_notes'),
            'selected': True,
            'recommended_techniques': recommend_techniques(len(text)),
            'text': text,
            'color_confidence': confidence,
            'color_distance': distance,
            'source': seg.get('source')
        }
        output.append(entry)
        idx += 1
    return output


def main():
    ap = argparse.ArgumentParser(description="Bangun file seleksi dari segmen teks berwarna")
    ap.add_argument('--input', '-i', required=True, help='File JSON sumber (misal colored_ocr.json)')
    ap.add_argument('--output', '-o', default='flagged_selection.json', help='File output seleksi')
    ap.add_argument('--min-length', type=int, default=5, help='Panjang minimum teks (default=5)')
    ap.add_argument('--include-colors', default='', help='Daftar warna yang disertakan, pisah koma (kosong=semua)')
    ap.add_argument('--exclude-colors', default='', help='Daftar warna yang dikecualikan, pisah koma')
    ap.add_argument('--dedupe', action='store_true', help='Aktifkan deduplikasi berdasarkan hash teks')
    ap.add_argument('--min-confidence', type=float, default=0.0, help='Ambang minimum color_confidence untuk disertakan')
    ap.add_argument('--max-color-distance', type=float, default=None, help='Ambang maksimum color_distance (kosong=tanpa batas)')
    ap.add_argument('--pretty', action='store_true', help='Output JSON indented')

    args = ap.parse_args()
    src = Path(args.input)
    if not src.exists():
        raise SystemExit(f"Input tidak ditemukan: {src}")

    include = {c.strip() for c in args.include_colors.split(',') if c.strip()} if args.include_colors else set()
    exclude = {c.strip() for c in args.exclude_colors.split(',') if c.strip()} if args.exclude_colors else set()

    segments = load_segments(src)
    selection = build_selection(
        segments,
        args.min_length,
        include,
        exclude,
        args.dedupe,
        min_confidence=max(0.0, args.min_confidence),
        max_color_distance=args.max_color_distance if (args.max_color_distance is None or args.max_color_distance >= 0)
        else None
    )

    out_path = Path(args.output)
    with out_path.open('w', encoding='utf-8') as f:
        if args.pretty:
            json.dump(selection, f, ensure_ascii=False, indent=2)
        else:
            json.dump(selection, f, ensure_ascii=False)

    print(f"✅ Seleksi dibuat: {out_path} (total entri: {len(selection)})")
    # Ringkas 5 contoh pertama
    for sample in selection[:5]:
        print(f"  - [p{sample['page']}] {sample['color']:7} len={sample['length']:3} :: {sample['text'][:60]}" )


if __name__ == '__main__':
    main()
