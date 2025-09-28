#!/usr/bin/env python3
"""
PDF Highlight Extractor
-----------------------
Ekstraksi teks yang di-highlight dari laporan (misal Turnitin) dengan dua mode:
1. Highlight berbasis anotasi PDF (true text) -> gunakan PyMuPDF annotation API.
2. Highlight tertanam sebagai gambar (scanned / flattened) -> lakukan OCR + deteksi warna.

Output: JSON list berisi objek:
  {
    "page_number": int,
    "text": str,
    "color": str | null,
    "position": [{"x0": float, "y0": float, "x1": float, "y1": float}]  # anotasi
    // atau untuk OCR image-based: "position": {"x0": int, "y0": int, "x1": int, "y1": int}
  }

Catatan:
- Jika ada anotasi highlight asli, hanya mode anotasi yang digunakan (lebih akurat).
- Jika tidak ditemukan anotasi, fallback ke OCR + color segmentation.
- Deteksi warna heuristik (HSV ranges) dan mapping ke nama warna terdekat.

Dependensi utama: PyMuPDF, OpenCV, pytesseract, Pillow, numpy
Pastikan tesseract-ocr terpasang di sistem (Ubuntu: sudo apt-get install -y tesseract-ocr)
"""
from __future__ import annotations
import argparse
import json
from math import sqrt
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union, Iterable

import fitz  # PyMuPDF

# Modul-modul OCR & CV hanya diimpor saat diperlukan untuk mempercepat kasus anotasi saja

