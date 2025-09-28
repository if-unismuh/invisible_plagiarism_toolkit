#!/usr/bin/env python3
"""
PyMuPDF-based Color Text Extractor
----------------------------------
Ekstrak teks yang memiliki warna non-hitam menggunakan PyMuPDF
dengan analisis struktur PDF internal yang lebih presisi.
"""

import fitz  # PyMuPDF
import json
import sys
import argparse
from typing import List, Dict, Any, Tuple
from collections import defaultdict


def classify_rgb(r: int, g: int, b: int) -> str:
    """
    Klasifikasi RGB ke nama warna berdasarkan threshold Turnitin
    """
    # Normalize to 0-1
    rf, gf, bf = r/255, g/255, b/255
    
    # Define color ranges more precisely for Turnitin colors
    if rf > 0.8 and gf < 0.4 and bf < 0.4:  # Red highlights
        return "red"
    elif rf > 0.8 and gf > 0.8 and bf < 0.4:  # Yellow highlights
        return "yellow"
    elif rf < 0.4 and gf < 0.4 and bf > 0.8:  # Blue highlights
        return "blue"
    elif rf < 0.4 and gf > 0.8 and bf < 0.4:  # Green highlights
        return "green"
    elif rf > 0.8 and gf < 0.4 and bf > 0.8:  # Magenta highlights
        return "magenta"
    elif rf < 0.4 and gf > 0.8 and bf > 0.8:  # Cyan highlights
        return "cyan"
    elif rf > 0.8 and gf > 0.5 and bf > 0.6:  # Pink highlights (common in Turnitin)
        return "pink"
    elif rf > 0.8 and gf > 0.4 and bf < 0.3:  # Orange highlights
        return "orange"
    elif rf > 0.5 and gf < 0.5 and bf > 0.5:  # Purple highlights
        return "purple"
    elif rf < 0.2 and gf < 0.2 and bf < 0.2:  # Near black
        return "black"
    elif rf > 0.8 and gf > 0.8 and bf > 0.8:  # Near white
        return "white"
    else:
        return "other"


def extract_colored_text_pymupdf(pdf_path: str, min_text_length: int = 3) -> List[Dict[str, Any]]:
    """
    Ekstrak teks yang memiliki warna non-hitam menggunakan PyMuPDF
    """
    doc = fitz.open(pdf_path)
    highlights = []
    
    for page_num, page in enumerate(doc, 1):
        # Ekstrak text blocks dengan detail format
        blocks = page.get_text("dict")
        
        for block in blocks.get("blocks", []):
            if block.get("type") != 0:  # Skip non-text blocks
                continue
                
            for line in block.get("lines", []):
                line_text_parts = []
                line_colors = []
                
                for span in line.get("spans", []):
                    # Get text color (integer representation)
                    color = span.get("color", 0)
                    
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    
                    # Convert color integer to RGB
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    
                    # Classify color
                    color_name = classify_rgb(r, g, b)
                    
                    # Only collect non-black text
                    if color_name != "black" and color_name != "white":
                        line_text_parts.append(text)
                        line_colors.append(color_name)
                
                # Combine spans from the same line if they have consistent color
                if line_text_parts:
                    combined_text = " ".join(line_text_parts)
                    if len(combined_text) >= min_text_length:
                        # Use most common color in the line
                        most_common_color = max(set(line_colors), key=line_colors.count) if line_colors else "other"
                        
                        highlights.append({
                            "page_number": page_num,
                            "text": combined_text,
                            "color": most_common_color,
                            "rgb": f"rgb({r},{g},{b})"
                        })
    
    doc.close()
    return highlights


