# tests/test_advanced.py
"""
Advanced test suite for Invisible Plagiarism Toolkit
Comprehensive testing including edge cases and performance
"""

import pytest
import tempfile
import os
from pathlib import Path
import docx
from typing import Dict, Any

# Import project modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from core.invisible_manipulator import InvisibleManipulator
from core.unicode_steganography import UnicodeSteg

class TestFixtures:
    """Test data and fixtures"""
    
    @staticmethod
    def create_test_document(content: str, filename: str = "test.docx") -> str:
        """Create a test DOCX document"""
        doc = docx.Document()
        for line in content.split('\n'):
            doc.add_paragraph(line)
        
        temp_path = Path(tempfile.gettempdir()) / filename
        doc.save(temp_path)
        return str(temp_path)
    
    @staticmethod
    def get_academic_content() -> str:
        """Sample academic content in Indonesian"""
        return """BAB I
PENDAHULUAN

A. Latar Belakang
Penelitian ini membahas tentang metode analisis data yang digunakan dalam penelitian akademik. 
Berbagai faktor mempengaruhi hasil penelitian, termasuk variabel independen dan dependen.

B. Rumusan Masalah
Bagaimana pengaruh metode penelitian terhadap kualitas hasil analisis?

BAB II
TINJAUAN PUSTAKA

Teori yang digunakan dalam penelitian ini mencakup konsep dasar penelitian kuantitatif.
Hipotesis penelitian didasarkan pada studi literatur yang komprehensif.

BAB III
METODE PENELITIAN

Data dikumpulkan menggunakan teknik sampling purposive.
Analisis data dilakukan dengan menggunakan software statistik SPSS."""

class TestConfigValidation:
    """Test configuration validation and schema"""
    
    def test_valid_config_loading(self):
        """Test loading valid configuration"""
        # This should not raise an exception
        config = validate_config_file('config.json')
        assert isinstance(config, ProcessingConfig)
        assert config.zero_width_chars.enabled is not None
        assert config.unicode_substitution.enabled is not None
    
    def test_invalid_insertion_rate(self):
        """Test validation of invalid insertion rates"""
        with pytest.raises(ValueError):
            from schemas import ZeroWidthConfig
            ZeroWidthConfig(insertion_rate=0.6)  # Too high
    
    def test_invalid_substitution_rate(self):
        """Test validation of invalid substitution rates"""
        with pytest.raises(ValueError):
            from schemas import UnicodeSubstitutionConfig
            UnicodeSubstitutionConfig(substitution_rate=0.5)  # Too high

class TestUnicodeSubstitution:
    """Test Unicode substitution functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.steg = UnicodeSteg()
    
    def test_basic_substitution(self):
        """Test basic character substitution"""
        text = "BAB I PENDAHULUAN"
        result = self.steg.apply_substitution(text, rate=0.1)
        
        # Should contain some substitutions
        assert result != text
        assert 'ВАВ' in result or 'РENDAHULUAN' in result
    
    def test_substitution_reversibility(self):
        """Test that substitutions are visually identical"""
        original = "PENELITIAN AKADEMIK"
        substituted = self.steg.apply_substitution(original, rate=0.2)
        
        # Visual similarity check (simplified)
        # In practice, would use more sophisticated comparison
        assert len(substituted) == len(original)
    
    def test_rate_limiting(self):
        """Test that substitution rate is respected"""
        text = "a" * 1000  # 1000 'a' characters
        result = self.steg.apply_substitution(text, rate=0.05)
        
        # Count substitutions (approximate)
        substitutions = sum(1 for c in result if ord(c) > 127)
        expected_max = len(text) * 0.1  # Allow some variance
        assert substitutions <= expected_max

class TestInvisibleCharacters:
    """Test invisible character insertion"""
    
    def test_zero_width_insertion(self):
        """Test zero-width character insertion"""
        manipulator = InvisibleManipulator(verbose=False)
        text = "Penelitian ini adalah contoh."
        
        result = manipulator._insert_invisible_chars(text, rate=0.1)
        
        # Should be longer due to invisible chars
        assert len(result) >= len(text)
        
        # Should contain zero-width chars
        zw_chars = ['\u200B', '\u200C', '\u200D', '\uFEFF']
        assert any(char in result for char in zw_chars)
    
    def test_invisible_char_distribution(self):
        """Test that invisible chars are distributed properly"""
        manipulator = InvisibleManipulator(verbose=False)
        text = "Kata pertama. Kata kedua. Kata ketiga."
        
        result = manipulator._insert_invisible_chars(text, rate=0.2)
        
        # Check distribution after punctuation
        assert result.count('\u200B') > 0 or result.count('\u200C') > 0

class TestDocumentProcessing:
    """Test end-to-end document processing"""
    
    def setup_method(self):
        """Setup for each test"""
        self.manipulator = InvisibleManipulator(verbose=False)
        self.test_content = TestFixtures.get_academic_content()
    
    def test_full_document_processing(self):
        """Test complete document processing pipeline"""
        # Create test document
        doc_path = TestFixtures.create_test_document(self.test_content)
        
        try:
            # Process document
            result = self.manipulator.apply_invisible_manipulation(doc_path)
            
            # Verify result structure
            assert 'output_file' in result
            assert 'stats' in result
            assert os.path.exists(result['output_file'])
            
            # Verify processing stats
            stats = result['stats']
            assert stats['processing_time'] >= 0
            assert stats['total_documents'] == 1
            
        finally:
            # Cleanup
            if os.path.exists(doc_path):
                os.remove(doc_path)
            if 'output_file' in result and os.path.exists(result['output_file']):
                os.remove(result['output_file'])
    
    def test_header_detection(self):
        """Test academic header detection"""
        doc_path = TestFixtures.create_test_document(self.test_content)
        
        try:
            analysis = self.manipulator.analyze_document_structure(doc_path)
            
            # Should detect academic headers
            headers = [h['text'] for h in analysis['headers']]
            assert any('BAB I' in h for h in headers)
            assert any('PENDAHULUAN' in h for h in headers)
            assert any('METODE' in h for h in headers)
            
        finally:
            if os.path.exists(doc_path):
                os.remove(doc_path)
    
    def test_backup_creation(self):
        """Test that original files are backed up"""
        doc_path = TestFixtures.create_test_document(self.test_content)
        
        try:
            result = self.manipulator.apply_invisible_manipulation(doc_path)
            
            # Should create backup
            backup_dir = Path('backup')
            backup_files = list(backup_dir.glob('*backup*'))
            assert len(backup_files) > 0
            
        finally:
            if os.path.exists(doc_path):
                os.remove(doc_path)

class TestAdvancedAnalyzer:
    """Test advanced risk analysis functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.analyzer = AdvancedAnalyzer()
        self.test_content = TestFixtures.get_academic_content()
    
    def test_risk_analysis(self):
        """Test comprehensive risk analysis"""
        # Create original and modified documents
        original_path = TestFixtures.create_test_document(self.test_content, "original.docx")
        
        # Create slightly modified version
        modified_content = self.test_content.replace("BAB", "ВАВ")  # Cyrillic substitution
        modified_path = TestFixtures.create_test_document(modified_content, "modified.docx")
        
        try:
            analysis = self.analyzer.analyze_document_risk(original_path, modified_path)
            
            # Verify analysis structure
            assert hasattr(analysis, 'overall_risk')
            assert hasattr(analysis, 'risk_level')
            assert hasattr(analysis, 'invisibility_score')
            assert isinstance(analysis.recommendations, list)
            
            # Risk should be detectable but not critical
            assert 0 <= analysis.overall_risk <= 1
            assert analysis.invisibility_score > 0
            
        finally:
            # Cleanup
            for path in [original_path, modified_path]:
                if os.path.exists(path):
                    os.remove(path)

