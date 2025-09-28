#!/usr/bin/env python3
"""
Strict Color Detection for Turnitin PDFs
----------------------------------------
Menggunakan deteksi warna yang sangat spesifik untuk highlight Turnitin
dengan filtering dan merging yang lebih ketat.
"""

import fitz  # PyMuPDF
import cv2
import numpy as np
import pytesseract
import json
import argparse
import sys
from typing import List, Dict, Any, Tuple
from collections import defaultdict


def get_turnitin_color_ranges():
    """
    Range warna HSV spesifik untuk highlight Turnitin
    Berdasarkan observasi umum laporan Turnitin
    """
    return {
        # Turnitin biasanya menggunakan warna-warna ini
        'similarity_red': {
            'hsv_ranges': [((0, 120, 150), (10, 255, 255)), ((170, 120, 150), (180, 255, 255))],
            'rgb_center': (255, 100, 100)
        },
        'similarity_orange': {
            'hsv_ranges': [((10, 120, 150), (25, 255, 255))],
            'rgb_center': (255, 165, 0)
        },
        'similarity_yellow': {
            'hsv_ranges': [((25, 120, 150), (35, 255, 255))],
            'rgb_center': (255, 255, 0)
        },
        'similarity_pink': {
            'hsv_ranges': [((160, 80, 180), (175, 200, 255))],
            'rgb_center': (255, 182, 193)
        },
        'quotation_blue': {
            'hsv_ranges': [((100, 120, 150), (130, 255, 255))],
            'rgb_center': (100, 149, 237)
        },
        'reference_green': {
            'hsv_ranges': [((40, 120, 150), (80, 255, 255))],
            'rgb_center': (144, 238, 144)
        }
    }


