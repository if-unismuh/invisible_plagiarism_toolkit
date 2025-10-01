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
import math
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import docx

# Add src to path for imports regardless of launch location
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from core.invisible_manipulator import InvisibleManipulator
from extractors.pdf_colored_ocr_extractor import extract_colored_regions
from processors.flagged_selection_builder import build_selection, load_segments
# from processors.targeted_invisible_applier import load_selection as load_flagged_selection
from utils.logger_config import setup_logger
from utils.performance_monitor import PerformanceMonitor

DEFAULT_PROTECTED_TERMS = [
    "bab i",
    "bab ii",
    "bab iii",
    "bab iv",
    "bab v",
    "bab 1",
    "bab 2",
    "bab 3",
    "bab 4",
    "pendahuluan",
    "abstrak",
    "abstract",
    "kata pengantar",
    "daftar pustaka",
    "kesimpulan",
    "saran",
    "lampiran"
]


TURNITIN_FLAG_PROFILES: dict[str, dict[str, str]] = {
    "red": {
        "turnitin_flag": "Student Papers",
        "flag_source": "student_papers",
        "flag_priority": "high",
        "flag_description": "Matches submissions from other students in the Turnitin index.",
    },
    "magenta": {
        "turnitin_flag": "Self-Plagiarism",
        "flag_source": "self_plagiarism",
        "flag_priority": "high",
        "flag_description": "Segments overlapping with the author's previous submissions.",
    },
    "green": {
        "turnitin_flag": "Publications / Journals",
        "flag_source": "publications",
        "flag_priority": "high",
        "flag_description": "Matches academic publications or journal articles.",
    },
    "blue": {
        "turnitin_flag": "Internet Sources",
        "flag_source": "internet_sources",
        "flag_priority": "high",
        "flag_description": "Content found on public web sources indexed by Turnitin.",
    },
    "cyan": {
        "turnitin_flag": "Institution Repositories",
        "flag_source": "institutional_repository",
        "flag_priority": "medium",
        "flag_description": "Matches campus or partner institutional archives.",
    },
    "orange": {
        "turnitin_flag": "Institution Database",
        "flag_source": "institution_database",
        "flag_priority": "medium",
        "flag_description": "Matches curated institution-specific databases.",
    },
    "yellow": {
        "turnitin_flag": "Quoted Text",
        "flag_source": "quoted_text",
        "flag_priority": "medium",
        "flag_description": "Typically text that appears inside quotations.",
    },
    "gray": {
        "turnitin_flag": "Excluded Text",
        "flag_source": "excluded",
        "flag_priority": "low",
        "flag_description": "Turnitin-marked regions excluded from similarity scoring.",
    },
    "other": {
        "turnitin_flag": "Unclassified Highlight",
        "flag_source": "other",
        "flag_priority": "low",
        "flag_description": "Detected highlight with ambiguous Turnitin classification.",
    },
}

FLAG_PRIORITY_WEIGHTS = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "other": 0,
}