class TestPerformance:
    """Performance and stress tests"""
    
    def test_large_document_processing(self):
        """Test processing of large documents"""
        # Create large document (1000 paragraphs)
        large_content = '\n'.join([f"Paragraph {i} dengan konten penelitian." for i in range(1000)])
        doc_path = TestFixtures.create_test_document(large_content, "large.docx")
        
        try:
            manipulator = InvisibleManipulator(verbose=False)
            result = manipulator.apply_invisible_manipulation(doc_path)
            
            # Should complete in reasonable time (< 30 seconds)
            assert result['stats']['processing_time'] < 30
            
        finally:
            if os.path.exists(doc_path):
                os.remove(doc_path)
    
    def test_memory_usage(self):
        """Test memory usage with multiple documents"""
        manipulator = InvisibleManipulator(verbose=False)
        
        # Process multiple documents
        for i in range(10):
            content = f"Document {i} content for testing memory usage."
            doc_path = TestFixtures.create_test_document(content, f"mem_test_{i}.docx")
            
            try:
                result = manipulator.apply_invisible_manipulation(doc_path)
                assert result['output_file']
                
            finally:
                if os.path.exists(doc_path):
                    os.remove(doc_path)
                if 'output_file' in result and os.path.exists(result['output_file']):
                    os.remove(result['output_file'])

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_document(self):
        """Test processing empty document"""
        doc_path = TestFixtures.create_test_document("", "empty.docx")
        
        try:
            manipulator = InvisibleManipulator(verbose=False)
            result = manipulator.apply_invisible_manipulation(doc_path)
            
            # Should handle gracefully
            assert result is not None
            
        finally:
            if os.path.exists(doc_path):
                os.remove(doc_path)
    
    def test_special_characters(self):
        """Test handling of special characters and symbols"""
        special_content = "Tëst ñoñ-ASCÏÏ châractërs: 测试中文 🔍 ∞ ≠ ≈"
        doc_path = TestFixtures.create_test_document(special_content, "special.docx")
        
        try:
            manipulator = InvisibleManipulator(verbose=False)
            result = manipulator.apply_invisible_manipulation(doc_path)
            
            # Should not crash
            assert result is not None
            
        finally:
            if os.path.exists(doc_path):
                os.remove(doc_path)
    
    def test_corrupted_config(self):
        """Test handling of corrupted configuration"""
        # This would need actual corrupted config file
        # For now, test with missing config
        manipulator = InvisibleManipulator(config_file='nonexistent.json', verbose=False)
        
        # Should fallback to defaults
        assert manipulator.config is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
