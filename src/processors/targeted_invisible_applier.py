#!/usr/bin/env python3
"""
targeted_invisible_applier.py

Tujuan:
  Mengambil daftar segmen terpilih dari flagged_selection.json lalu
  menerapkan hanya teknik invisible (unicode substitution & zero width)
  pada paragraf di dokumen sumber yang mengandung teks tersebut.

Catatan Penting:
  - Ini pendekatan sederhana: pencarian substring di keseluruhan paragraf.
  - Jika teks pendek/umum bisa menyebabkan banyak match. Dianjurkan gunakan
    min-length >= 6 dan lakukan kurasi manual pada flagged_selection.json.
  - Mengandalkan engine yang sudah ada di InvisibleManipulator untuk
    substitusi karakter (kita gunakan kembali fungsi apply_unicode_substitution_to_text
    dan insert_invisible_chars dengan laju dikontrol lewat argumen CLI override).

Alur:
 1. Muat flagged_selection.json
 2. Filter hanya selected == True
 3. Muat dokumen DOCX sumber
 4. Untuk setiap paragraf, cek apakah mengandung salah satu teks target
    (urutan: teks lebih panjang dulu supaya tidak nested collision)
 5. Terapkan teknik sesuai recommended_techniques untuk entri tsb:
      - unicode_substitution: pakai fungsi substitusi
      - zero_width: sisipkan zero-width setelah tanda baca / spasi
 6. Simpan dokumen hasil (output path)
 7. Buat laporan ringkas JSON (opsional) berisi id segmen yang berhasil dimanipulasi

CLI:
  python targeted_invisible_applier.py \
      --doc input/thesis.docx \
      --selection flagged_selection.json \
      --output output/processed_documents/thesis_targeted.docx \
      --unicode-rate 0.04 \
      --zero-width-rate 0.06 \
      --report targeted_report.json

Limitasi:
  - Tidak melakukan verifikasi perbedaan visual.
  - Tidak memodifikasi metadata.
  - Tidak melakukan backup otomatis (bisa ditambahkan).

Author: Auto-generated helper
"""
from __future__ import annotations
import json
import argparse
from pathlib import Path
import docx
import random
from typing import List, Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.invisible_manipulator import InvisibleManipulator

# Reuse logic but allow overriding rates transiently

def load_selection(path: Path) -> List[Dict[str, Any]]:
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("flagged_selection.json harus list")
    return [d for d in data if d.get('selected')]


def insert_zero_width(text: str, rate: float, zero_chars: List[str]) -> str:
    if rate <= 0 or not zero_chars:
        return text
    out = []
    for ch in text:
        out.append(ch)
        if ch in ' .,;:!' and random.random() < rate:
            out.append(random.choice(zero_chars))
    return ''.join(out)


def apply_unicode_subs(text: str, manip: InvisibleManipulator, rate: float) -> str:
    # Temporarily override substitution rate inside manip.config
    original_rate = manip.config['invisible_techniques']['unicode_substitution']['substitution_rate']
    manip.config['invisible_techniques']['unicode_substitution']['substitution_rate'] = rate
    try:
        return manip.apply_unicode_substitution_to_text(text)
    finally:
        manip.config['invisible_techniques']['unicode_substitution']['substitution_rate'] = original_rate


def main():
    ap = argparse.ArgumentParser(description="Terapkan manipulasi invisible hanya ke segmen terpilih")
    ap.add_argument('--doc', required=True, help='File DOCX sumber')
    ap.add_argument('--selection', required=True, help='File flagged_selection.json')
    ap.add_argument('--output', required=True, help='File DOCX hasil')
    ap.add_argument('--unicode-rate', type=float, default=0.03, help='Override laju unicode substitution')
    ap.add_argument('--zero-width-rate', type=float, default=0.05, help='Laju sisip zero width')
    ap.add_argument('--report', default='', help='File laporan JSON (opsional)')
    ap.add_argument('--dry-run', action='store_true', help='Tidak menulis file output')

    args = ap.parse_args()
    selection_path = Path(args.selection)
    if not selection_path.exists():
        raise SystemExit(f"Selection file tidak ditemukan: {selection_path}")

    doc_path = Path(args.doc)
    if not doc_path.exists():
        raise SystemExit(f"DOCX sumber tidak ditemukan: {doc_path}")

    selections = load_selection(selection_path)
    if not selections:
        raise SystemExit("Tidak ada entri 'selected' di selection file.")

    # Urutkan segmen berdasarkan panjang teks desc (supaya match panjang dulu)
    selections.sort(key=lambda x: len(x['text']), reverse=True)

    manip = InvisibleManipulator(verbose=False)

    zero_chars = list(manip.invisible_chars.get('zero_width', {}).values()) if manip.invisible_chars else []

    doc = docx.Document(str(doc_path))

    manipulated_ids = []

    # Pre-build list of (id, text, techniques)
    targets = [(seg['id'], seg['text'], seg.get('recommended_techniques', [])) for seg in selections]

    for p_idx, paragraph in enumerate(doc.paragraphs):
        original = paragraph.text
        modified = original
        changed = False
        for seg_id, seg_text, techniques in targets:
            if seg_text in modified:
                # Apply per-technique
                if 'unicode_substitution' in techniques:
                    modified = modified.replace(seg_text, apply_unicode_subs(seg_text, manip, args.unicode_rate))
                if 'zero_width' in techniques:
                    after = modified if seg_text not in modified else modified
                    # If we just replaced, we still want to inject zero width around occurrences
                    modified = insert_zero_width(after, args.zero_width_rate, zero_chars)
                changed = True
                if seg_id not in manipulated_ids:
                    manipulated_ids.append(seg_id)
        if changed and modified != original:
            paragraph.text = modified

    if not args.dry_run:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_path))
        print(f"✅ Dokumen tersimpan: {out_path}")
        print(f"Total segmen terpengaruh: {len(manipulated_ids)}")
    else:
        print(f"[DRY-RUN] Perubahan tidak disimpan. Segmen terpengaruh: {len(manipulated_ids)}")

    if args.report:
        report_data = {
            'source_doc': str(doc_path),
            'output_doc': None if args.dry_run else str(args.output),
            'manipulated_count': len(manipulated_ids),
            'manipulated_ids': manipulated_ids
        }
        with open(args.report, 'w', encoding='utf-8') as rf:
            json.dump(report_data, rf, ensure_ascii=False, indent=2)
        print(f"📝 Laporan dibuat: {args.report}")


if __name__ == '__main__':
    main()
