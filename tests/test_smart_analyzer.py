#!/usr/bin/env python3
"""
Tests for Smart Flag Analyzer
Validate that it correctly identifies false positives
"""

import sys
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from processors.smart_flag_analyzer import (
    SmartFlagAnalyzer,
    FlagPriority,
    ContentType,
    filter_segments_smart
)


class TestSmartFlagAnalyzer:
    """Test suite for smart flag analyzer"""

    def setup_method(self):
        """Setup for each test"""
        self.analyzer = SmartFlagAnalyzer()

    def test_standard_header_detection(self):
        """Test that standard headers are correctly identified and skipped"""
        test_cases = [
            {'text': 'BAB I PENDAHULUAN', 'color': 'red'},
            {'text': 'BAB II TINJAUAN PUSTAKA', 'color': 'red'},
            {'text': 'BAB III METODE PENELITIAN', 'color': 'red'},
            {'text': 'ABSTRAK', 'color': 'red'},
            {'text': 'DAFTAR PUSTAKA', 'color': 'red'},
            {'text': 'KATA PENGANTAR', 'color': 'red'},
        ]

        for segment in test_cases:
            result = self.analyzer.analyze_segment(segment)
            assert result.content_type == ContentType.STANDARD_HEADER, \
                f"Failed for: {segment['text']}"
            assert result.should_skip == True, \
                f"Should skip header: {segment['text']}"
            assert result.flag_priority == FlagPriority.SKIP

    def test_citation_detection(self):
        """Test that proper citations are detected and handled correctly"""
        test_cases = [
            'Menurut Smith (2020), penelitian menunjukkan bahwa...',
            'Hasil penelitian (Johnson et al., 2019) menunjukkan...',
            '"This is a quote" (Author, 2020)',
            'dikutip dari Brown (2018), data menunjukkan...',
            'Penelitian [1] menunjukkan bahwa...',
        ]

        for text in test_cases:
            segment = {'text': text, 'color': 'blue', 'length': len(text)}
            result = self.analyzer.analyze_segment(segment)
            assert result.content_type == ContentType.CITATION, \
                f"Should detect citation: {text[:50]}"
            assert result.should_skip == True, \
                f"Should skip cited text: {text[:50]}"

    def test_common_phrase_detection(self):
        """Test detection of common academic phrases"""
        test_cases = [
            'Penelitian ini bertujuan untuk...',
            'Tujuan penelitian ini adalah...',
            'Berdasarkan hasil penelitian menunjukkan bahwa...',
            'Teknik pengumpulan data menggunakan kuesioner',
            'Metode yang digunakan dalam penelitian ini',
        ]

        for text in test_cases:
            segment = {'text': text, 'color': 'green', 'length': len(text)}
            result = self.analyzer.analyze_segment(segment)
            # Should be either common_phrase or methodology
            assert result.should_skip == True, \
                f"Should skip common phrase: {text}"
            assert result.flag_priority in [FlagPriority.SKIP, FlagPriority.LOW]

    def test_methodology_detection(self):
        """Test detection of standard methodology descriptions"""
        test_cases = [
            'Uji validitas dan reliabilitas dilakukan dengan...',
            'Analisis regresi linear berganda digunakan untuk...',
            'Teknik sampling menggunakan purposive sampling',
            'Pengumpulan data menggunakan wawancara dan observasi',
            'Skala Likert 5 poin digunakan untuk mengukur...',
        ]

        for text in test_cases:
            segment = {'text': text, 'color': 'yellow', 'length': len(text)}
            result = self.analyzer.analyze_segment(segment)
            assert result.should_skip == True, \
                f"Should skip methodology: {text}"

    def test_regular_content_high_priority(self):
        """Test that actual plagiarized content is flagged"""
        segment = {
            'text': 'This is potentially plagiarized content from another source without citation',
            'color': 'red',
            'length': 77,
            'color_confidence': 0.85,
            'color_distance': 40.0
        }

        result = self.analyzer.analyze_segment(segment)
        assert result.content_type == ContentType.REGULAR_CONTENT
        assert result.should_skip == False, "Should NOT skip potential plagiarism"
        assert result.flag_priority == FlagPriority.CRITICAL
        assert len(result.recommended_techniques) > 0

    def test_short_segment_filtering(self):
        """Test that very short segments are skipped as noise"""
        segment = {
            'text': 'dan',
            'color': 'red',
            'length': 3,
            'color_confidence': 0.80
        }

        result = self.analyzer.analyze_segment(segment)
        assert result.should_skip == True, "Should skip very short segments"

    def test_low_confidence_filtering(self):
        """Test that low confidence detections are handled carefully"""
        segment = {
            'text': 'Some text that might be highlighted',
            'color': 'yellow',
            'length': 36,
            'color_confidence': 0.25,
            'color_distance': 90.0
        }

        result = self.analyzer.analyze_segment(segment)
        assert result.should_skip == True, "Should skip low confidence detections"

    def test_quoted_text_with_citation(self):
        """Test quoted text with proper citation"""
        segment = {
            'text': '"This is a direct quote from the source" (Smith, 2020)',
            'color': 'blue',
            'length': 55
        }

        result = self.analyzer.analyze_segment(segment)
        assert result.should_skip == True, "Should skip properly cited quotes"
        # Can be either QUOTE or CITATION - both are fine
        assert result.content_type in [ContentType.QUOTE, ContentType.CITATION]

    def test_quoted_text_without_citation(self):
        """Test quoted text WITHOUT citation - should be flagged"""
        segment = {
            'text': '"This is a direct quote without any citation at all"',
            'color': 'red',
            'length': 54,
            'color_confidence': 0.85
        }

        result = self.analyzer.analyze_segment(segment)
        assert result.should_skip == False, "Should NOT skip uncited quotes"
        assert result.flag_priority == FlagPriority.HIGH

    def test_batch_analysis(self):
        """Test batch processing of multiple segments"""
        segments = [
            {'text': 'BAB I', 'color': 'red', 'length': 5},
            {'text': 'Menurut (Author, 2020), ...', 'color': 'blue', 'length': 27},
            {'text': 'Actual plagiarized content here', 'color': 'red', 'length': 31,
             'color_confidence': 0.80, 'color_distance': 45.0},
            {'text': 'PENDAHULUAN', 'color': 'red', 'length': 11},
        ]

        results = self.analyzer.batch_analyze(segments)

        assert len(results) == 4
        assert results[0].should_skip == True  # Header
        assert results[1].should_skip == True  # Citation
        assert results[2].should_skip == False  # Plagiarism
        assert results[3].should_skip == True  # Header

    def test_filter_segments_smart(self):
        """Test the filter_segments_smart helper function"""
        segments = [
            {'text': 'BAB I PENDAHULUAN', 'color': 'red', 'length': 17},
            {'text': 'This needs modification', 'color': 'red', 'length': 23,
             'color_confidence': 0.85, 'color_distance': 40.0},
            {'text': 'ABSTRAK', 'color': 'red', 'length': 7},
        ]

        to_modify, to_skip = filter_segments_smart(segments)

        assert len(to_skip) == 2  # Both headers
        assert len(to_modify) == 1  # Only the content
        assert to_modify[0]['text'] == 'This needs modification'

    def test_statistics_generation(self):
        """Test statistics generation from results"""
        segments = [
            {'text': 'BAB I', 'color': 'red', 'length': 5},
            {'text': 'Citation (2020)', 'color': 'blue', 'length': 15},
            {'text': 'Content 1', 'color': 'red', 'length': 9,
             'color_confidence': 0.80, 'color_distance': 40.0},
            {'text': 'Content 2', 'color': 'green', 'length': 9,
             'color_confidence': 0.80, 'color_distance': 40.0},
        ]

        results = self.analyzer.batch_analyze(segments)
        stats = self.analyzer.get_statistics(results)

        assert stats['total_segments'] == 4
        assert stats['should_skip'] >= 2  # At least headers
        assert 'by_content_type' in stats
        assert 'by_priority' in stats
        assert 0 <= stats['avg_confidence'] <= 1.0

    def test_color_priority_mapping(self):
        """Test that different colors get appropriate priorities"""
        # High priority colors (critical plagiarism indicators)
        high_priority_segment = {
            'text': 'Some potentially plagiarized content',
            'color': 'red',
            'length': 36,
            'color_confidence': 0.85,
            'color_distance': 40.0
        }
        result = self.analyzer.analyze_segment(high_priority_segment)
        assert result.flag_priority == FlagPriority.CRITICAL

        # Medium priority colors
        medium_priority_segment = {
            'text': 'Some potentially plagiarized content',
            'color': 'orange',
            'length': 36,
            'color_confidence': 0.85,
            'color_distance': 40.0
        }
        result = self.analyzer.analyze_segment(medium_priority_segment)
        assert result.flag_priority == FlagPriority.MEDIUM

    def test_technique_recommendations(self):
        """Test that appropriate techniques are recommended based on context"""
        # High priority should get aggressive techniques
        high_seg = {
            'text': 'Long plagiarized content that needs aggressive modification techniques',
            'color': 'red',
            'length': 70,
            'color_confidence': 0.90,
            'color_distance': 35.0
        }
        result = self.analyzer.analyze_segment(high_seg)
        assert 'unicode_substitution' in result.recommended_techniques
        assert 'zero_width' in result.recommended_techniques

        # Short content shouldn't get paraphrase
        short_seg = {
            'text': 'Short text here',
            'color': 'blue',
            'length': 15,
            'color_confidence': 0.85,
            'color_distance': 40.0
        }
        result = self.analyzer.analyze_segment(short_seg)
        assert 'paraphrase' not in result.recommended_techniques


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])
