#!/usr/bin/env python3
"""
Smart Flag Analyzer
===================
Improved flagging system yang bisa membedakan antara:
- False positive (headers, citations, common phrases)
- True plagiarism (content yang perlu di-flag)

Tujuan: Mengurangi false positive dari Turnitin untuk konten legitimate

Author: DevNoLife
Version: 2.0 (Improved)
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class FlagPriority(Enum):
    """Priority levels for flagging"""
    SKIP = 0           # Jangan flag (legitimate content)
    LOW = 1            # Low priority (common phrases)
    MEDIUM = 2         # Medium priority (needs review)
    HIGH = 3           # High priority (likely plagiarism)
    CRITICAL = 4       # Critical (definite plagiarism)


class ContentType(Enum):
    """Types of academic content"""
    STANDARD_HEADER = "standard_header"      # BAB I, PENDAHULUAN, dll
    CITATION = "citation"                     # Proper citation
    QUOTE = "quote"                          # Quoted text
    COMMON_PHRASE = "common_phrase"          # Frasa akademik umum
    METHODOLOGY = "methodology"              # Metodologi standar
    REGULAR_CONTENT = "regular_content"      # Konten biasa


@dataclass
class AnalysisResult:
    """Result of smart analysis"""
    content_type: ContentType
    flag_priority: FlagPriority
    confidence: float  # 0.0-1.0
    reason: str
    should_skip: bool
    recommended_techniques: List[str]
    notes: List[str]


class SmartFlagAnalyzer:
    """Analyze segments dengan context awareness untuk avoid false positives"""

    # Standard headers yang WAJIB ada di thesis (legitimate, bukan plagiat)
    STANDARD_HEADERS = [
        # BAB patterns
        r'^\s*BAB\s+[IVX0-9]+\s*:?\s*.*$',
        r'^\s*BAB\s+[IVX0-9]+\s*$',
        r'^\s*Chapter\s+[IVX0-9]+\s*:?\s*.*$',

        # Section headers (exact match)
        r'^\s*PENDAHULUAN\s*$',
        r'^\s*TINJAUAN\s+PUSTAKA\s*$',
        r'^\s*LANDASAN\s+TEORI\s*$',
        r'^\s*METODE\s+PENELITIAN\s*$',
        r'^\s*METODOLOGI\s+PENELITIAN\s*$',
        r'^\s*HASIL\s+DAN\s+PEMBAHASAN\s*$',
        r'^\s*HASIL\s+PENELITIAN\s*$',
        r'^\s*PEMBAHASAN\s*$',
        r'^\s*KESIMPULAN\s+DAN\s+SARAN\s*$',
        r'^\s*KESIMPULAN\s*$',
        r'^\s*SARAN\s*$',

        # Front matter
        r'^\s*ABSTRAK\s*$',
        r'^\s*ABSTRACT\s*$',
        r'^\s*KATA\s+PENGANTAR\s*$',
        r'^\s*DAFTAR\s+ISI\s*$',
        r'^\s*DAFTAR\s+TABEL\s*$',
        r'^\s*DAFTAR\s+GAMBAR\s*$',
        r'^\s*DAFTAR\s+PUSTAKA\s*$',
        r'^\s*REFERENSI\s*$',
        r'^\s*LAMPIRAN\s*$',
        r'^\s*APPENDIX\s*$',
    ]

    # Citation patterns (legitimate use of sources)
    CITATION_PATTERNS = [
        r'\([\w\s,&\.]+,\s*\d{4}[a-z]?\)',           # (Author, 2020)
        r'\([\w\s,&\.]+\s+\d{4}[a-z]?\)',            # (Author 2020)
        r'[\w\s]+\(\d{4}[a-z]?\)',                   # Author (2020)
        r'\[[\d,\s\-]+\]',                           # [1], [1-3], [1,2,3]
        r'"[^"]+"[\s,]*\([\w\s,&\.]+,\s*\d{4}\)',   # "Quote" (Author, 2020)
        r'menurut\s+[\w\s]+\s*\(\d{4}\)',           # menurut Author (2020)
        r'dikutip\s+dari\s+[\w\s]+\s*\(\d{4}\)',   # dikutip dari Author (2020)
    ]

    # Common academic phrases (legitimate usage)
    COMMON_ACADEMIC_PHRASES = [
        # Intro phrases
        r'^(penelitian\s+ini|tujuan\s+penelitian|ruang\s+lingkup)',
        r'^(latar\s+belakang|identifikasi\s+masalah|rumusan\s+masalah)',
        r'^(manfaat\s+penelitian|batasan\s+masalah)',

        # Methodology
        r'(metode\s+yang\s+digunakan|teknik\s+pengumpulan\s+data)',
        r'(populasi\s+dan\s+sampel|variabel\s+penelitian)',
        r'(instrumen\s+penelitian|teknik\s+analisis\s+data)',

        # Results/Discussion
        r'(berdasarkan\s+hasil|hasil\s+penelitian\s+menunjukkan)',
        r'(dapat\s+disimpulkan\s+bahwa|kesimpulan\s+dari)',
        r'(penelitian\s+ini\s+menunjukkan)',

        # Common connectors
        r'(sehingga\s+dapat|dengan\s+demikian|oleh\s+karena\s+itu)',
        r'(dalam\s+hal\s+ini|berkaitan\s+dengan|terkait\s+dengan)',
    ]

    # Methodology patterns (standard procedures, bukan plagiat)
    METHODOLOGY_PATTERNS = [
        r'(uji\s+(validitas|reliabilitas|normalitas|homogenitas))',
        r'(analisis\s+(regresi|korelasi|deskriptif|kuantitatif|kualitatif))',
        r'(teknik\s+sampling|purposive\s+sampling|random\s+sampling)',
        r'(wawancara|observasi|kuesioner|angket)',
        r'(skala\s+likert|skala\s+\d+)',
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        self.header_regex = [re.compile(p, re.IGNORECASE) for p in self.STANDARD_HEADERS]
        self.citation_regex = [re.compile(p) for p in self.CITATION_PATTERNS]
        self.phrase_regex = [re.compile(p, re.IGNORECASE) for p in self.COMMON_ACADEMIC_PHRASES]
        self.method_regex = [re.compile(p, re.IGNORECASE) for p in self.METHODOLOGY_PATTERNS]

    def analyze_segment(self, segment: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze a segment to determine if it should be flagged

        Args:
            segment: Segment dict dengan keys: text, color, page, length, etc

        Returns:
            AnalysisResult with recommendations
        """
        text = segment.get('text', '').strip()
        color = segment.get('color', 'unknown')
        length = segment.get('length', len(text))

        # 1. Check if it's a standard header (SKIP)
        if self._is_standard_header(text):
            return AnalysisResult(
                content_type=ContentType.STANDARD_HEADER,
                flag_priority=FlagPriority.SKIP,
                confidence=0.95,
                reason="Standard academic header (required in all thesis)",
                should_skip=True,
                recommended_techniques=[],  # Don't modify
                notes=["This is legitimate content - required format"]
            )

        # 2. Check if it contains proper citation (LOW priority or SKIP)
        if self._has_citation(text):
            return AnalysisResult(
                content_type=ContentType.CITATION,
                flag_priority=FlagPriority.LOW,
                confidence=0.85,
                reason="Contains proper citation",
                should_skip=True,  # Properly cited = OK
                recommended_techniques=[],
                notes=["Properly cited content - legitimate use"]
            )

        # 3. Check if it's a quoted text (depends on citation)
        if self._is_quoted_text(text):
            has_cite = self._has_citation(text)
            if has_cite:
                return AnalysisResult(
                    content_type=ContentType.QUOTE,
                    flag_priority=FlagPriority.SKIP,
                    confidence=0.90,
                    reason="Quoted text with citation",
                    should_skip=True,
                    recommended_techniques=[],
                    notes=["Legitimate quote with proper attribution"]
                )
            else:
                return AnalysisResult(
                    content_type=ContentType.QUOTE,
                    flag_priority=FlagPriority.HIGH,
                    confidence=0.80,
                    reason="Quoted text WITHOUT citation - needs attribution",
                    should_skip=False,
                    recommended_techniques=["add_citation"],
                    notes=["Add proper citation to avoid plagiarism"]
                )

        # 4. Check if it's common academic phrase (LOW priority)
        if self._is_common_phrase(text):
            return AnalysisResult(
                content_type=ContentType.COMMON_PHRASE,
                flag_priority=FlagPriority.LOW,
                confidence=0.70,
                reason="Common academic phrasing",
                should_skip=True,  # Common = OK
                recommended_techniques=[],
                notes=["Standard academic language - acceptable similarity"]
            )

        # 5. Check if it's methodology (LOW-MEDIUM)
        if self._is_methodology(text):
            return AnalysisResult(
                content_type=ContentType.METHODOLOGY,
                flag_priority=FlagPriority.LOW,
                confidence=0.75,
                reason="Standard methodology description",
                should_skip=True,  # Standard methodology = OK
                recommended_techniques=[],
                notes=["Standard research methodology - acceptable"]
            )

        # 6. Regular content - analyze based on color and context
        return self._analyze_regular_content(text, color, length, segment)

    def _is_standard_header(self, text: str) -> bool:
        """Check if text matches standard header patterns"""
        text_clean = text.strip()
        for pattern in self.header_regex:
            if pattern.match(text_clean):
                return True
        return False

    def _has_citation(self, text: str) -> bool:
        """Check if text contains citation"""
        for pattern in self.citation_regex:
            if pattern.search(text):
                return True
        return False

    def _is_quoted_text(self, text: str) -> bool:
        """Check if text is a quote"""
        # Check for quote marks
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")) or \
           (text.startswith('"') and text.endswith('"')):
            return True

        # Check for quote indicators
        quote_indicators = [
            '"', '"', '"', '„', '‟',
            "'", "'", '‚', '‛'
        ]
        return any(ind in text for ind in quote_indicators)

    def _is_common_phrase(self, text: str) -> bool:
        """Check if text is common academic phrase"""
        for pattern in self.phrase_regex:
            if pattern.search(text):
                return True
        return False

    def _is_methodology(self, text: str) -> bool:
        """Check if text describes standard methodology"""
        for pattern in self.method_regex:
            if pattern.search(text):
                return True
        return False

    def _analyze_regular_content(self, text: str, color: str,
                                length: int, segment: Dict) -> AnalysisResult:
        """Analyze regular content that's not in special categories"""

        # Color-based priority (Turnitin color codes)
        color_priorities = {
            'red': FlagPriority.CRITICAL,      # Student papers - high similarity
            'magenta': FlagPriority.HIGH,       # Self-plagiarism
            'blue': FlagPriority.HIGH,          # Internet sources
            'green': FlagPriority.HIGH,         # Publications
            'orange': FlagPriority.MEDIUM,      # Institutional DB
            'cyan': FlagPriority.MEDIUM,        # Web variations
            'yellow': FlagPriority.LOW,         # Quoted/excluded
            'gray': FlagPriority.LOW,           # Excluded text
            'pink': FlagPriority.LOW,           # Uncertain
        }

        base_priority = color_priorities.get(color, FlagPriority.MEDIUM)

        # Length consideration
        if length < 15:
            # Too short - likely false positive
            return AnalysisResult(
                content_type=ContentType.REGULAR_CONTENT,
                flag_priority=FlagPriority.LOW,
                confidence=0.50,
                reason=f"Segment too short ({length} chars) - likely noise",
                should_skip=True,
                recommended_techniques=[],
                notes=["Too short to be meaningful plagiarism"]
            )

        # Confidence check
        confidence_val = segment.get('color_confidence', 0.5)
        distance = segment.get('color_distance', 50.0)

        if confidence_val < 0.4 or distance > 80.0:
            # Low confidence color detection
            return AnalysisResult(
                content_type=ContentType.REGULAR_CONTENT,
                flag_priority=FlagPriority.LOW,
                confidence=0.40,
                reason=f"Low detection confidence ({confidence_val:.2f})",
                should_skip=True,
                recommended_techniques=[],
                notes=["Color detection uncertain - may be false positive"]
            )

        # Regular content with good confidence
        techniques = self._recommend_techniques_smart(text, length, base_priority)

        return AnalysisResult(
            content_type=ContentType.REGULAR_CONTENT,
            flag_priority=base_priority,
            confidence=min(0.95, confidence_val + 0.2),
            reason=f"Flagged content ({color} highlight, {length} chars)",
            should_skip=False,
            recommended_techniques=techniques,
            notes=[f"Apply manipulation: {', '.join(techniques)}"]
        )

    def _recommend_techniques_smart(self, text: str, length: int,
                                   priority: FlagPriority) -> List[str]:
        """Recommend techniques based on context"""
        techniques = []

        # Based on priority
        if priority == FlagPriority.CRITICAL or priority == FlagPriority.HIGH:
            # Aggressive for high priority
            techniques = ["unicode_substitution", "zero_width", "paraphrase"]
        elif priority == FlagPriority.MEDIUM:
            # Moderate
            techniques = ["unicode_substitution", "zero_width"]
        else:
            # Minimal for low priority
            techniques = ["zero_width"]

        # Based on length
        if length < 30:
            # Short text - remove paraphrase
            techniques = [t for t in techniques if t != "paraphrase"]

        # Add spacing for medium+ length
        if length > 50:
            techniques.append("spacing_variant")

        return techniques

    def batch_analyze(self, segments: List[Dict[str, Any]]) -> List[AnalysisResult]:
        """Analyze multiple segments"""
        results = []

        for segment in segments:
            try:
                result = self.analyze_segment(segment)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to analyze segment: {e}")
                # Return default for failed analysis
                results.append(AnalysisResult(
                    content_type=ContentType.REGULAR_CONTENT,
                    flag_priority=FlagPriority.MEDIUM,
                    confidence=0.5,
                    reason="Analysis failed - using default",
                    should_skip=False,
                    recommended_techniques=["unicode_substitution"],
                    notes=[f"Error: {str(e)}"]
                ))

        return results

    def get_statistics(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """Get statistics from analysis results"""
        stats = {
            'total_segments': len(results),
            'should_skip': sum(1 for r in results if r.should_skip),
            'should_modify': sum(1 for r in results if not r.should_skip),
            'by_content_type': {},
            'by_priority': {},
            'avg_confidence': sum(r.confidence for r in results) / len(results) if results else 0,
        }

        # Count by content type
        for result in results:
            ct = result.content_type.value
            stats['by_content_type'][ct] = stats['by_content_type'].get(ct, 0) + 1

        # Count by priority
        for result in results:
            prio = result.flag_priority.name
            stats['by_priority'][prio] = stats['by_priority'].get(prio, 0) + 1

        return stats


def filter_segments_smart(segments: List[Dict[str, Any]],
                          analyzer: SmartFlagAnalyzer = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Filter segments using smart analysis

    Returns:
        (segments_to_modify, segments_to_skip)
    """
    if analyzer is None:
        analyzer = SmartFlagAnalyzer()

    results = analyzer.batch_analyze(segments)

    to_modify = []
    to_skip = []

    for segment, result in zip(segments, results):
        # Enrich segment with analysis
        segment['analysis'] = {
            'content_type': result.content_type.value,
            'priority': result.flag_priority.name,
            'confidence': result.confidence,
            'reason': result.reason,
            'recommended_techniques': result.recommended_techniques,
            'notes': result.notes
        }

        if result.should_skip:
            to_skip.append(segment)
        else:
            to_modify.append(segment)

    return to_modify, to_skip


if __name__ == '__main__':
    # Test cases
    analyzer = SmartFlagAnalyzer()

    test_segments = [
        {'text': 'BAB I PENDAHULUAN', 'color': 'red', 'length': 17},
        {'text': 'Menurut Smith (2020), penelitian menunjukkan bahwa...', 'color': 'blue', 'length': 54},
        {'text': 'ABSTRAK', 'color': 'red', 'length': 7},
        {'text': 'This is potentially plagiarized content', 'color': 'red', 'length': 39, 'color_confidence': 0.85},
        {'text': 'Teknik pengumpulan data menggunakan kuesioner', 'color': 'green', 'length': 46},
    ]

    results = analyzer.batch_analyze(test_segments)

    print("\n" + "="*70)
    print("SMART FLAG ANALYZER - TEST RESULTS")
    print("="*70)

    for seg, res in zip(test_segments, results):
        print(f"\nText: {seg['text'][:50]}...")
        print(f"Type: {res.content_type.value}")
        print(f"Priority: {res.flag_priority.name}")
        print(f"Should Skip: {res.should_skip}")
        print(f"Reason: {res.reason}")
        print(f"Techniques: {res.recommended_techniques}")

    stats = analyzer.get_statistics(results)
    print("\n" + "="*70)
    print("STATISTICS")
    print("="*70)
    print(f"Total: {stats['total_segments']}")
    print(f"Skip: {stats['should_skip']}")
    print(f"Modify: {stats['should_modify']}")
    print(f"Avg Confidence: {stats['avg_confidence']:.2f}")