class PlagiarismBypassCLI:
    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace = Path(workspace_dir)
        self.logger = setup_logger(__name__)
        self.monitor = PerformanceMonitor()
        self.job_reference = os.getenv("IPT_JOB_ID")
        self.setup_workspace()
        self.config_data = self._load_config()
        self.paraphrase_min_words = int(self.config_data.get('paraphrase_min_words', 8))
        self.protected_literals, self.protected_regex = self._compile_protected_patterns(
            self.config_data.get('protected_terms', DEFAULT_PROTECTED_TERMS)
        )
        
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
        
    def _load_config(self) -> Dict[str, Any]:
        config_path = Path('config.json')
        if config_path.exists():
            try:
                with config_path.open('r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as exc:
                self.logger.warning("Gagal memuat config.json: %s", exc)
        return {}

    def _compile_protected_patterns(self, items: List[str]) -> Tuple[List[str], List[re.Pattern]]:
        literals: List[str] = []
        regexes: List[re.Pattern] = []
        for raw in items:
            if not raw:
                continue
            if raw.startswith('regex:'):
                pattern = raw[6:]
                try:
                    regexes.append(re.compile(pattern, re.IGNORECASE))
                except re.error as exc:
                    self.logger.warning("Pola regex tidak valid '%s': %s", pattern, exc)
            else:
                normalized = re.sub(r"\s+", " ", raw.lower()).strip()
                if normalized:
                    literals.append(normalized)
        return literals, regexes

    def _is_protected_text(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", (text or '').lower()).strip()
        if not normalized:
            return False
        for literal in self.protected_literals:
            if literal and literal in normalized:
                return True
        for pattern in self.protected_regex:
            if pattern.search(normalized):
                return True
        return False

    def _allow_paraphrase(self, text: str) -> bool:
        if not text:
            return False
        if self._is_protected_text(text):
            return False
        words = re.findall(r"\w+", text, flags=re.UNICODE)
        if len(words) < self.paraphrase_min_words:
            return False
        return True

    @staticmethod
    def _normalize_turnitin_color(color: Optional[str]) -> str:
        if not color:
            return "other"
        name = color.strip().lower()
        if not name:
            return "other"
        alias_map = {
            "purple": "magenta",
            "violet": "magenta",
            "fuchsia": "magenta",
            "pink": "magenta",
            "teal": "cyan",
            "aqua": "cyan",
            "turquoise": "cyan",
            "light": "yellow",
            "grey": "gray",
            "dark": "other",
        }
        return alias_map.get(name, name)

    @staticmethod
    def _resolve_turnitin_flag_info(
        color: str,
        confidence: float,
        palette_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Map normalized color to Turnitin flag metadata with confidence adjustments."""
        normalized_color = PlagiarismBypassCLI._normalize_turnitin_color(color)
        base_profile = dict(TURNITIN_FLAG_PROFILES.get(normalized_color, TURNITIN_FLAG_PROFILES["other"]))

        initial_priority = base_profile.get("flag_priority", "other")
        adjustments: List[str] = []
        adjusted_priority = initial_priority

        if confidence < 0.20:
            adjusted_priority = "low"
            adjustments.append("confidence < 0.20")
        elif confidence < 0.35 and initial_priority == "high":
            adjusted_priority = "medium"
            adjustments.append("confidence < 0.35 for high-priority color")
        elif confidence < 0.30 and initial_priority == "medium":
            adjusted_priority = "low"
            adjustments.append("confidence < 0.30 for medium-priority color")

        if palette_hint and palette_hint != normalized_color and confidence < 0.60:
            adjustments.append(f"palette voted {palette_hint}")

        priority_score = FLAG_PRIORITY_WEIGHTS.get(adjusted_priority, 0)
        description = base_profile.get("flag_description", "")
        if adjustments:
            adjustment_text = ", ".join(adjustments)
            description = (description + " " + f"(Adjusted: {adjustment_text})").strip()

        return {
            "turnitin_flag": base_profile.get("turnitin_flag", "Unclassified Highlight"),
            "flag_source": base_profile.get("flag_source", normalized_color),
            "flag_priority": adjusted_priority,
            "flag_priority_initial": initial_priority,
            "flag_priority_score": priority_score,
            "flag_confidence": round(max(0.0, min(1.0, confidence)), 4),
            "flag_notes": description,
        }

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
        
        passes = [
            {
                "tag": "baseline",
                "min_area": config["min_area"],
                "aggressive": config["aggressive"],
                "max_coverage": config["max_coverage"],
            },
            {
                "tag": "aggressive",
                "min_area": max(400, int(config["min_area"] * 0.65)),
                "aggressive": True,
                "max_coverage": min(0.9, config["max_coverage"] + 0.2),
            },
            {
                "tag": "low_area",
                "min_area": max(250, int(config["min_area"] * 0.45)),
                "aggressive": config["aggressive"],
                "max_coverage": min(0.85, config["max_coverage"] + 0.1),
            },
        ]

        combined: Dict[tuple, Dict[str, Any]] = {}
        counts: Dict[str, int] = {}

        def normalize_text(value: str) -> str:
            return re.sub(r"\s+", " ", value.strip()).lower()

        priority_rank = {
            "red": 0,
            "magenta": 1,
            "green": 2,
            "blue": 3,
            "cyan": 4,
            "orange": 5,
            "yellow": 6,
            "gray": 7,
            "other": 8,
        }

        def choose_color(candidates: Dict[str, Dict[str, Any]]) -> str:
            if not candidates:
                return "other"

            def sort_key(item):
                name, meta = item
                distance = meta.get("distance")
                if not isinstance(distance, (int, float)) or not math.isfinite(distance):
                    distance = float("inf")
                return (
                    priority_rank.get(name, 99),
                    -meta.get("confidence", 0.0),
                    distance,
                )

            return min(candidates.items(), key=sort_key)[0]

        for cfg in passes:
            try:
                result = extract_colored_regions(
                    pdf_path,
                    min_area=cfg["min_area"],
                    aggressive=cfg["aggressive"],
                    max_coverage=cfg["max_coverage"],
                    merge=True,
                    ocr_lang="ind+eng",
                )
            except Exception as exc:
                self.logger.warning(
                    "Highlight extraction pass '%s' failed: %s",
                    cfg["tag"],
                    exc,
                )
                continue

            counts[cfg["tag"]] = len(result)

            for item in result:
                page = item.get("page_number")
                text = (item.get("text") or "").strip()
                if not text:
                    continue
                key = (page, normalize_text(text))
                color_raw = item.get("color", "other")
                color_norm = self._normalize_turnitin_color(color_raw)
                profile_raw = item.get("color_profile", color_raw)
                profile_norm = self._normalize_turnitin_color(profile_raw)
                confidence = float(item.get("color_confidence", 0.0) or 0.0)
                distance_value = item.get("color_distance")
                try:
                    distance = float(distance_value)
                except (TypeError, ValueError):
                    distance = float("inf")

                entry = combined.setdefault(
                    key,
                    {
                        "page_number": page,
                        "text": text,
                        "colors": set(),
                        "color_meta": {},
                        "sources": [],
                    },
                )
                entry["colors"].add(color_norm)
                entry["sources"].append(cfg["tag"])
                meta = entry.setdefault("color_meta", {})
                stats = meta.setdefault(
                    color_norm,
                    {
                        "confidence": 0.0,
                        "distance": float("inf"),
                        "raw": color_raw,
                        "profile": profile_norm,
                    },
                )
                if confidence > stats.get("confidence", 0.0):
                    stats["confidence"] = confidence
                if distance < stats.get("distance", float("inf")):
                    stats["distance"] = distance
                if not stats.get("raw"):
                    stats["raw"] = color_raw
                if profile_norm and stats.get("profile") != profile_norm:
                    stats["profile"] = profile_norm

        highlights = []
        for entry in combined.values():
            color_meta = entry.pop("color_meta", {})
            colors = list(entry.pop("colors"))
            colors.sort(key=lambda c: priority_rank.get(c, 99))
            sanitized_meta: Dict[str, Dict[str, Any]] = {}
            for name, meta in color_meta.items():
                sanitized: Dict[str, Any] = {
                    "confidence": float(meta.get("confidence", 0.0) or 0.0),
                    "raw": meta.get("raw"),
                    "profile": meta.get("profile"),
                }
                dist_val = meta.get("distance")
                if isinstance(dist_val, (int, float)) and math.isfinite(dist_val):
                    sanitized["distance"] = float(dist_val)
                else:
                    sanitized["distance"] = None
                sanitized_meta[name] = sanitized
            entry["color_sources"] = colors
            entry["color_candidates"] = sanitized_meta
            entry["color"] = choose_color(sanitized_meta)
            chosen_meta = sanitized_meta.get(entry["color"], {})
            entry["color_confidence"] = chosen_meta.get("confidence", 0.0)
            distance_val = chosen_meta.get("distance")
            if isinstance(distance_val, (int, float)) and math.isfinite(distance_val):
                entry["color_distance"] = float(distance_val)
            else:
                entry["color_distance"] = None
            entry["color_profile"] = chosen_meta.get("profile", entry["color"])
            entry["color_raw"] = chosen_meta.get("raw", entry["color"])

            flag_info = self._resolve_turnitin_flag_info(
                entry["color"],
                entry["color_confidence"],
                entry.get("color_profile"),
            )
            for key, value in flag_info.items():
                entry[key] = value

            highlights.append(entry)

        total = len(highlights)
        self.logger.info(
            "Aggregated %s unique highlights (baseline=%s aggressive=%s low_area=%s)",
            total,
            counts.get("baseline", 0),
            counts.get("aggressive", 0),
            counts.get("low_area", 0),
        )
        return highlights
    
    def filter_priority_highlights(
        self,
        highlights: List[Dict[str, Any]],
        mode: str = "balanced",
    ) -> List[Dict[str, Any]]:
        """Filter highlights by Turnitin priority policy and confidence."""

        priority_palette = {
            color: profile.get("flag_priority", "other")
            for color, profile in TURNITIN_FLAG_PROFILES.items()
        }

        policy = {
            "stealth": {"priorities": {"high"}, "min_length": 15, "min_conf": 0.35},
            "balanced": {"priorities": {"high", "medium"}, "min_length": 10, "min_conf": 0.25},
            "aggressive": {"priorities": {"high", "medium", "low"}, "min_length": 6, "min_conf": 0.15},
        }.get(mode, {"priorities": {"high", "medium"}, "min_length": 10, "min_conf": 0.25})

        allowed_priorities = policy["priorities"]
        min_length = policy["min_length"]
        min_confidence = policy["min_conf"]

        filtered: List[Dict[str, Any]] = []
        for segment in highlights:
            text = (segment.get("text") or "").strip()
            if not text:
                continue

            normalized_color = self._normalize_turnitin_color(segment.get("color"))
            color_confidence = float(segment.get("color_confidence", 0.0) or 0.0)
            flag_priority = segment.get("flag_priority")
            if not flag_priority:
                derived_flag = self._resolve_turnitin_flag_info(
                    normalized_color,
                    color_confidence,
                    segment.get("color_profile"),
                )
                for key, value in derived_flag.items():
                    segment.setdefault(key, value)
                flag_priority = segment.get("flag_priority")

            if flag_priority not in allowed_priorities:
                continue

            flag_confidence = float(segment.get("flag_confidence", color_confidence) or 0.0)
            if flag_confidence < min_confidence:
                continue

            filtered.append(segment)

        if not filtered:
            self.logger.warning(
                "No highlights met confidence/priority policy for mode '%s'; "
                "falling back to color-only filtering.",
                mode,
            )
            fallback_colors = {
                color
                for color, priority in priority_palette.items()
                if priority in allowed_priorities
            }
            if not fallback_colors:
                fallback_colors = set(TURNITIN_FLAG_PROFILES.keys())
            selection = build_selection(
                highlights,
                min_length=min_length,
                include=fallback_colors,
                exclude=set(),
                dedupe=True,
            )
            return selection

        selection = build_selection(
            filtered,
            min_length=min_length,
            include=set(),
            exclude=set(),
            dedupe=True,
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
                paraphrase_cfg.setdefault('clause_swap_rate', 0.25)
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
                techniques = list(seg.get('recommended_techniques', []))
                if 'paraphrase' in techniques and not self._allow_paraphrase(text):
                    techniques = [t for t in techniques if t != 'paraphrase']
                seg['recommended_techniques'] = techniques
                prepared_selections.append({
                    'id': seg.get('id'),
                    'text': text,
                    'text_lower': text.lower(),
                    'techniques': techniques
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
                "flag_priority_distribution": self._get_distribution(highlights, 'flag_priority'),
                "flag_label_distribution": self._get_distribution(highlights, 'turnitin_flag'),
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
            "flag_priority_distribution": self._get_distribution(highlights, 'flag_priority'),
            "flag_label_distribution": self._get_distribution(highlights, 'turnitin_flag'),
            "manipulated_segment_count": len(manipulated_ids),
            "manipulated_segment_ids": manipulated_ids,
            "priority_samples": [
                {
                    "id": seg.get('id'),
                    "page": seg.get('page'),
                    "color": seg.get('color'),
                    "turnitin_flag": seg.get('turnitin_flag'),
                    "flag_priority": seg.get('flag_priority'),
                    "flag_confidence": seg.get('flag_confidence'),
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
    
    def _get_distribution(
        self,
        highlights: List[Dict[str, Any]],
        key: str,
        default: str = "unknown",
    ) -> Dict[str, int]:
        from collections import Counter

        values = []
        for item in highlights:
            value = item.get(key, default)
            if value is None:
                value = default
            if isinstance(value, str):
                value = value or default
            values.append(value)
        return dict(Counter(values))

    def _get_color_distribution(self, highlights: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate color distribution from highlights"""
        return self._get_distribution(highlights, 'color')
    
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
