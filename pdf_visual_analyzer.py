#!/usr/bin/env python3
"""
PDF Visual Analysis Tool
------------------------
Analisis visual PDF untuk memahami struktur warna dan layout
sebelum melakukan ekstraksi highlight yang presisi.
"""

import fitz  # PyMuPDF
import cv2
import numpy as np
import json
import argparse
import sys
from collections import Counter


def analyze_pdf_colors(pdf_path: str, sample_pages: int = 3) -> dict:
    """
    Analisis warna dominan dalam PDF
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    # Sample beberapa halaman untuk analisis
    page_indices = list(range(min(sample_pages, total_pages)))
    
    all_colors = []
    color_stats = {}
    
    for page_num in page_indices:
        page = doc[page_num]
        
        # Render dengan resolusi sedang
        matrix = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        
        # Convert to numpy
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        
        # Analisis distribusi warna
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        
        # Cari piksel non-putih dan non-hitam
        h, s, v = cv2.split(hsv)
        
        # Mask untuk area berwarna (bukan putih/hitam/abu)
        colored_mask = (s > 30) & (v > 50) & (v < 240)
        
        if np.any(colored_mask):
            colored_pixels = img[colored_mask]
            
            # Cluster warna dengan K-means sederhana
            unique_colors = []
            for pixel in colored_pixels[::100]:  # Sample setiap 100 piksel
                r, g, b = pixel
                # Quantize warna untuk clustering
                r_q = (r // 32) * 32
                g_q = (g // 32) * 32
                b_q = (b // 32) * 32
                unique_colors.append((r_q, g_q, b_q))
            
            all_colors.extend(unique_colors)
        
        print(f"Analyzed page {page_num + 1}/{total_pages}", file=sys.stderr)
    
    doc.close()
    
    # Hitung frekuensi warna
    color_counts = Counter(all_colors)
    
    # Convert ke format yang mudah dibaca
    color_analysis = []
    for (r, g, b), count in color_counts.most_common(20):
        # Convert ke HSV untuk klasifikasi
        hsv_pixel = cv2.cvtColor(np.uint8([[[r, g, b]]]), cv2.COLOR_RGB2HSV)[0, 0]
        h, s, v = hsv_pixel
        
        color_name = classify_color_hsv(h, s, v)
        
        color_analysis.append({
            'rgb': [int(r), int(g), int(b)],
            'hsv': [int(h), int(s), int(v)],
            'color_name': color_name,
            'count': int(count),
            'hex': f"#{r:02x}{g:02x}{b:02x}"
        })
    
    return {
        'total_colored_pixels': len(all_colors),
        'unique_colors': len(color_counts),
        'top_colors': color_analysis
    }


def classify_color_hsv(h: int, s: int, v: int) -> str:
    """
    Klasifikasi warna berdasarkan HSV
    """
    if s < 30:
        if v < 80:
            return "dark_gray"
        elif v > 200:
            return "light_gray"
        else:
            return "gray"
    
    # Klasifikasi berdasarkan hue
    if h < 10 or h > 170:
        return "red"
    elif h < 25:
        return "orange"
    elif h < 35:
        return "yellow"
    elif h < 85:
        return "green"
    elif h < 100:
        return "cyan"
    elif h < 130:
        return "blue"
    elif h < 160:
        return "purple"
    else:
        return "magenta"


def extract_with_dynamic_thresholds(pdf_path: str, color_analysis: dict) -> list:
    """
    Ekstrak highlight menggunakan threshold dinamis berdasarkan analisis warna
    """
    if not color_analysis['top_colors']:
        return []
    
    doc = fitz.open(pdf_path)
    highlights = []
    
    # Ambil warna-warna yang berpotensi highlight (bukan gray)
    highlight_colors = []
    for color_info in color_analysis['top_colors']:
        if color_info['color_name'] not in ['gray', 'light_gray', 'dark_gray']:
            if color_info['count'] > 100:  # Cukup signifikan
                highlight_colors.append(color_info)
    
    if not highlight_colors:
        doc.close()
        return []
    
    print(f"Using {len(highlight_colors)} potential highlight colors", file=sys.stderr)
    
    for page_num, page in enumerate(doc, 1):
        matrix = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        
        for color_info in highlight_colors:
            target_h, target_s, target_v = color_info['hsv']
            
            # Dynamic range based on color characteristics
            h_range = 15 if color_info['color_name'] in ['red', 'magenta'] else 10
            s_range = 40
            v_range = 60
            
            # Create mask with tolerance
            h_lower = max(0, target_h - h_range)
            h_upper = min(179, target_h + h_range)
            s_lower = max(0, target_s - s_range)
            s_upper = min(255, target_s + s_range)
            v_lower = max(0, target_v - v_range)
            v_upper = min(255, target_v + v_range)
            
            # Handle red hue wrap-around
            if color_info['color_name'] == 'red' and target_h < 20:
                mask1 = cv2.inRange(hsv, np.array([0, s_lower, v_lower]), np.array([h_upper, s_upper, v_upper]))
                mask2 = cv2.inRange(hsv, np.array([160, s_lower, v_lower]), np.array([179, s_upper, v_upper]))
                mask = cv2.bitwise_or(mask1, mask2)
            else:
                lower = np.array([h_lower, s_lower, v_lower])
                upper = np.array([h_upper, s_upper, v_upper])
                mask = cv2.inRange(hsv, lower, upper)
            
            if not np.any(mask):
                continue
            
            # Morphological operations
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 500:  # Minimum area
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                
                # Aspect ratio filtering
                aspect = w / h if h > 0 else 0
                if aspect < 1.5 or aspect > 25:
                    continue
                
                # Size filtering
                if h < 12 or h > 80 or w < 40:
                    continue
                
                # Extract and OCR
                roi = img[y:y+h, x:x+w]
                
                try:
                    text = pytesseract.image_to_string(
                        roi, 
                        lang='ind+eng',
                        config='--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,():-'
                    ).strip()
                    
                    if text and len(text) >= 5 and not text.isdigit():
                        highlights.append({
                            'page_number': page_num,
                            'text': text,
                            'color': color_info['color_name'],
                            'bbox': {'x': x//2, 'y': y//2, 'w': w//2, 'h': h//2}
                        })
                        
                except Exception:
                    continue
    
    doc.close()
    return highlights


def main():
    parser = argparse.ArgumentParser(description='PDF Visual Analysis and Smart Highlight Extraction')
    parser.add_argument('pdf_path', help='Path to PDF file')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze colors, don\'t extract')
    parser.add_argument('--simple', action='store_true', help='Simple output (text and color only)')
    parser.add_argument('--sample-pages', type=int, default=3, help='Pages to sample for color analysis')
    
    args = parser.parse_args()
    
    print("Analyzing PDF colors...", file=sys.stderr)
    color_analysis = analyze_pdf_colors(args.pdf_path, args.sample_pages)
    
    print(f"Found {color_analysis['unique_colors']} unique colors", file=sys.stderr)
    print(f"Top colors: {[c['color_name'] for c in color_analysis['top_colors'][:5]]}", file=sys.stderr)
    
    if args.analyze_only:
        result = color_analysis
    else:
        print("Extracting highlights...", file=sys.stderr)
        highlights = extract_with_dynamic_thresholds(args.pdf_path, color_analysis)
        
        # Deduplicate
        seen = set()
        unique_highlights = []
        for h in highlights:
            key = (h['text'].strip(), h['color'])
            if key not in seen:
                seen.add(key)
                if args.simple:
                    unique_highlights.append({'text': h['text'], 'color': h['color']})
                else:
                    unique_highlights.append(h)
        
        print(f"Extracted {len(unique_highlights)} unique highlights", file=sys.stderr)
        
        result = {
            'color_analysis': color_analysis,
            'highlights': unique_highlights
        }
    
    # Output
    if args.pretty:
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        json_str = json.dumps(result, ensure_ascii=False)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(json_str)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