def extract_annotation_highlights(doc: fitz.Document) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    # Warna referensi untuk pencocokan (RGB 0-255) – dipakai kalau ingin menstandarkan nama warna
    color_map = {
        "red": (255, 0, 0),
        "yellow": (255, 255, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "magenta": (255, 0, 255),
        "cyan": (0, 255, 255),
        "orange": (255, 165, 0),
        "purple": (128, 0, 128),
        "pink": (255, 192, 203),
        "gray": (128, 128, 128)
    }

    def rgb_to_name(rgb_floats: Tuple[float, float, float] | None) -> Optional[str]:
        if not rgb_floats:
            return None
        r, g, b = [int(round(c * 255)) for c in rgb_floats]
        best_name, best_dist = None, None
        for name, (cr, cg, cb) in color_map.items():
            dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_name = name
        return best_name

    for page_index, page in enumerate(doc, start=1):
        annots = page.annots(types=[fitz.PDF_ANNOT_HIGHLIGHT])
        if not annots:
            continue
        for annot in annots:
            quads = annot.vertices
            if not quads:
                continue
            text_parts: List[str] = []
            positions: List[Dict[str, float]] = []
            # Quads: setiap 4 titik = 1 highlight segment
            for i in range(0, len(quads), 4):
                quad = quads[i : i + 4]
                rect = fitz.Quad(quad).rect
                clip_text = page.get_text("text", clip=rect).strip()
                if clip_text:
                    text_parts.append(clip_text)
                positions.append({
                    "x0": rect.x0,
                    "y0": rect.y0,
                    "x1": rect.x1,
                    "y1": rect.y1,
                })
            if not text_parts:
                continue
            color_f = annot.colors.get("stroke") if annot.colors else None
            color_name = rgb_to_name(color_f) if color_f else None
            results.append({
                "page_number": page_index,
                "text": " ".join(text_parts),
                "color": color_name,
                "position": positions,
            })
    return results


def extract_image_based_highlights(
    doc: fitz.Document,
    ocr_lang: str = "eng",
    min_area: int = 2000,
    aggressive: bool = False,
    hsv_expand: int = 0,
    debug_dir: Optional[Path] = None,
    color_strategy: str = "preset",
    # Filtering / post-processing parameters (used by color presence strategies)
    max_coverage: float = 0.55,
    max_height_ratio: float = 0.30,
    min_density: float = 0.08,
    max_density: float = 0.90,
    enable_line_split: bool = True,
) -> List[Dict[str, Any]]:
    # Import heavy deps lazily
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    import pytesseract  # type: ignore

    color_name_map = {
        "red": (220, 20, 60),
        "orange": (255, 140, 0),
        "yellow": (255, 225, 60),
        "green": (0, 200, 70),
        "cyan": (64, 224, 208),
        "blue": (65, 105, 225),
        "magenta": (199, 21, 133),
        "pink": (255, 105, 180),
    }

    # PRESET STRATEGY --------------------------------------------------------
    # Predefined hue windows + variants
    # Supported strategies:
    #  - preset  : predefined HSV hue windows
    #  - generic : adaptive saturation/value heuristic (existing implementation)
    #  - anycolor: new strategy – detect any region that exhibits colorfulness (inverse logic)
    if color_strategy not in {"preset", "generic", "anycolor"}:
        raise ValueError("color_strategy must be 'preset', 'generic', atau 'anycolor'")

    if color_strategy == "preset":
        base_hue_windows = [
            (20, 40, 'yellow'),
            (40, 85, 'green'),
            (85, 100, 'cyan'),
            (100, 140, 'blue'),
            (140, 165, 'magenta'),
            (165, 180, 'red'),  # upper red
            (0, 10, 'red'),     # lower red
            (10, 20, 'orange'),
        ]
        light_variants = [
            (20, 40, 'light_yellow'),
            (40, 85, 'light_green'),
            (85, 100, 'light_cyan'),
            (100, 130, 'light_blue'),
            (140, 165, 'lavender'),
            (10, 25, 'peach'),
        ]
        def expand(h0: int, h1: int) -> Tuple[int, int]:
            if hsv_expand <= 0:
                return h0, h1
            return max(0, h0 - hsv_expand), min(180, h1 + hsv_expand)
        color_ranges: List[Tuple[Tuple[int, int, int], Tuple[int, int, int], str]] = []
        sv_profiles = [
            (60, 160),
            (40, 150),
            (25, 140),
        ]
        if aggressive:
            sv_profiles.append((15, 130))
        for (h0, h1, label) in base_hue_windows:
            eh0, eh1 = expand(h0, h1)
            for s_min, v_min in sv_profiles:
                color_ranges.append(((eh0, s_min, v_min), (eh1, 255, 255), label))
        for (h0, h1, label) in light_variants:
            eh0, eh1 = expand(h0, h1)
            color_ranges.append(((eh0, 10, 180), (eh1, 120, 255), label))
        if aggressive:
            color_ranges.append(((0, 0, 170), (180, 40, 235), 'light_gray'))
    else:
        color_ranges = []  # not used in generic / anycolor strategies

    def rgb_to_name(rgb: Tuple[int, int, int]) -> str:
        r, g, b = rgb
        best_name, best_dist = None, None
        for name, (cr, cg, cb) in color_name_map.items():
            dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_name = name
        return best_name or "unknown"

    results: List[Dict[str, Any]] = []

    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)

    for page_index, page in enumerate(doc, start=1):
        matrix = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            # Just in case (alpha disabled above, but keep safe)
            import cv2  # re-import safe
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

        highlight_boxes: List[Dict[str, Any]] = []

        # Adaptive kernel size
        kernel_size = 7 if not aggressive else 11
        kernel = np.ones((kernel_size, kernel_size), np.uint8)

        if color_strategy == "preset":
            for (lower, upper, label) in color_ranges:  # type: ignore
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                mask = cv2.inRange(hsv, lower_np, upper_np)
                if not np.any(mask):
                    continue
                mask = cv2.medianBlur(mask, 5)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                if aggressive:
                    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    x, y, w, h = cv2.boundingRect(cnt)
                    area = w * h
                    if area < min_area or h < 12:
                        continue
                    if h < 20 and w > 8 * h:
                        continue
                    merged = False
                    for hb in highlight_boxes:
                        ex_x0, ex_y0, ex_x1, ex_y1 = hb['bbox']
                        inter_x0 = max(ex_x0, x)
                        inter_y0 = max(ex_y0, y)
                        inter_x1 = min(ex_x1, x + w)
                        inter_y1 = min(ex_y1, y + h)
                        if inter_x1 <= inter_x0 or inter_y1 <= inter_y0:
                            continue
                        inter_area = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
                        union_area = (ex_x1 - ex_x0) * (ex_y1 - ex_y0) + area - inter_area
                        if union_area and inter_area / union_area > 0.45:
                            new_box = (
                                min(ex_x0, x),
                                min(ex_y0, y),
                                max(ex_x1, x + w),
                                max(ex_y1, y + h),
                            )
                            hb['bbox'] = new_box
                            hb.setdefault('labels', set()).add(label)
                            merged = True
                            break
                    if merged:
                        continue
                    contour_mask = cv2.drawContours(
                        np.zeros(mask.shape, dtype=np.uint8), [cnt], -1, 255, -1
                    )
                    mean_color = cv2.mean(img, mask=contour_mask)[:3]
                    mean_color = tuple(int(c) for c in mean_color)
                    color_name = rgb_to_name(mean_color)
                    highlight_boxes.append({
                        'bbox': (x, y, x + w, y + h),
                        'color': color_name,
                        'labels': {label},
                    })
        else:  # GENERIC / ANYCOLOR STRATEGIES
            # Build saturation/value adaptive mask without predefined hue categories
            S = hsv[:, :, 1]
            V = hsv[:, :, 2]
            if color_strategy == "generic":
                # ORIGINAL generic logic (slightly refactored)
                flat_s = S.reshape(-1)
                p50 = int(np.percentile(flat_s, 50))
                p80 = int(np.percentile(flat_s, 80))
                sat_core = max(25, (p50 + p80) // 2)
                mask_color = (S >= sat_core) & (V >= 150)
                if aggressive:
                    mask_pastel = (S >= int(sat_core * 0.55)) & (V >= 175)
                    mask_color = mask_color | mask_pastel
                    mask_gray = (S <= 35) & (V >= 170)
                    mask_color = mask_color | mask_gray
                mask = mask_color.astype('uint8') * 255
            else:  # ANYCOLOR strategy (color presence detection)
                # Approach: measure colorfulness & saturation difference vs grayscale.
                # 1. Compute color difference metric D (channel spread)
                R = img[:, :, 0].astype(np.int16)
                G = img[:, :, 1].astype(np.int16)
                B = img[:, :, 2].astype(np.int16)
                rg = (R - G)
                yb = ((R + G) // 2 - B)
                # Colorfulness (simplified per-pixel magnitude)
                colorfulness = np.sqrt(rg.astype(np.float32) ** 2 + yb.astype(np.float32) ** 2)
                # Adaptive thresholds
                cf_flat = colorfulness.reshape(-1)
                sat_flat = S.reshape(-1)
                cf_p60 = float(np.percentile(cf_flat, 60))
                cf_p80 = float(np.percentile(cf_flat, 80))
                sat_p55 = float(np.percentile(sat_flat, 55))
                sat_p75 = float(np.percentile(sat_flat, 75))
                cf_thr = max(18.0, (cf_p60 + cf_p80) / 2.0)
                sat_thr = max(28.0, (sat_p55 + sat_p75) / 2.0)
                base_mask = (colorfulness >= cf_thr) & (S >= sat_thr) & (V >= 120)
                if aggressive:
                    # Include mild/pastel color areas (lower colorfulness but bright & some saturation)
                    pastel_mask = (colorfulness >= cf_thr * 0.55) & (S >= sat_thr * 0.55) & (V >= 170)
                    base_mask = base_mask | pastel_mask
                # Exclude near-white & near-black & very dark text clusters (low V or very low S & high contrast)
                near_white = (V >= 250) & (S <= 15)
                near_black = (V <= 25)
                base_mask = base_mask & (~near_white) & (~near_black)
                mask = base_mask.astype('uint8') * 255
            mask = cv2.medianBlur(mask, 5)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            if aggressive:
                mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                area = w * h
                if area < min_area or h < 12:
                    continue
                if h < 20 and w > 10 * h:
                    continue
                # Page-level filters (avoid giant full-page boxes)
                page_h, page_w = img.shape[0], img.shape[1]
                page_area = page_h * page_w
                coverage = area / page_area
                if coverage > max_coverage:
                    continue
                if h > int(max_height_ratio * page_h):
                    continue
                # Density inside bbox
                sub_mask = mask[y:y+h, x:x+w]
                nonzero = np.count_nonzero(sub_mask)
                density = nonzero / float(area)
                if density < min_density or density > max_density:
                    continue
                contour_mask = cv2.drawContours(
                    np.zeros(mask.shape, dtype=np.uint8), [cnt], -1, 255, -1
                )
                mean_color = cv2.mean(img, mask=contour_mask)[:3]
                mean_color = tuple(int(c) for c in mean_color)
                color_name = rgb_to_name(mean_color)
                # Optional: split large horizontal bands into lines (refine)
                if enable_line_split and w > 0.75 * page_w and h > 28:
                    # Project mask rows
                    proj = sub_mask.sum(axis=1) / 255  # number of active pixels per row
                    # Threshold: at least 30% row coverage considered highlighted row
                    row_active = proj >= (0.30 * w)
                    # Group consecutive True rows
                    in_run = False
                    run_start = 0
                    runs: List[Tuple[int, int]] = []
                    for idx, val in enumerate(row_active):
                        if val and not in_run:
                            in_run = True
                            run_start = idx
                        elif not val and in_run:
                            in_run = False
                            runs.append((run_start, idx - 1))
                    if in_run:
                        runs.append((run_start, len(row_active) - 1))
                    # Create line boxes
                    made_split = False
                    for (rs, re) in runs:
                        line_h = re - rs + 1
                        if line_h < 12:
                            continue
                        line_area = line_h * w
                        line_density = np.count_nonzero(sub_mask[rs:re+1, :]) / float(line_area)
                        if line_density < min_density or line_density > max_density:
                            continue
                        highlight_boxes.append({
                            'bbox': (x, y + rs, x + w, y + re + 1),
                            'color': color_name,
                            'labels': {color_name},
                        })
                        made_split = True
                    if made_split:
                        continue  # skip original big box
                # Append original box
                highlight_boxes.append({
                    'bbox': (x, y, x + w, y + h),
                    'color': color_name,
                    'labels': {color_name},
                })

        # Refine labels: if multiple heuristic labels captured, choose most frequent mapped to base name
        for hb in highlight_boxes:
            if color_strategy == "preset":
                if len(hb.get('labels', [])) > 1:
                    labels = list(hb['labels'])
                    base_pref = [l for l in labels if not l.startswith('light_')]
                    chosen = base_pref[0] if base_pref else labels[0]
                    hb['heur_label'] = chosen
                else:
                    hb['heur_label'] = next(iter(hb.get('labels', {hb['color']})))
            else:
                hb['heur_label'] = hb['color']

        if debug_dir and highlight_boxes:
            # Optionally save a debug composite mask outline per page
            import cv2
            debug_img = img.copy()
            for hb in highlight_boxes:
                x0, y0, x1, y1 = hb['bbox']
                cv2.rectangle(debug_img, (x0, y0), (x1, y1), (0, 0, 255), 2)
                cv2.putText(debug_img, hb['color'], (x0, max(0, y0 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            out_path = debug_dir / f"page_{page_index:03d}.jpg"
            try:
                from PIL import Image
                Image.fromarray(debug_img).save(out_path)
            except Exception:
                pass

        if not highlight_boxes:
            continue

        # OCR
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang=ocr_lang)
        word_boxes: List[Tuple[int,int,int,int,str]] = []
        for i in range(len(ocr_data['text'])):
            raw = ocr_data['text'][i]
            if raw is None:
                continue
            text = raw.strip()
            if not text:
                continue
            conf_str = ocr_data['conf'][i]
            try:
                conf = float(conf_str)
            except Exception:
                continue
            if conf < 40:  # confidence filter
                continue
            x = ocr_data['left'][i]
            y = ocr_data['top'][i]
            w = ocr_data['width'][i]
            h = ocr_data['height'][i]
            word_boxes.append((x, y, x + w, y + h, text))

        for hb in highlight_boxes:
            x0, y0, x1, y1 = hb['bbox']
            overlaps = []
            for wx0, wy0, wx1, wy1, text in word_boxes:
                inter_x0 = max(x0, wx0)
                inter_y0 = max(y0, wy0)
                inter_x1 = min(x1, wx1)
                inter_y1 = min(y1, wy1)
                if inter_x1 > inter_x0 and inter_y1 > inter_y0:
                    overlaps.append((wy0, wx0, text))
            if not overlaps:
                continue
            overlaps.sort()
            joined_text = " ".join(t for _, _, t in overlaps)
            joined_text = " ".join(joined_text.split())  # normalize whitespace
            results.append({
                "page_number": page_index,
                "text": joined_text,
                "color": hb.get('heur_label', hb['color']),
                "position": {"x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1)},
            })
    return results


def process_pdf(
    path: Union[str, Path],
    ocr_lang: str = "eng",
    force_mode: str = "auto",
    min_area: int = 2000,
    aggressive: bool = False,
    hsv_expand: int = 0,
    debug_dir: Optional[str] = None,
    color_strategy: str = "preset",
    max_coverage: float = 0.55,
    max_height_ratio: float = 0.30,
    min_density: float = 0.08,
    max_density: float = 0.90,
    enable_line_split: bool = True,
) -> Union[str, List[Dict[str, Any]]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    doc = fitz.open(path)

    if force_mode not in {"auto", "annot", "ocr"}:
        raise ValueError("force_mode must be one of: auto, annot, ocr")

    if force_mode in ("auto", "annot"):
        annot_results = extract_annotation_highlights(doc)
        if annot_results and force_mode != "ocr":
            return annot_results

    # If force_mode == 'ocr' or no annotations found
    image_results = extract_image_based_highlights(
        doc,
        ocr_lang=ocr_lang,
        min_area=min_area,
        aggressive=aggressive,
        hsv_expand=hsv_expand,
        debug_dir=Path(debug_dir) if debug_dir else None,
        color_strategy=color_strategy,
        max_coverage=max_coverage,
        max_height_ratio=max_height_ratio,
        min_density=min_density,
        max_density=max_density,
        enable_line_split=enable_line_split,
    )
    if not image_results:
        return "No highlight annotations found"
    return image_results


def main():
    parser = argparse.ArgumentParser(description="Ekstrak teks highlight dari PDF (anotasi atau OCR)")
    parser.add_argument("pdf", help="Path ke file PDF input")
    parser.add_argument("-o", "--output", help="Path file output JSON (default: stdout)")
    parser.add_argument("--lang", default="eng", help="Kode bahasa OCR Tesseract (default: eng)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--mode", choices=["auto", "annot", "ocr"], default="auto", help="Mode ekstraksi: auto (default), annot, ocr")
    parser.add_argument("--min-area", type=int, default=2000, help="Minimum luas (pixels) untuk kotak highlight")
    parser.add_argument("--aggressive", action="store_true", help="Aktifkan mode agresif (deteksi highlight samar)")
    parser.add_argument("--hsv-expand", type=int, default=0, help="Perluas rentang hue (+/- nilai) untuk toleransi pergeseran warna")
    parser.add_argument("--debug-dir", help="Folder untuk simpan gambar debug (kotak highlight per halaman)")
    parser.add_argument("--color-strategy", choices=["preset", "generic", "anycolor"], default="preset", help="Strategi: preset (HSV hue list), generic (saturasi adaptif), anycolor (deteksi semua area berwarna/presence)")
    parser.add_argument("--max-coverage", type=float, default=0.55, help="Maks rasio area bbox terhadap halaman (filter kotak raksasa)")
    parser.add_argument("--max-height-ratio", type=float, default=0.30, help="Maks rasio tinggi bbox terhadap tinggi halaman")
    parser.add_argument("--min-density", type=float, default=0.08, help="Min kepadatan piksel mask di dalam bbox")
    parser.add_argument("--max-density", type=float, default=0.90, help="Maks kepadatan piksel mask di dalam bbox")
    parser.add_argument("--no-line-split", action="store_true", help="Nonaktifkan pemecahan kotak besar menjadi baris-baris")
    parser.add_argument("--simple", action="store_true", help="Keluarkan hanya daftar {text, color} (tanpa posisi, deduplikasi)")
    args = parser.parse_args()

    result = process_pdf(
        args.pdf,
        ocr_lang=args.lang,
        force_mode=args.mode,
        min_area=args.min_area,
        aggressive=args.aggressive,
        hsv_expand=args.hsv_expand,
        debug_dir=args.debug_dir,
        color_strategy=args.color_strategy,
        max_coverage=args.max_coverage,
        max_height_ratio=args.max_height_ratio,
        min_density=args.min_density,
        max_density=args.max_density,
        enable_line_split=not args.no_line_split,
    )

    if isinstance(result, str):  # pesan fallback
        out_payload = result
    else:
        out_data = result
        if args.simple:
            # Transform to simplified list of unique (text,color)
            seen = set()
            simple_list = []
            for item in out_data:
                text = item.get("text", "").strip()
                color = item.get("color") or None
                if not text:
                    continue
                key = (text, color)
                if key in seen:
                    continue
                seen.add(key)
                simple_list.append({"text": text, "color": color})
            out_payload = simple_list
        else:
            out_payload = out_data

        out_text = json.dumps(out_payload, ensure_ascii=False, indent=2 if args.pretty else None)

    if isinstance(result, str):
        out_text = json.dumps(out_payload, ensure_ascii=False, indent=2 if args.pretty else None)

    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
    else:
        print(out_text)


if __name__ == "__main__":  # pragma: no cover
    main()
