#!/usr/bin/env python3
"""
Flag Validator & Improved Extraction
====================================
Solve masalah flag/highlight extraction dari Turnitin PDF:
1. Validate extracted highlights
2. Cross-reference dengan original DOCX
3. Fix common extraction errors
4. Provide confidence scores

Author: DevNoLife
Version: 2.0 (Improved)
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from difflib import SequenceMatcher
from pathlib import Path


class FlagValidator:
    """Validate dan improve flag extraction dari PDF"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # Minimum similarity untuk valid match
        self.min_similarity = 0.70

        # Maximum acceptable length difference
        self.max_length_diff_ratio = 0.50  # 50%

    def validate_highlight(self, highlight: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single highlight extraction

        Args:
            highlight: Highlight dict dengan keys: text, color, bbox, etc

        Returns:
            Enhanced highlight dengan validation info
        """
        text = highlight.get('text', '').strip()
        color = highlight.get('color', 'unknown')
        source = highlight.get('source', 'unknown')

        issues = []
        warnings = []
        confidence = 1.0

        # 1. Check text length
        if not text:
            issues.append("Empty text")
            confidence = 0.0
        elif len(text) < 5:
            warnings.append("Very short text (possible noise)")
            confidence *= 0.7

        # 2. Check for OCR artifacts
        if text:
            # Check for excessive special characters (OCR errors)
            special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
            special_ratio = special_count / len(text)

            if special_ratio > 0.3:
                warnings.append(f"High special char ratio ({special_ratio:.1%})")
                confidence *= 0.8

            # Check for gibberish (no vowels, too many consonants)
            if len(text) > 10:
                vowels = sum(1 for c in text.lower() if c in 'aeiou')
                vowel_ratio = vowels / len(text)

                if vowel_ratio < 0.15:  # Less than 15% vowels
                    warnings.append(f"Low vowel ratio ({vowel_ratio:.1%}) - possible OCR error")
                    confidence *= 0.7

        # 3. Check color detection
        color_confidence = highlight.get('color_confidence', 0.0)
        if color_confidence < 0.5:
            warnings.append(f"Low color confidence ({color_confidence:.2f})")
            confidence *= 0.9

        # 4. Check source reliability
        if source == 'annotation':
            # Native annotations are more reliable
            confidence *= 1.1  # Boost
        elif source == 'ocr':
            # OCR-based extraction less reliable
            confidence *= 0.9

        # Cap confidence at 1.0
        confidence = min(1.0, confidence)

        # Build validation result
        validation = {
            'is_valid': len(issues) == 0,
            'confidence': confidence,
            'issues': issues,
            'warnings': warnings,
            'quality': self._get_quality_label(confidence)
        }

        # Add to highlight
        highlight['validation'] = validation

        return highlight

    def _get_quality_label(self, confidence: float) -> str:
        """Get quality label from confidence score"""
        if confidence >= 0.90:
            return "EXCELLENT"
        elif confidence >= 0.75:
            return "GOOD"
        elif confidence >= 0.60:
            return "FAIR"
        elif confidence >= 0.40:
            return "POOR"
        else:
            return "UNRELIABLE"

    def cross_reference_with_docx(self, highlights: List[Dict[str, Any]],
                                 docx_paragraphs: List[str]) -> List[Dict[str, Any]]:
        """
        Cross-reference extracted highlights dengan original DOCX text

        Args:
            highlights: List of highlight dicts dari PDF
            docx_paragraphs: List of paragraph texts dari DOCX

        Returns:
            Enhanced highlights dengan matching info
        """
        self.logger.info(f"Cross-referencing {len(highlights)} highlights with {len(docx_paragraphs)} paragraphs")

        enhanced = []

        for highlight in highlights:
            text = highlight.get('text', '').strip()
            if not text:
                continue

            # Find best matching paragraph in DOCX
            best_match = self._find_best_match(text, docx_paragraphs)

            if best_match:
                highlight['docx_match'] = {
                    'paragraph_index': best_match['index'],
                    'paragraph_text': best_match['text'][:100] + '...',  # Preview
                    'similarity': best_match['similarity'],
                    'match_type': best_match['match_type'],
                    'matched': True
                }

                # Adjust confidence based on match quality
                validation = highlight.get('validation', {})
                old_conf = validation.get('confidence', 1.0)
                new_conf = old_conf * (0.5 + 0.5 * best_match['similarity'])
                validation['confidence'] = new_conf
                validation['quality'] = self._get_quality_label(new_conf)
                highlight['validation'] = validation

            else:
                highlight['docx_match'] = {
                    'matched': False,
                    'reason': 'No similar paragraph found in DOCX'
                }

                # Lower confidence for unmatched
                validation = highlight.get('validation', {})
                validation['confidence'] *= 0.5
                validation['warnings'].append("Not found in original DOCX")
                highlight['validation'] = validation

            enhanced.append(highlight)

        # Statistics
        matched = sum(1 for h in enhanced if h['docx_match'].get('matched'))
        self.logger.info(f"Cross-reference complete: {matched}/{len(enhanced)} matched ({matched/len(enhanced)*100:.1f}%)")

        return enhanced

    def _find_best_match(self, text: str, paragraphs: List[str]) -> Optional[Dict[str, Any]]:
        """Find best matching paragraph for a highlight text"""
        text_clean = self._clean_text(text)

        if not text_clean:
            return None

        best_match = None
        best_similarity = 0.0

        for idx, para in enumerate(paragraphs):
            para_clean = self._clean_text(para)

            if not para_clean:
                continue

            # Try exact match first
            if text_clean == para_clean:
                return {
                    'index': idx,
                    'text': para,
                    'similarity': 1.0,
                    'match_type': 'exact'
                }

            # Try substring match
            if text_clean in para_clean:
                similarity = len(text_clean) / len(para_clean)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        'index': idx,
                        'text': para,
                        'similarity': similarity,
                        'match_type': 'substring'
                    }
                continue

            if para_clean in text_clean:
                similarity = len(para_clean) / len(text_clean)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        'index': idx,
                        'text': para,
                        'similarity': similarity,
                        'match_type': 'substring_reverse'
                    }
                continue

            # Fuzzy match
            similarity = SequenceMatcher(None, text_clean, para_clean).ratio()
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    'index': idx,
                    'text': para,
                    'similarity': similarity,
                    'match_type': 'fuzzy'
                }

        # Only return if similarity meets threshold
        if best_match and best_similarity >= self.min_similarity:
            return best_match

        return None

    def _clean_text(self, text: str) -> str:
        """Clean text for comparison"""
        # Lowercase
        text = text.lower()

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Remove common punctuation
        text = re.sub(r'[^\w\s]', '', text)

        return text.strip()

    def filter_by_confidence(self, highlights: List[Dict[str, Any]],
                           min_confidence: float = 0.60) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter highlights by validation confidence

        Args:
            highlights: List of highlights dengan validation info
            min_confidence: Minimum confidence threshold

        Returns:
            (high_confidence_highlights, low_confidence_highlights)
        """
        high_conf = []
        low_conf = []

        for h in highlights:
            validation = h.get('validation', {})
            confidence = validation.get('confidence', 0.0)

            if confidence >= min_confidence:
                high_conf.append(h)
            else:
                low_conf.append(h)

        self.logger.info(f"Filtered by confidence (>= {min_confidence}):")
        self.logger.info(f"  - High confidence: {len(high_conf)}")
        self.logger.info(f"  - Low confidence: {len(low_conf)}")

        return high_conf, low_conf

    def fix_common_extraction_errors(self, highlights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fix common extraction errors automatically

        Args:
            highlights: List of highlights

        Returns:
            Fixed highlights
        """
        fixed = []

        for h in highlights.copy():
            text = h.get('text', '')

            # 1. Fix excessive whitespace
            text = ' '.join(text.split())

            # 2. Fix broken words (common OCR issue)
            # Example: "te xt" -> "text"
            text = self._fix_broken_words(text)

            # 3. Remove leading/trailing special chars
            text = text.strip('.,;:-_+=*&^%$#@!~`')

            # 4. Fix common OCR substitutions
            text = self._fix_ocr_errors(text)

            # Update text
            h['text'] = text

            # Skip if empty after fixing
            if not text.strip():
                continue

            fixed.append(h)

        self.logger.info(f"Fixed {len(highlights) - len(fixed)} empty highlights")

        return fixed

    def _fix_broken_words(self, text: str) -> str:
        """Fix words broken by OCR errors"""
        # Simple heuristic: merge single chars with next word
        words = text.split()
        fixed_words = []

        i = 0
        while i < len(words):
            word = words[i]

            # If single char and next word exists, try to merge
            if len(word) == 1 and i + 1 < len(words):
                next_word = words[i + 1]
                # Merge if next word starts with lowercase (likely continuation)
                if next_word and next_word[0].islower():
                    fixed_words.append(word + next_word)
                    i += 2
                    continue

            fixed_words.append(word)
            i += 1

        return ' '.join(fixed_words)

    def _fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR character substitution errors"""
        # Common OCR mistakes
        replacements = {
            ' 0 ': ' o ',  # Zero to O (in words)
            ' l ': ' I ',  # Lowercase L to I (in words)
            ' | ': ' I ',  # Pipe to I
        }

        for wrong, right in replacements.items():
            text = text.replace(wrong, right)

        return text

    def generate_validation_report(self, highlights: List[Dict[str, Any]]) -> str:
        """Generate validation report"""
        total = len(highlights)
        valid = sum(1 for h in highlights if h.get('validation', {}).get('is_valid', False))
        matched = sum(1 for h in highlights if h.get('docx_match', {}).get('matched', False))

        # Quality distribution
        quality_dist = {}
        for h in highlights:
            quality = h.get('validation', {}).get('quality', 'UNKNOWN')
            quality_dist[quality] = quality_dist.get(quality, 0) + 1

        # Average confidence
        confidences = [h.get('validation', {}).get('confidence', 0.0) for h in highlights]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        report = f"""
{'='*70}
HIGHLIGHT VALIDATION REPORT
{'='*70}

Total Highlights: {total}
Valid: {valid} ({valid/total*100:.1f}%)
Matched to DOCX: {matched} ({matched/total*100:.1f}%)
Average Confidence: {avg_conf:.2f}

Quality Distribution:
"""
        for quality in ['EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'UNRELIABLE']:
            count = quality_dist.get(quality, 0)
            if count > 0:
                report += f"  - {quality}: {count} ({count/total*100:.1f}%)\n"

        report += f"\n{'='*70}\n"

        return report


def validate_and_enhance_highlights(highlights: List[Dict[str, Any]],
                                   docx_paragraphs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Helper function untuk validate dan enhance highlights

    Args:
        highlights: Raw highlights dari PDF extraction
        docx_paragraphs: Optional list of paragraphs dari DOCX untuk cross-reference

    Returns:
        Enhanced and validated highlights
    """
    validator = FlagValidator()

    # 1. Validate each highlight
    validated = [validator.validate_highlight(h) for h in highlights]

    # 2. Fix common errors
    fixed = validator.fix_common_extraction_errors(validated)

    # 3. Cross-reference dengan DOCX if available
    if docx_paragraphs:
        enhanced = validator.cross_reference_with_docx(fixed, docx_paragraphs)
    else:
        enhanced = fixed

    # 4. Generate report
    report = validator.generate_validation_report(enhanced)
    print(report)

    return enhanced


if __name__ == '__main__':
    # Test
    print("="*70)
    print("FLAG VALIDATOR - TEST")
    print("="*70)

    # Sample highlights (simulated PDF extraction)
    test_highlights = [
        {
            'text': 'BAB I PENDAHULUAN',
            'color': 'red',
            'color_confidence': 0.95,
            'source': 'annotation'
        },
        {
            'text': 'Penelitian ini bertujuan untuk menganalisis',
            'color': 'blue',
            'color_confidence': 0.80,
            'source': 'ocr'
        },
        {
            'text': 'te xt with br0ken w0rds',  # OCR errors
            'color': 'green',
            'color_confidence': 0.60,
            'source': 'ocr'
        },
        {
            'text': '###@@@',  # Noise/artifacts
            'color': 'yellow',
            'color_confidence': 0.30,
            'source': 'ocr'
        }
    ]

    # Sample DOCX paragraphs
    docx_paras = [
        'BAB I PENDAHULUAN',
        'Penelitian ini bertujuan untuk menganalisis berbagai faktor',
        'text with broken words should match this',
        'Other content here'
    ]

    # Validate
    validated = validate_and_enhance_highlights(test_highlights, docx_paras)

    print("\nValidation Results:")
    for i, h in enumerate(validated, 1):
        val = h['validation']
        match = h.get('docx_match', {})
        print(f"\n{i}. Text: {h['text'][:50]}")
        print(f"   Quality: {val['quality']} (conf: {val['confidence']:.2f})")
        print(f"   Matched: {match.get('matched', False)}")
        if match.get('matched'):
            print(f"   Match type: {match['match_type']} (sim: {match['similarity']:.2f})")
