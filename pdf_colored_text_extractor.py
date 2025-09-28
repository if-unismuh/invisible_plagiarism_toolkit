#!/usr/bin/env python3
"""
PDF Colored Text/Background Extractor
-------------------------------------
Ekstrak semua teks yang:
- Memiliki warna font selain hitam/abu/putih
- Atau memiliki background warna selain putih/abu

Fokus: Hanya deteksi dan keluarkan {text, color, bg_color, page_number}

Dependensi: fitz (PyMuPDF)
"""
import fitz  # PyMuPDF
import argparse
import json
from collections import Counter

def rgb_to_name(r, g, b):
    # Sederhana: deteksi putih, hitam, abu, dan "colored"
    if r > 230 and g > 230 and b > 230:
        return "white"
    if r < 40 and g < 40 and b < 40:
        return "black"
    if abs(r-g) < 18 and abs(r-b) < 18 and abs(g-b) < 18:
        if r > 180:
            return "light_gray"
        if r > 80:
            return "gray"
        return "dark_gray"
    return "colored"

def extract_colored_text(pdf_path, min_text_len=2):
    doc = fitz.open(pdf_path)
    results = []
    for page_num, page in enumerate(doc, 1):
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text or len(text) < min_text_len:
                        continue
                    # Font color
                    color = span.get("color", 0)
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    color_name = rgb_to_name(r, g, b)
                    # Background color (if available)
                    bg_color = span.get("bgcolor")
                    if bg_color is not None:
                        br = (bg_color >> 16) & 0xFF
                        bg = (bg_color >> 8) & 0xFF
                        bb = bg_color & 0xFF
                        bg_name = rgb_to_name(br, bg, bb)
                    else:
                        bg_name = None
                    # Deteksi: font berwarna atau background berwarna
                    if (color_name == "colored") or (bg_name and bg_name == "colored"):
                        results.append({
                            "page_number": page_num,
                            "text": text,
                            "color": color_name,
                            "bg_color": bg_name
                        })
    doc.close()
    return results

def main():
    parser = argparse.ArgumentParser(description="Ekstrak semua teks yang berwarna atau punya background warna dari PDF.")
    parser.add_argument("pdf", help="Path ke file PDF")
    parser.add_argument("-o", "--output", help="File output JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON")
    parser.add_argument("--min-len", type=int, default=2, help="Minimal panjang teks")
    args = parser.parse_args()
    results = extract_colored_text(args.pdf, min_text_len=args.min_len)
    if args.pretty:
        out = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        out = json.dumps(results, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)

if __name__ == "__main__":
    main()