def extract_annotation_highlights_enhanced(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Enhanced annotation extraction with better text reconstruction
    """
    doc = fitz.open(pdf_path)
    highlights = []
    
    for page_num, page in enumerate(doc, 1):
        annots = page.annots(types=[fitz.PDF_ANNOT_HIGHLIGHT])
        
        for annot in annots:
            # Get annotation color
            color_tuple = annot.colors.get("stroke") if annot.colors else None
            
            if color_tuple:
                r, g, b = [int(c * 255) for c in color_tuple]
                color_name = classify_rgb(r, g, b)
            else:
                color_name = "unknown"
            
            # Extract text from annotation quads
            vertices = annot.vertices
            if not vertices:
                continue
            
            text_parts = []
            for i in range(0, len(vertices), 4):
                if i + 3 >= len(vertices):
                    break
                    
                quad = vertices[i:i+4]
                rect = fitz.Quad(quad).rect
                
                # Extract text with word-level precision
                words = page.get_text("words", clip=rect)
                line_text = " ".join([word[4] for word in words if word[4].strip()])
                
                if line_text.strip():
                    text_parts.append(line_text.strip())
            
            if text_parts:
                full_text = " ".join(text_parts)
                if len(full_text) >= 3:
                    highlights.append({
                        "page_number": page_num,
                        "text": full_text,
                        "color": color_name,
                        "source": "annotation"
                    })
    
    doc.close()
    return highlights


def merge_similar_highlights(highlights: List[Dict[str, Any]], similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    Merge highlights with similar text content
    """
    if not highlights:
        return []
    
    # Group by page and color
    grouped = defaultdict(list)
    for h in highlights:
        key = (h['page_number'], h['color'])
        grouped[key].append(h)
    
    merged = []
    for items in grouped.values():
        # Sort by text length (longest first)
        items.sort(key=lambda x: len(x['text']), reverse=True)
        
        used = set()
        for i, item in enumerate(items):
            if i in used:
                continue
                
            current_text = item['text'].lower()
            
            # Find similar items to merge
            for j, other in enumerate(items[i+1:], i+1):
                if j in used:
                    continue
                    
                other_text = other['text'].lower()
                
                # Simple similarity check
                if current_text in other_text or other_text in current_text:
                    # Use the longer text
                    if len(other['text']) > len(item['text']):
                        item['text'] = other['text']
                    used.add(j)
            
            merged.append(item)
    
    return merged


def main():
    parser = argparse.ArgumentParser(description='PyMuPDF Precise Color Text Extractor')
    parser.add_argument('pdf_path', help='Path to PDF file')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('--pretty', action='store_true', help='Pretty print JSON')
    parser.add_argument('--min-length', type=int, default=3, help='Minimum text length')
    parser.add_argument('--mode', choices=['text', 'annotation', 'both'], default='both', 
                        help='Extraction mode: text (colored text), annotation (highlights), both')
    parser.add_argument('--merge', action='store_true', help='Merge similar highlights')
    parser.add_argument('--simple', action='store_true', help='Simple output (text and color only)')
    
    args = parser.parse_args()
    
    all_highlights = []
    
    # Extract based on mode
    if args.mode in ['text', 'both']:
        text_highlights = extract_colored_text_pymupdf(args.pdf_path, args.min_length)
        all_highlights.extend(text_highlights)
        print(f"Found {len(text_highlights)} colored text segments", file=sys.stderr)
    
    if args.mode in ['annotation', 'both']:
        annot_highlights = extract_annotation_highlights_enhanced(args.pdf_path)
        all_highlights.extend(annot_highlights)
        print(f"Found {len(annot_highlights)} annotation highlights", file=sys.stderr)
    
    # Merge similar if requested
    if args.merge:
        all_highlights = merge_similar_highlights(all_highlights)
        print(f"After merging: {len(all_highlights)} highlights", file=sys.stderr)
    
    # Deduplicate by text and color
    seen = set()
    unique_highlights = []
    for h in all_highlights:
        key = (h['text'].strip(), h['color'])
        if key not in seen and len(h['text'].strip()) >= args.min_length:
            seen.add(key)
            unique_highlights.append(h)
    
    # Simplify output if requested
    if args.simple:
        unique_highlights = [{'text': h['text'], 'color': h['color']} for h in unique_highlights]
    
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