def extract_strict_highlights(pdf_path: str, min_area: int = 800, max_area_ratio: float = 0.1) -> List[Dict[str, Any]]:
    """
    Ekstrak highlight dengan deteksi warna yang sangat spesifik untuk Turnitin
    """
    doc = fitz.open(pdf_path)
    highlights = []
    color_ranges = get_turnitin_color_ranges()
    
    for page_num, page in enumerate(doc, 1):
        # Render halaman dengan resolusi tinggi
        matrix = fitz.Matrix(2.0, 2.0)  # 2x zoom for better accuracy
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        
        # Convert to numpy array
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:  # RGBA
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        
        page_area = img.shape[0] * img.shape[1]
        
        # Detect each Turnitin color
        for color_name, color_info in color_ranges.items():
            combined_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            
            # Combine all HSV ranges for this color
            for lower_hsv, upper_hsv in color_info['hsv_ranges']:
                lower = np.array(lower_hsv, dtype=np.uint8)
                upper = np.array(upper_hsv, dtype=np.uint8)
                mask = cv2.inRange(hsv, lower, upper)
                combined_mask = cv2.bitwise_or(combined_mask, mask)
            
            if not np.any(combined_mask):
                continue
            
            # Noise reduction - very conservative
            kernel = np.ones((3, 3), np.uint8)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=1)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            # Find contours
            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Very strict area filtering
                if area < min_area:
                    continue
                
                # Reject massive areas (likely false positives)
                if area > max_area_ratio * page_area:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                
                # Aspect ratio filtering (highlights are typically horizontal)
                aspect_ratio = w / h if h > 0 else 0
                if aspect_ratio < 2.0 or aspect_ratio > 20.0:
                    continue
                
                # Height filtering (highlights shouldn't be too tall or too short)
                if h < 15 or h > 60:  # Scaled for 2x resolution
                    continue
                
                # Width filtering (highlights should have reasonable width)
                if w < 60:  # Too narrow
                    continue
                
                # Density check - how much of the bounding box is actually colored
                roi_mask = combined_mask[y:y+h, x:x+w]
                density = np.count_nonzero(roi_mask) / (w * h)
                if density < 0.15:  # At least 15% of the box should be colored
                    continue
                
                # Extract text with specific OCR config
                roi = img[y:y+h, x:x+w]
                
                # Preprocess ROI for better OCR
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
                
                # Try multiple OCR configurations
                ocr_configs = [
                    '--psm 7 --oem 3',  # Single text line
                    '--psm 8 --oem 3',  # Single word
                    '--psm 6 --oem 3',  # Single uniform block
                ]
                
                best_text = ""
                best_conf = 0
                
                for config in ocr_configs:
                    try:
                        data = pytesseract.image_to_data(
                            roi_gray, 
                            lang='ind+eng',
                            config=config,
                            output_type=pytesseract.Output.DICT
                        )
                        
                        # Reconstruct text with confidence filtering
                        words = []
                        for i in range(len(data['text'])):
                            word = data['text'][i].strip()
                            conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
                            
                            if word and conf > 30:  # Only high-confidence words
                                words.append(word)
                        
                        text = ' '.join(words).strip()
                        if text and len(text) > len(best_text):
                            best_text = text
                            
                    except Exception:
                        continue
                
                # Final text validation
                if best_text and len(best_text) >= 5:  # Minimum 5 characters
                    # Additional filtering for common false positives
                    if not is_likely_false_positive(best_text):
                        highlights.append({
                            'page_number': page_num,
                            'text': best_text,
                            'color': color_name,
                            'confidence': 'high',
                            'bbox': {'x': x//2, 'y': y//2, 'w': w//2, 'h': h//2}  # Scale back to original
                        })
    
    doc.close()
    return highlights


def is_likely_false_positive(text: str) -> bool:
    """
    Check if text is likely a false positive
    """
    text_lower = text.lower().strip()
    
    # Common false positives
    false_positive_patterns = [
        len(text_lower) < 3,
        text_lower.isdigit(),
        len(text_lower.split()) == 1 and len(text_lower) < 6,
        text_lower in ['the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with'],
        any(char.isdigit() for char in text_lower) and len(text_lower) < 8,
        text_lower.startswith('http'),
        text_lower.count('.') > 3,  # Likely garbage
    ]
    
    return any(false_positive_patterns)


def merge_nearby_text(highlights: List[Dict[str, Any]], distance_threshold: int = 10) -> List[Dict[str, Any]]:
    """
    Merge highlights yang berdekatan dan warna sama
    """
    if not highlights:
        return []
    
    # Group by page and color
    grouped = defaultdict(list)
    for h in highlights:
        key = (h['page_number'], h['color'])
        grouped[key].append(h)
    
    merged = []
    
    for group in grouped.values():
        # Sort by y position, then x position
        group.sort(key=lambda x: (x['bbox']['y'], x['bbox']['x']))
        
        if not group:
            continue
            
        current = group[0].copy()
        
        for next_item in group[1:]:
            curr_bbox = current['bbox']
            next_bbox = next_item['bbox']
            
            # Check if they're on the same line (similar y position)
            y_diff = abs(curr_bbox['y'] - next_bbox['y'])
            
            # Check horizontal distance
            x_gap = next_bbox['x'] - (curr_bbox['x'] + curr_bbox['w'])
            
            if y_diff <= distance_threshold and 0 <= x_gap <= distance_threshold * 3:
                # Merge
                current['text'] += ' ' + next_item['text']
                
                # Update bounding box
                new_x = min(curr_bbox['x'], next_bbox['x'])
                new_y = min(curr_bbox['y'], next_bbox['y'])
                new_w = max(curr_bbox['x'] + curr_bbox['w'], next_bbox['x'] + next_bbox['w']) - new_x
                new_h = max(curr_bbox['y'] + curr_bbox['h'], next_bbox['y'] + next_bbox['h']) - new_y
                
                current['bbox'] = {'x': new_x, 'y': new_y, 'w': new_w, 'h': new_h}
            else:
                # Save current and start new
                merged.append(current)
                current = next_item.copy()
        
        # Don't forget the last one
        merged.append(current)
    
    return merged


def main():
    parser = argparse.ArgumentParser(description='Strict Turnitin Highlight Extractor')
    parser.add_argument('pdf_path', help='Path to PDF file')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON')
    parser.add_argument('--min-area', type=int, default=800, help='Minimum area for highlight detection')
    parser.add_argument('--max-area-ratio', type=float, default=0.1, help='Maximum area ratio of page')
    parser.add_argument('--merge', action='store_true', help='Merge nearby highlights')
    parser.add_argument('--simple', action='store_true', help='Simple output (text and color only)')
    
    args = parser.parse_args()
    
    print(f"Extracting highlights with strict mode...", file=sys.stderr)
    
    highlights = extract_strict_highlights(
        args.pdf_path, 
        min_area=args.min_area,
        max_area_ratio=args.max_area_ratio
    )
    
    print(f"Found {len(highlights)} potential highlights", file=sys.stderr)
    
    if args.merge:
        highlights = merge_nearby_text(highlights)
        print(f"After merging: {len(highlights)} highlights", file=sys.stderr)
    
    # Deduplicate
    seen = set()
    unique_highlights = []
    for h in highlights:
        text_clean = h['text'].strip()
        key = (text_clean, h['color'])
        if key not in seen and len(text_clean) >= 5:
            seen.add(key)
            if args.simple:
                unique_highlights.append({'text': text_clean, 'color': h['color']})
            else:
                unique_highlights.append(h)
    
    print(f"Final unique highlights: {len(unique_highlights)}", file=sys.stderr)
    
    # Output
    if args.pretty:
        json_str = json.dumps(unique_highlights, indent=2, ensure_ascii=False)
    else:
        json_str = json.dumps(unique_highlights, ensure_ascii=False)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(json_str)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
