#!/usr/bin/env python3
"""
turnitin_bypass_processor.py

Skrip terintegrasi untuk memproses dokumen PDF yang terdeteksi Turnitin:
1. Ekstrak segmen berwarna dari PDF
2. Filter berdasarkan prioritas warna Turnitin
3. Buat seleksi dan terapkan manipulasi dengan intensitas berbeda per prioritas
4. Output dokumen DOCX yang sudah dimanipulasi

Menggunakan konfigurasi dari config.json untuk mapping warna dan intensitas manipulasi.

Usage:
  python turnitin_bypass_processor.py \
    --pdf input.pdf \
    --docx input.docx \
    --output output/processed.docx \
    --priority high \
    --report

Author: Auto-generated integration script
"""
from __future__ import annotations
import json
import argparse
from pathlib import Path
import subprocess
import sys
from typing import Dict, List, Any


def load_config(config_path: Path = Path('config.json')) -> Dict[str, Any]:
    """Load configuration with Turnitin color priorities"""
    with config_path.open('r', encoding='utf-8') as f:
        return json.load(f)


def get_colors_by_priority(config: Dict[str, Any], priority: str) -> List[str]:
    """Get color list for specified priority level"""
    turnitin_colors = config.get('turnitin_colors', {})
    priority_key = f"{priority}_priority"
    if priority_key in turnitin_colors:
        return turnitin_colors[priority_key]['colors']
    return []


def get_manipulation_rates(config: Dict[str, Any], priority: str) -> Dict[str, float]:
    """Get manipulation rates for specified priority"""
    rates = config.get('flagged_selection', {}).get('manipulation_rates', {})
    priority_key = f"{priority}_priority"
    if priority_key in rates:
        return rates[priority_key]
    # Fallback default rates
    return {'unicode_rate': 0.035, 'zero_width_rate': 0.050}


def run_command(cmd: List[str], description: str) -> bool:
    """Run subprocess command with error handling"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Turnitin Bypass Processor - Integrated Pipeline')
    parser.add_argument('--pdf', required=True, help='Input PDF file with Turnitin highlights')
    parser.add_argument('--docx', required=True, help='Source DOCX file to manipulate')
    parser.add_argument('--output', required=True, help='Output manipulated DOCX file')
    parser.add_argument('--priority', choices=['high', 'medium', 'low', 'all'], 
                       default='high', help='Color priority level to process')
    parser.add_argument('--ocr-lang', default='eng', help='OCR language')
    parser.add_argument('--min-area', type=int, default=1200, help='Minimum detection area')
    parser.add_argument('--report', action='store_true', help='Generate processing report')
    parser.add_argument('--keep-intermediate', action='store_true', help='Keep intermediate files')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t apply actual changes')
    
    args = parser.parse_args()
    
    # Validate inputs
    pdf_path = Path(args.pdf)
    docx_path = Path(args.docx)
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return 1
    if not docx_path.exists():
        print(f"❌ DOCX file not found: {docx_path}")
        return 1
    
    # Load config
    try:
        config = load_config()
        print("📋 Configuration loaded")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return 1
    
    # Setup intermediate files
    base_name = pdf_path.stem
    extract_json = f"{base_name}_colored_ocr.json"
    selection_json = f"{base_name}_selection.json"
    report_json = f"{base_name}_report.json" if args.report else ""
    
    print(f"🎯 Processing: {pdf_path.name} -> {args.output}")
    print(f"📊 Priority level: {args.priority}")
    
    # Step 1: Extract colored regions from PDF
    extract_cmd = [
        'python', 'pdf_colored_ocr_extractor.py',
        str(pdf_path),
        '--min-area', str(args.min_area),
        '--lang', args.ocr_lang,
        '--simple-dedupe',
        '--pretty',
        '-o', extract_json
    ]
    
    if not run_command(extract_cmd, "Extracting colored regions from PDF"):
        return 1
    
    # Step 2: Build flagged selection based on priority
    colors_to_include = []
    if args.priority == 'all':
        # Include all priority levels
        for level in ['high', 'medium', 'low']:
            colors_to_include.extend(get_colors_by_priority(config, level))
    else:
        colors_to_include = get_colors_by_priority(config, args.priority)
    
    if not colors_to_include:
        print(f"❌ No colors found for priority: {args.priority}")
        return 1
    
    colors_str = ','.join(colors_to_include)
    min_length = config.get('flagged_selection', {}).get('auto_filter', {}).get('min_length', 10)
    
    selection_cmd = [
        'python', 'flagged_selection_builder.py',
        '--input', extract_json,
        '--output', selection_json,
        '--include-colors', colors_str,
        '--min-length', str(min_length),
        '--dedupe',
        '--pretty'
    ]
    
    if not run_command(selection_cmd, f"Building selection for {args.priority} priority colors"):
        return 1
    
    # Step 3: Apply targeted manipulation
    rates = get_manipulation_rates(config, args.priority)
    
    apply_cmd = [
        'python', 'targeted_invisible_applier.py',
        '--doc', str(docx_path),
        '--selection', selection_json,
        '--output', args.output,
        '--unicode-rate', str(rates['unicode_rate']),
        '--zero-width-rate', str(rates['zero_width_rate'])
    ]
    
    if args.report:
        apply_cmd.extend(['--report', report_json])
    
    if args.dry_run:
        apply_cmd.append('--dry-run')
    
    if not run_command(apply_cmd, "Applying targeted invisible manipulation"):
        return 1
    
    # Summary
    print("\n🎉 Processing completed successfully!")
    print(f"📥 Input PDF: {pdf_path}")
    print(f"📝 Source DOCX: {docx_path}")
    if not args.dry_run:
        print(f"📤 Output DOCX: {args.output}")
    print(f"🎨 Colors processed: {colors_str}")
    print(f"⚙️  Manipulation rates: Unicode {rates['unicode_rate']}, Zero-width {rates['zero_width_rate']}")
    
    if args.report and Path(report_json).exists():
        print(f"📊 Report: {report_json}")
    
    # Cleanup intermediate files
    if not args.keep_intermediate:
        for temp_file in [extract_json, selection_json]:
            temp_path = Path(temp_file)
            if temp_path.exists():
                temp_path.unlink()
                print(f"🗑️  Cleaned up: {temp_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())