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

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

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
        
        cmd = ['ocrmypdf', str(input_pdf), str(output_pdf)]
        if force:
            cmd.append('--force-ocr')
        cmd.extend(['--language', 'ind+eng', '--optimize', '1'])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                self.logger.info(f"OCR completed successfully: {output_pdf.name}")
                return True
            else:
                self.logger.error(f"OCR failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("OCR timeout after 5 minutes")
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
                          mode: str = "balanced") -> Optional[Path]:
        """Apply invisible manipulations to original document"""
        
        # Mode settings for manipulation rates
        rates = {
            "stealth": {"unicode": 0.02, "zero_width": 0.03},
            "balanced": {"unicode": 0.04, "zero_width": 0.06},
            "aggressive": {"unicode": 0.07, "zero_width": 0.10}
        }
        
        config = rates.get(mode, rates["balanced"])
        
        # Output path
        output_path = self.workspace / "output" / "processed" / f"{original_docx.stem}_{mode}_processed.docx"
        
        try:
            # Use InvisibleManipulator for comprehensive processing
            manipulator = InvisibleManipulator(verbose=True)
            
            # Enable debug flags if needed (passed from CLI args later)
            # This will be updated when we call process_documents
            
            # Apply full manipulation pipeline
            result = manipulator.apply_invisible_manipulation(
                str(original_docx),
                str(output_path),
                dry_run=False
            )
            
            if result and result.get('output_file'):
                self.logger.info(f"Document processed successfully: {output_path.name}")
                return Path(result['output_file'])
            else:
                self.logger.error("Document processing failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Manipulation failed: {e}")
            return None
    
    def generate_report(self, original_file: Path, turnitin_file: Path, 
                       processed_file: Optional[Path], highlights: List[Dict[str, Any]],
                       selections: List[Dict[str, Any]], mode: str) -> Path:
        """Generate comprehensive processing report"""
        
        report_data = {
            "processing_info": {
                "mode": mode,
                "timestamp": self.monitor.get_current_time(),
                "processing_time": self.monitor.get_elapsed_time()
            },
            "input_files": {
                "original_document": str(original_file.name),
                "turnitin_report": str(turnitin_file.name)
            },
            "analysis_results": {
                "total_highlights": len(highlights),
                "selected_segments": len(selections),
                "color_distribution": self._get_color_distribution(highlights)
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
        
        report_path = self.workspace / "output" / "reports" / f"processing_report_{mode}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Report generated: {report_path.name}")
        return report_path
    
    def _get_color_distribution(self, highlights: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate color distribution from highlights"""
        from collections import Counter
        colors = [h.get('color', 'unknown') for h in highlights]
        return dict(Counter(colors))
    
    def process_documents(self, mode: str = "balanced") -> bool:
        """Main processing pipeline"""
        self.monitor.start()
        
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
        processed_file = self.apply_manipulations(original_file, selections, mode)
        if not processed_file:
            self.logger.error("Document manipulation failed")
            return False
        
        # Generate report
        report_path = self.generate_report(
            original_file, turnitin_file, processed_file, 
            highlights, selections, mode
        )
        
        # Final summary
        self.logger.info("=" * 60)
        self.logger.info("✅ PROCESSING COMPLETED SUCCESSFULLY")
        self.logger.info("=" * 60)
        self.logger.info(f"📄 Processed Document: {processed_file}")
        self.logger.info(f"📊 Report: {report_path}")
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
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with visual flags (highlights changes in document)'
    )
    
    parser.add_argument(
        '--no-change-log',
        action='store_true',
        help='Disable embedded change log in output document'
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
    
    # Update config for debug mode if enabled
    if args.debug:
        print("🐛 Debug mode enabled - visual flags will be added to document")
        import json
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            config.setdefault('debug', {})['enable_visual_flags'] = True
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
    
    if args.no_change_log:
        print("📝 Change log disabled")
        import json
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            config.setdefault('debug', {})['enable_change_log'] = False
            config['debug']['export_change_log'] = False
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
    
    # Process documents
    success = cli.process_documents(args.mode)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
