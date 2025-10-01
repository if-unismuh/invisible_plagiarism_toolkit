#!/usr/bin/env python3
"""
Minimal Colored Region OCR Extractor
-----------------------------------
Fokus: PDF yang sudah flattened (semua highlight jadi gambar). Deteksi area yang punya warna (bukan putih / abu netral)
kemudian ekstrak teks di dalamnya via OCR.

Output: List objek {page_number, text, color}
 - color adalah nama warna sederhana berdasarkan hue rata-rata area.

Strategi deteksi warna:
 1. Render halaman (scale 2x) -> RGB -> HSV
 2. Hitung percentil saturasi (p60, p85) untuk adaptif ambang
 3. Mask dasar: S >= sat_core & V >= 150
 4. Tambah pastel jika --aggressive: (S >= 0.55*sat_core & V >= 180)
 5. Buang near-white (S < 25 & V > 235) dan near-black (V < 35)
 6. Morfologi -> kontur -> filter area dan coverage
 7. OCR full page sekali (image_to_data) -> kelompokkan kata yang overlap dengan bbox berwarna
 8. Gabung kata berdasarkan urutan top-left (sort by y,x)

Param penting:
  --min-area       : area minimum kotak deteksi (default 1200)
  --max-coverage   : rasio maksimum area bbox terhadap halaman (default 0.50)
  --aggressive     : aktifkan deteksi pastel/faint
  --no-merge       : jangan merge kotak overlap
  --pretty         : pretty JSON
  --simple-dedupe  : deduplikasi teks akhir

Catatan: Tidak mencoba mengklasifikasikan warna highlight Turnitin eksak; hanya label generik (yellow/green/cyan/blue/magenta/red/orange/pink/other).
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import fitz  # PyMuPDF
import numpy as np
import cv2  # type: ignore
import pytesseract  # type: ignore

ColorName = str

# ------------------------------------------------------------
# Turnitin color profiling (approximate palette taken from common highlights)
# ------------------------------------------------------------

TURNITIN_COLOR_PROFILES = {
    "red": (232, 80, 80),
    "magenta": (190, 90, 200),
    "blue": (86, 125, 228),
    "green": (104, 204, 140),
    "yellow": (248, 236, 130),
    "orange": (244, 170, 104),
    "cyan": (135, 205, 228),
    "purple": (170, 96, 220),
    "pink": (232, 140, 200),
    "gray": (198, 198, 198),
}

_TURNITIN_COLOR_LAB = {
    name: cv2.cvtColor(
        np.array([[profile]], dtype=np.uint8),
        cv2.COLOR_RGB2LAB,
    )[0][0].astype(np.float32)
    for name, profile in TURNITIN_COLOR_PROFILES.items()
}


def _mean_rgb_from_mask(img: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
    """Compute average RGB value inside mask; return None if mask empty."""
    if img.size == 0:
        return None
    mask_bool = mask.astype(bool)
    if not mask_bool.any():
        return None
    pixels = img[mask_bool]
    if pixels.size == 0:
        return None
    return pixels.reshape(-1, 3).mean(axis=0)


def match_turnitin_color(
    mean_rgb: Optional[np.ndarray],
    mean_hsv: Tuple[float, float, float],
) -> Tuple[str, float, str, float]:
    """Return best-fit Turnitin color, confidence, palette match, and distance."""
    hsv_color = hsv_to_name(mean_hsv[0], mean_hsv[1], mean_hsv[2])
    if mean_rgb is None:
        return hsv_color, 0.0, hsv_color, 999.0

    try:
        lab_color = cv2.cvtColor(
            np.array([[mean_rgb]], dtype=np.float32),
            cv2.COLOR_RGB2LAB,
        )[0][0].astype(np.float32)
    except Exception:
        return hsv_color, 0.0, hsv_color, 999.0

    best_name = hsv_color
    best_distance = float("inf")
    for name, profile_lab in _TURNITIN_COLOR_LAB.items():
        dist = float(np.linalg.norm(lab_color - profile_lab))
        if dist < best_distance:
            best_distance = dist
            best_name = name

    # Determine confidence; tighten threshold for fallback to hue heuristic
    confidence = max(0.0, min(1.0, 1.0 - (best_distance / 85.0)))
    distance_threshold = 60.0
    if best_distance > distance_threshold and hsv_color not in {"light", "gray"}:
        # Hue-based name feels more reliable when palette distance is large
        return hsv_color, confidence * 0.5, best_name, best_distance

    return best_name, confidence, best_name, best_distance

# ------------------------------------------------------------
# Color naming helpers
# ------------------------------------------------------------

def hsv_to_name(h: float, s: float, v: float) -> ColorName:
    if v < 40:
        return "dark"
    if s < 30:
        return "light" if v > 200 else "gray"
    # Hue mapping (OpenCV hue 0-180)
    if (h < 10) or (h >= 170):
        return "red"
    if h < 20:
        return "orange"
    if h < 35:
        return "yellow"
    if h < 85:
        return "green"
    if h < 100:
        return "cyan"
    if h < 130:
        return "blue"
    if h < 155:
        return "magenta"
    return "pink"

# ------------------------------------------------------------
# Core extraction
# ------------------------------------------------------------

def extract_colored_regions(
    pdf_path: Path,
    min_area: int = 1200,
    aggressive: bool = False,
    max_coverage: float = 0.50,
    merge: bool = True,
    ocr_lang: str = "ind+eng",
) -> List[Dict[str, Any]]:
    doc = fitz.open(pdf_path)
    results: List[Dict[str, Any]] = []

    for page_index, page in enumerate(doc, start=1):
        matrix = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        H, S, V = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

        flat_s = S.reshape(-1)
        p60 = int(np.percentile(flat_s, 60))
        p85 = int(np.percentile(flat_s, 85))
        sat_core = max(25, (p60 + p85) // 2)

        mask = (S >= sat_core) & (V >= 150)
        if aggressive:
            pastel = (S >= int(0.55 * sat_core)) & (V >= 180)
            mask = mask | pastel
        near_white = (S < 25) & (V > 235)
        near_black = (V < 35)
        mask = mask & (~near_white) & (~near_black)
        mask_u8 = mask.astype('uint8') * 255

        kernel = np.ones((5, 5), np.uint8)
        mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_CLOSE, kernel)
        if aggressive:
            mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_DILATE, kernel)

        contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        page_h, page_w = img.shape[0], img.shape[1]
        page_area = page_h * page_w

        boxes: List[Dict[str, Any]] = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area < min_area or h < 12:
                continue
            coverage = area / page_area
            if coverage > max_coverage:
                continue
            # Filter extreme wide thin noise
            if h < 18 and w > 15 * h:
                continue
            # Compute mean color inside contour
            contour_mask = cv2.drawContours(np.zeros(mask_u8.shape, dtype=np.uint8), [cnt], -1, 255, -1)
            mean_hsv = cv2.mean(hsv, mask=contour_mask)[:3]
            mean_rgb = _mean_rgb_from_mask(img, contour_mask)
            color_name, confidence, palette_name, distance = match_turnitin_color(mean_rgb, mean_hsv)
            boxes.append({
                'bbox': (x, y, x + w, y + h),
                'color': color_name,
                'color_confidence': confidence,
                'color_profile': palette_name,
                'color_distance': distance,
            })

        if merge and boxes:
            boxes = merge_boxes(boxes)

        if not boxes:
            continue

        # OCR once (word-level)
        try:
            ocr = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang=ocr_lang)
        except pytesseract.TesseractError:
            # Fallback tanpa spesifikasi bahasa
            ocr = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words = []
        for i in range(len(ocr['text'])):
            word = (ocr['text'][i] or '').strip()
            if not word:
                continue
            try:
                conf = float(ocr['conf'][i])
            except Exception:
                continue
            if conf < 40:
                continue
            x = ocr['left'][i]
            y = ocr['top'][i]
            w = ocr['width'][i]
            h = ocr['height'][i]
            words.append((x, y, x + w, y + h, word))

        for b in boxes:
            x0, y0, x1, y1 = b['bbox']
            collected = []
            for wx0, wy0, wx1, wy1, wtxt in words:
                inter_x0 = max(x0, wx0)
                inter_y0 = max(y0, wy0)
                inter_x1 = min(x1, wx1)
                inter_y1 = min(y1, wy1)
                if inter_x1 > inter_x0 and inter_y1 > inter_y0:
                    collected.append((wy0, wx0, wtxt))
            if not collected:
                continue
            collected.sort()
            text = ' '.join(t for _, _, t in collected)
            text = ' '.join(text.split())
            if not text:
                continue
            results.append({
                'page_number': page_index,
                'text': text,
                'color': b['color'],
            })

    doc.close()
    return results

# ------------------------------------------------------------
# Box merging
# ------------------------------------------------------------

def merge_boxes(boxes: List[Dict[str, Any]], iou_thr: float = 0.35) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for b in boxes:
        x0, y0, x1, y1 = b['bbox']
        added = False
        for mb in merged:
            mx0, my0, mx1, my1 = mb['bbox']
            inter_x0 = max(x0, mx0)
            inter_y0 = max(y0, my0)
            inter_x1 = min(x1, mx1)
            inter_y1 = min(y1, my1)
            if inter_x1 <= inter_x0 or inter_y1 <= inter_y0:
                continue
            inter_area = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
            area_a = (x1 - x0) * (y1 - y0)
            area_b = (mx1 - mx0) * (my1 - my0)
            union = area_a + area_b - inter_area
            if union and (inter_area / union) > iou_thr:
                mb['bbox'] = (min(mx0, x0), min(my0, y0), max(mx1, x1), max(my1, y1))
                # Choose more vivid color (simple heuristic: prefer non-gray)
                if mb['color'] == 'gray' and b['color'] != 'gray':
                    mb['color'] = b['color']
                added = True
                break
        if not added:
            merged.append(b)
    return merged

# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='Deteksi teks yang berada di area berwarna (flattened PDF)')
    ap.add_argument('pdf', help='Path PDF input')
    ap.add_argument('-o', '--output', help='File output JSON')
    ap.add_argument('--min-area', type=int, default=1200, help='Minimum area kontur')
    ap.add_argument('--max-coverage', type=float, default=0.50, help='Maks rasio area kontur vs halaman')
    ap.add_argument('--aggressive', action='store_true', help='Aktifkan deteksi pastel')
    ap.add_argument('--no-merge', action='store_true', help='Nonaktifkan merge kotak overlap')
    ap.add_argument('--simple-dedupe', action='store_true', help='Deduplikasi teks akhir')
    ap.add_argument('--lang', default='ind+eng', help='Bahasa OCR (default ind+eng, contoh: eng)')
    ap.add_argument('--pretty', action='store_true', help='Pretty print JSON')
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    results = extract_colored_regions(
        pdf_path,
        min_area=args.min_area,
        aggressive=args.aggressive,
        max_coverage=args.max_coverage,
        merge=not args.no_merge,
        ocr_lang=args.lang,
    )

    if args.simple_dedupe:
        seen = set()
        dedup = []
        for r in results:
            key = (r['text'], r['color'])
            if key in seen:
                continue
            seen.add(key)
            dedup.append(r)
        results = dedup

    out_text = json.dumps(results, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(out_text, encoding='utf-8')
    else:
        print(out_text)

if __name__ == '__main__':
    main()
