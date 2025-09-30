#!/usr/bin/env python3
"""
Invisible Plagiarism Toolkit - Main CLI
Professional Document Manipulation System

Alur Sistem:
1. Upload 2 dokumen: original.docx + turnitin_report.pdf
2. OCR PDF dengan ocrmypdf untuk text extraction
3. Analisis highlight/flag dari PDF
4. Aplikasi manipulasi sesuai teknik:
   🔤 Unicode Steganography
   👻 Invisible Characters
   📑 Header Manipulation
   📋 Metadata Manipulation
   🔍 Verification System
   📊 Comprehensive Reporting
   🎯 Multiple Processing Modes

Author: DevNoLife
Version: 1.0.0
"""

import sys
import os
import argparse
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

import docx

# Add src to path for imports regardless of launch location
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from core.invisible_manipulator import InvisibleManipulator
from extractors.pdf_colored_ocr_extractor import extract_colored_regions
from processors.flagged_selection_builder import build_selection, load_segments
# from processors.targeted_invisible_applier import load_selection as load_flagged_selection
from utils.logger_config import setup_logger
from utils.performance_monitor import PerformanceMonitor

class PlagiarismBypassCLI:
    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace = Path(workspace_dir)
        self.logger = setup_logger(__name__)
        self.monitor = PerformanceMonitor()
        self.job_reference = os.getenv("IPT_JOB_ID")
        self.setup_workspace()
        
    def setup_workspace(self):
        """Setup workspace directories"""
        directories = [
            "input/original",
            "input/turnitin", 
            "output/processed",
            "output/analysis",
            "output/reports",
            "temp"
        ]
        
        for dir_path in directories:
            (self.workspace / dir_path).mkdir(parents=True, exist_ok=True)
            
        self.logger.info(f"Workspace initialized at: {self.workspace.absolute()}")
        
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        try:
            # Check ocrmypdf
            result = subprocess.run(['ocrmypdf', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error("ocrmypdf not found. Install with: sudo apt install ocrmypdf")
                return False
                
            self.logger.info(f"Dependencies OK - {result.stdout.strip()}")
            return True
            
        except FileNotFoundError:
            self.logger.error("ocrmypdf not found. Install with: sudo apt install ocrmypdf")
            return False
    
    def find_input_files(self) -> tuple[Optional[Path], Optional[Path]]:
        """Find original DOCX and Turnitin PDF files"""
        original_dir = self.workspace / "input" / "original"
        turnitin_dir = self.workspace / "input" / "turnitin"
        
        # Find DOCX files
        docx_files = list(original_dir.glob("*.docx"))
        original_file = docx_files[0] if docx_files else None
        
        # Find PDF files
        pdf_files = list(turnitin_dir.glob("*.pdf"))
        turnitin_file = pdf_files[0] if pdf_files else None
        
        if original_file:
            self.logger.info(f"Found original document: {original_file.name}")
        else:
            self.logger.warning("No DOCX file found in workspace/input/original/")
            
        if turnitin_file:
            self.logger.info(f"Found Turnitin report: {turnitin_file.name}")  
        else:
            self.logger.warning("No PDF file found in workspace/input/turnitin/")
            
        return original_file, turnitin_file
    
    def ocr_pdf(self, input_pdf: Path, output_pdf: Path, force: bool = True) -> bool:
        """Convert PDF to text-searchable using ocrmypdf"""
        self.logger.info(f"Converting PDF to text-searchable: {input_pdf.name}")
        
        def build_cmd(lang: str) -> list[str]:
            cmd = ['ocrmypdf', str(input_pdf), str(output_pdf)]
            if force:
                cmd.append('--force-ocr')
            cmd.extend(['--language', lang, '--optimize', '1'])
            return cmd

        primary_cmd = build_cmd('ind+eng')
        try:
            result = subprocess.run(primary_cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                self.logger.info(f"OCR completed successfully: {output_pdf.name}")
                return True

            stderr_lower = (result.stderr or '').lower()
            if 'does not have language data' in stderr_lower and 'ind' in stderr_lower:
                self.logger.warning("Tesseract language 'ind' tidak tersedia. Mencoba ulang dengan bahasa Inggris saja.")
                fallback_cmd = build_cmd('eng')
                fallback_result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=300)
                if fallback_result.returncode == 0:
                    self.logger.info(f"OCR fallback (eng) completed successfully: {output_pdf.name}")
                    return True
                self.logger.error(f"OCR fallback failed: {fallback_result.stderr}")
                return False

            self.logger.error(f"OCR failed: {result.stderr}")
            return False
        except subprocess.TimeoutExpired:
            self.logger.error("OCR timeout setelah 5 menit")
            return False
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return False
    
    def extract_highlights(self, pdf_path: Path, mode: str = "balanced") -> List[Dict[str, Any]]:
        """Extract colored highlights from PDF"""
        self.logger.info(f"Extracting highlights with {mode} mode")
        
        # Mode settings
        settings = {
            "stealth": {"min_area": 1500, "aggressive": False, "max_coverage": 0.30},
            "balanced": {"min_area": 1200, "aggressive": True, "max_coverage": 0.50}, 
            "aggressive": {"min_area": 800, "aggressive": True, "max_coverage": 0.70}
        }
        
        config = settings.get(mode, settings["balanced"])
        
        try:
            highlights = extract_colored_regions(
                pdf_path,
                min_area=config["min_area"],
                aggressive=config["aggressive"],
                max_coverage=config["max_coverage"],
                merge=True,
                ocr_lang="ind+eng"
            )
            
            self.logger.info(f"Extracted {len(highlights)} highlighted segments")
            return highlights
            
        except Exception as e:
            self.logger.error(f"Highlight extraction failed: {e}")
            return []
    
    def filter_priority_highlights(self, highlights: List[Dict[str, Any]], 
                                 mode: str = "balanced") -> List[Dict[str, Any]]:
        """Filter highlights by Turnitin color priorities"""
        
        # Turnitin color priorities
        priority_colors = {
            "high": ["red", "green", "blue", "magenta"],
            "medium": ["orange", "cyan", "yellow"],
            "low": ["pink", "gray", "light"]
        }
        
        # Mode filtering
        if mode == "stealth":
            include_colors = set(priority_colors["high"])
            min_length = 15
        elif mode == "balanced":
            include_colors = set(priority_colors["high"] + priority_colors["medium"])
            min_length = 10
        else:  # aggressive
            include_colors = set(priority_colors["high"] + priority_colors["medium"] + priority_colors["low"])
            min_length = 6
            
        # Build selection
        selection = build_selection(
            highlights, 
            min_length=min_length,
            include=include_colors,
            exclude=set(),
            dedupe=True
        )
        
        self.logger.info(f"Filtered to {len(selection)} priority segments ({mode} mode)")
        return selection
    
    def apply_manipulations(self, original_docx: Path, selections: List[Dict[str, Any]], 
                          mode: str = "balanced") -> tuple[Optional[Path], Dict[int, List[Dict[str, str]]]]:
        """Apply invisible manipulations to original document guided by flagged selections."""
        
        # Mode settings for manipulation rates
        rates = {
            "stealth": {"unicode": 0.02, "zero_width": 0.03, "paraphrase": 0.10},
            "balanced": {"unicode": 0.04, "zero_width": 0.06, "paraphrase": 0.20},
            "aggressive": {"unicode": 0.07, "zero_width": 0.10, "paraphrase": 0.30}
        }
        config = rates.get(mode, rates["balanced"])

        # Output path
        output_path = self.workspace / "output" / "processed" / f"{original_docx.stem}_{mode}_processed.docx"

        try:
            manipulator = InvisibleManipulator(verbose=True)
            zero_width_chars = list(manipulator.invisible_chars.get('zero_width', {}).values()) if manipulator.invisible_chars else []
            unicode_enabled = manipulator.config['invisible_techniques']['unicode_substitution'].get('enabled', True)
            zero_enabled = manipulator.config['invisible_techniques']['zero_width_chars'].get('enabled', True)
            paraphrase_cfg = manipulator.config['invisible_techniques'].get('paraphrase', {})
            paraphrase_enabled = paraphrase_cfg.get('enabled', True)
            spacing_cfg = manipulator.config['invisible_techniques'].get('spacing_variants', {})
            spacing_enabled = spacing_cfg.get('enabled', True)

            # Override rates based on mode
            manipulator.config['invisible_techniques']['unicode_substitution']['substitution_rate'] = config['unicode']
            manipulator.config['invisible_techniques']['zero_width_chars']['insertion_rate'] = config['zero_width']
            if paraphrase_cfg:
                paraphrase_cfg['replacement_rate'] = config['paraphrase']
            paraphrase_rate = manipulator.config['invisible_techniques'].get('paraphrase', {}).get('replacement_rate', 0.0)
            if spacing_cfg:
                spacing_cfg.setdefault('hair_space_rate', 0.12)
                spacing_cfg.setdefault('zwnj_rate', 0.08)
                spacing_cfg.setdefault('zwj_rate', 0.05)
                spacing_cfg.setdefault('after_punctuation_rate', 0.10)

            document = docx.Document(str(original_docx))
            self.logger.info("Applying targeted invisible manipulations to flagged segments ...")

            # Prepare selections map (lowercase for matching)
            prepared_selections = []
            for seg in selections:
                text = (seg.get('text') or '').strip()
                if not text:
                    continue
                if seg.get('selected') is False:
                    continue
                prepared_selections.append({
                    'id': seg.get('id'),
                    'text': text,
                    'text_lower': text.lower(),
                    'techniques': seg.get('recommended_techniques', [])
                })

            manipulated_ids: set[int] = set()
            manipulated_map: Dict[int, List[Dict[str, str]]] = {}

            paragraphs = []
            seen_paragraphs: set[int] = set()
            for para in document.paragraphs:
                if id(para) not in seen_paragraphs:
                    paragraphs.append(para)
                    seen_paragraphs.add(id(para))
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            if id(para) not in seen_paragraphs:
                                paragraphs.append(para)
                                seen_paragraphs.add(id(para))

            def assign_text_to_runs(paragraph_obj, new_text):
                runs = paragraph_obj.runs
                if not runs:
                    paragraph_obj.text = new_text
                    return
                idx = 0
                total_runs = len(runs)
                for i, run in enumerate(runs):
                    if i == total_runs - 1:
                        run.text = new_text[idx:]
                    else:
                        length = len(run.text)
                        run.text = new_text[idx: idx + length]
                        idx += length

            def build_manipulated_fragment(fragment_text: str, techniques: List[str]) -> str:
                result_fragment = fragment_text
                if paraphrase_enabled and 'paraphrase' in techniques:
                    result_fragment = manipulator.apply_paraphrase_to_text(result_fragment, paraphrase_rate)
                if unicode_enabled and 'unicode_substitution' in techniques:
                    result_fragment = manipulator.apply_unicode_substitution_to_text(result_fragment)
                if zero_enabled and 'zero_width' in techniques and zero_width_chars:
                    result_fragment = manipulator.insert_invisible_chars(
                        result_fragment,
                        zero_width_chars,
                        manipulator.config['invisible_techniques']['zero_width_chars']['insertion_rate']
                    )
                if spacing_enabled and 'spacing_variant' in techniques:
                    result_fragment = manipulator.apply_spacing_variants_to_text(result_fragment, spacing_cfg)
                return result_fragment

            for paragraph in paragraphs:
                full_text = ''.join(run.text for run in paragraph.runs) if paragraph.runs else (paragraph.text or '')
                if not full_text:
                    continue
                lower_text = full_text.lower()
                matches: List[tuple[int, int, str, int, str]] = []

                for seg in prepared_selections:
                    search_start = 0
                    seg_len = len(seg['text'])
                    if seg_len == 0:
                        continue
                    while True:
                        idx = lower_text.find(seg['text_lower'], search_start)
                        if idx == -1:
                            break
                        end_idx = idx + seg_len
                        original_fragment = full_text[idx:end_idx]
                        replacement_fragment = build_manipulated_fragment(original_fragment, seg['techniques'])
                        matches.append((idx, end_idx, replacement_fragment, seg.get('id'), original_fragment))
                        seg_id = seg.get('id')
                        if isinstance(seg_id, int):
                            samples = manipulated_map.setdefault(seg_id, [])
                            if len(samples) < 3:
                                samples.append({
                                    'original': original_fragment,
                                    'manipulated': replacement_fragment
                                })
                                manipulated_ids.add(seg_id)
                        search_start = idx + seg_len

                if not matches:
                    continue

                matches.sort(key=lambda item: item[0], reverse=True)
                new_text = full_text
                for start_idx, end_idx, replacement_fragment, seg_id, _original in matches:
                    new_text = new_text[:start_idx] + replacement_fragment + new_text[end_idx:]

                zero_added = manipulator._count_invisible_chars(full_text, new_text)
                if zero_added:
                    manipulator.stats['invisible_chars_inserted'] += zero_added
                spacing_added = manipulator._count_spacing_variants(full_text, new_text)
                if spacing_added:
                    manipulator.stats['spacing_variants_inserted'] += spacing_added

                assign_text_to_runs(paragraph, new_text)

            # Apply metadata manipulation once per document
            manipulator.apply_metadata_manipulation(document)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            document.save(str(output_path))

            self.logger.info(f"Document processed successfully: {output_path.name}")
            self.logger.info(f"Total flagged segments manipulated: {len(manipulated_ids)}")
            return output_path, manipulated_map

        except Exception as e:
            self.logger.error(f"Manipulation failed: {e}")
            return None, {}
    
    def generate_report(self, original_file: Path, turnitin_file: Path, 
                       processed_file: Optional[Path], highlights: List[Dict[str, Any]],
                       selections: List[Dict[str, Any]], mode: str, job_reference: str,
                       manipulated_ids: List[int], manipulated_map: Dict[int, List[Dict[str, str]]]) -> Path:
        """Generate comprehensive processing report"""
        
        report_data = {
            "processing_info": {
                "mode": mode,
                "timestamp": self.monitor.get_current_time(),
                "processing_time": self.monitor.get_elapsed_time(),
                "job_reference": job_reference
            },
            "input_files": {
                "original_document": str(original_file.name),
                "turnitin_report": str(turnitin_file.name)
            },
            "analysis_results": {
                "total_highlights": len(highlights),
                "selected_segments": sum(1 for seg in selections if seg.get('selected', True)),
                "color_distribution": self._get_color_distribution(highlights),
                "manipulated_segment_ids": manipulated_ids,
                "manipulated_segments": [
                    {
                        "id": seg_id,
                        "samples": manipulated_map.get(seg_id, [])
                    }
                    for seg_id in manipulated_ids
                ]
            },
            "output_files": {
                "processed_document": str(processed_file.name) if processed_file else None
            },
            "techniques_applied": [
                "🔤 Unicode Steganography",
                "👻 Invisible Characters", 
                "📑 Header Manipulation",
                "📋 Metadata Manipulation"
            ]
        }
        
        report_path = self.workspace / "output" / "reports" / f"processing_report_{job_reference}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Report generated: {report_path.name}")
        return report_path

    def save_analysis_summary(
        self,
        job_reference: str,
        mode: str,
        turnitin_file: Path,
        processed_file: Optional[Path],
        report_path: Path,
        highlights: List[Dict[str, Any]],
        selections: List[Dict[str, Any]],
        manipulated_ids: List[int],
        manipulated_map: Dict[int, List[Dict[str, str]]]
    ) -> Path:
        """Persist analysis summary for UI consumption."""

        root_dir = self.workspace.parent
        summary_path = self.workspace / "output" / "analysis" / f"analysis_summary_{job_reference}.json"
        priority_path = self.workspace / "output" / "analysis" / f"priority_segments_{job_reference}.json"

        def rel_path(path: Optional[Path]) -> Optional[str]:
            if not path:
                return None
            try:
                return os.path.relpath(path, start=root_dir)
            except ValueError:
                return str(path)

        # Persist full priority selection for downstream viewers
        manipulated_set = set(manipulated_ids)
        selection_export = []
        for seg in selections:
            entry = dict(seg)
            seg_id = entry.get('id')
            entry['manipulated'] = bool(seg_id in manipulated_set)
            if seg_id in manipulated_map:
                entry['manipulated_samples'] = manipulated_map.get(seg_id, [])
            selection_export.append(entry)

        with open(priority_path, 'w', encoding='utf-8') as priority_file:
            json.dump(selection_export, priority_file, indent=2, ensure_ascii=False)

        summary = {
            "job_reference": job_reference,
            "mode": mode,
            "timestamp": self.monitor.get_current_time(),
            "processing_time": self.monitor.get_elapsed_time(),
            "original_pdf": rel_path(turnitin_file),
            "processed_document": rel_path(processed_file),
            "report": rel_path(report_path),
            "priority_segments_file": rel_path(priority_path),
            "total_highlights": len(highlights),
            "total_priority": sum(1 for seg in selections if seg.get('selected', True)),
            "color_distribution": self._get_color_distribution(highlights),
            "manipulated_segment_count": len(manipulated_ids),
            "manipulated_segment_ids": manipulated_ids,
            "priority_samples": [
                {
                    "id": seg.get('id'),
                    "page": seg.get('page'),
                    "color": seg.get('color'),
                    "length": seg.get('length'),
                    "text": seg.get('text'),
                    "manipulated": bool(seg.get('id') in manipulated_set),
                    "manipulated_samples": manipulated_map.get(seg.get('id'), [])
                }
                for seg in selections[:10]
            ],
            "manipulated_segments": [
                {
                    "id": seg_id,
                    "samples": manipulated_map.get(seg_id, [])
                }
                for seg_id in manipulated_ids
            ],
        }

        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Analysis summary saved: {summary_path.name}")
        return summary_path
    
    def _get_color_distribution(self, highlights: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate color distribution from highlights"""
        from collections import Counter
        colors = [h.get('color', 'unknown') for h in highlights]
        return dict(Counter(colors))
    
    def process_documents(self, mode: str = "balanced") -> bool:
        """Main processing pipeline"""
        self.monitor.start()
        job_tag = self.job_reference or mode
        
        self.logger.info("=" * 60)
        self.logger.info("🚀 INVISIBLE PLAGIARISM TOOLKIT - PROCESSING STARTED")
        self.logger.info("=" * 60)
        
        # Check dependencies
        if not self.check_dependencies():
            return False
            
        # Find input files
        original_file, turnitin_file = self.find_input_files()
        
        if not original_file or not turnitin_file:
            self.logger.error("Required input files not found!")
            self.logger.info("Please place files in:")
            self.logger.info(f"  - Original DOCX: {self.workspace / 'input' / 'original'}")
            self.logger.info(f"  - Turnitin PDF: {self.workspace / 'input' / 'turnitin'}")
            return False
        
        # OCR PDF for text extraction
        ocr_pdf_path = self.workspace / "temp" / f"ocr_{turnitin_file.name}"
        if not self.ocr_pdf(turnitin_file, ocr_pdf_path):
            self.logger.warning("OCR failed, using original PDF")
            ocr_pdf_path = turnitin_file
        
        # Extract highlights
        highlights = self.extract_highlights(ocr_pdf_path, mode)
        if not highlights:
            self.logger.error("No highlights found in PDF")
            return False
        
        # Filter priority highlights
        selections = self.filter_priority_highlights(highlights, mode)
        if not selections:
            self.logger.error("No priority highlights selected")
            return False
        
        # Apply manipulations
        processed_file, manipulated_map = self.apply_manipulations(original_file, selections, mode)
        if not processed_file:
            self.logger.error("Document manipulation failed")
            return False
        manipulated_ids = sorted(manipulated_map.keys())

        # Generate report
        report_path = self.generate_report(
            original_file, turnitin_file, processed_file, 
            highlights, selections, mode, job_tag, manipulated_ids, manipulated_map
        )

        # Persist analysis summary for UI/monitoring
        summary_path = self.save_analysis_summary(
            job_reference=job_tag,
            mode=mode,
            turnitin_file=turnitin_file,
            processed_file=processed_file,
            report_path=report_path,
            highlights=highlights,
            selections=selections,
            manipulated_ids=manipulated_ids,
            manipulated_map=manipulated_map
        )
        
        # Final summary
        self.logger.info("=" * 60)
        self.logger.info("✅ PROCESSING COMPLETED SUCCESSFULLY")
        self.logger.info("=" * 60)
        self.logger.info(f"📄 Processed Document: {processed_file}")
        self.logger.info(f"📊 Report: {report_path}")
        self.logger.info(f"📁 Analysis Summary: {summary_path}")
        self.logger.info(f"🧩 Segments manipulated: {len(manipulated_ids)}")
        self.logger.info(f"⏱️  Processing Time: {self.monitor.get_elapsed_time():.2f}s")
        
        return True

def create_cli_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Invisible Plagiarism Toolkit - Professional Document Manipulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Processing Modes:
  stealth    - Minimal modifications, highest invisibility
  balanced   - Moderate modifications, good invisibility/coverage balance  
  aggressive - Maximum modifications, highest bypass potential

Usage Examples:
  python main.py --mode balanced
  python main.py --mode stealth --workspace /custom/path
  python main.py --help

Before running:
  1. Place original DOCX in: workspace/input/original/
  2. Place Turnitin PDF in: workspace/input/turnitin/
        """
    )
    
    parser.add_argument(
        '--mode', 
        choices=['stealth', 'balanced', 'aggressive'],
        default='balanced',
        help='Processing mode (default: balanced)'
    )
    
    parser.add_argument(
        '--workspace',
        default='workspace',
        help='Workspace directory path (default: workspace)'
    )
    
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='Check dependencies only'
    )
    
    return parser

def main():
    """Main CLI entry point"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Initialize CLI
    cli = PlagiarismBypassCLI(args.workspace)
    
    # Check dependencies only
    if args.check_deps:
        if cli.check_dependencies():
            print("✅ All dependencies are properly installed")
            return 0
        else:
            print("❌ Missing dependencies")
            return 1
    
    # Process documents
    success = cli.process_documents(args.mode)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
