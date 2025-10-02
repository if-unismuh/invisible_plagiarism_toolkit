# tools/detection_tester.py
"""
Detection Tester Tool
Tests the effectiveness of invisible manipulation against various detection methods
Simulates common plagiarism detection algorithms

Author: DevNoLife
Version: 1.0
"""

import os
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
import docx
from collections import Counter
import hashlib

class DetectionTester:
    def __init__(self):
        print("🔍 Detection Tester Tool")
        print("🎯 Simulating plagiarism detection algorithms")
        
        self.detection_methods = {
            'exact_match': self.test_exact_match,
            'fingerprinting': self.test_fingerprinting,
            'unicode_analysis': self.test_unicode_analysis,
            'invisible_char_detection': self.test_invisible_chars,
            'pattern_analysis': self.test_pattern_analysis,
            'statistical_analysis': self.test_statistical_analysis
        }
        
        print(f"✅ {len(self.detection_methods)} detection methods loaded")
    
    def test_documents(self, original_path, modified_path):
        """Test both documents against all detection methods"""
        print("🧪 COMPREHENSIVE DETECTION TESTING")
        print("=" * 60)
        
        # Load documents
        original_text = self.extract_text_from_docx(original_path)
        modified_text = self.extract_text_from_docx(modified_path)
        
        if not original_text or not modified_text:
            print("❌ Could not extract text from documents")
            return None
        
        results = {
            'test_info': {
                'original_file': str(original_path),
                'modified_file': str(modified_path),
                'test_timestamp': datetime.now().isoformat(),
                'original_length': len(original_text),
                'modified_length': len(modified_text)
            },
            'detection_results': {},
            'overall_scores': {},
            'risk_assessment': {}
        }
        
        print(f"📄 Original text: {len(original_text)} characters")
        print(f"📄 Modified text: {len(modified_text)} characters")
        print(f"📊 Length difference: {abs(len(modified_text) - len(original_text))} chars")
        
        # Run all detection tests
        for method_name, method_func in self.detection_methods.items():
            print(f"\n🔍 Testing: {method_name.replace('_', ' ').title()}")
            
            try:
                detection_result = method_func(original_text, modified_text)
                results['detection_results'][method_name] = detection_result
                
                # Print summary
                if 'detection_probability' in detection_result:
                    prob = detection_result['detection_probability']
                    status = "🚨 HIGH" if prob > 0.7 else "⚠️ MEDIUM" if prob > 0.3 else "✅ LOW"
                    print(f"   Detection probability: {prob:.1%} {status}")
                
            except Exception as e:
                print(f"   ❌ Test failed: {e}")
                results['detection_results'][method_name] = {'error': str(e)}
        
        # Calculate overall scores
        results['overall_scores'] = self.calculate_overall_scores(results['detection_results'])
        results['risk_assessment'] = self.assess_risk_level(results['overall_scores'])
        
        # Print summary
        self.print_detection_summary(results)
        
        # Save results
        self.save_detection_results(results)
        
        return results
    
    def extract_text_from_docx(self, file_path):
        """Extract text content from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            print(f"❌ Could not read {file_path}: {e}")
            return None
    
    def test_exact_match(self, original, modified):
        """Test exact string matching (most basic detection)"""
        # Split into paragraphs
        orig_paragraphs = [p.strip() for p in original.split('\n') if p.strip()]
        mod_paragraphs = [p.strip() for p in modified.split('\n') if p.strip()]
        
        exact_matches = 0
        total_paragraphs = len(orig_paragraphs)
        
        for orig_para in orig_paragraphs:
            if orig_para in mod_paragraphs:
                exact_matches += 1
        
        detection_probability = exact_matches / max(1, total_paragraphs)
        
        return {
            'method': 'exact_match',
            'exact_matches': exact_matches,
            'total_paragraphs': total_paragraphs,
            'detection_probability': detection_probability,
            'status': 'detected' if detection_probability > 0.1 else 'not_detected'
        }
    
    def test_fingerprinting(self, original, modified):
        """Test fingerprinting detection (hash-based)"""
        # Create fingerprints using n-grams
        orig_fingerprints = self.create_text_fingerprints(original)
        mod_fingerprints = self.create_text_fingerprints(modified)
        
        # Calculate overlap
        overlap = len(orig_fingerprints & mod_fingerprints)
        total_fingerprints = len(orig_fingerprints)
        
        detection_probability = overlap / max(1, total_fingerprints)
        
        return {
            'method': 'fingerprinting',
            'original_fingerprints': len(orig_fingerprints),
            'modified_fingerprints': len(mod_fingerprints),
            'overlapping_fingerprints': overlap,
            'detection_probability': detection_probability,
            'status': 'detected' if detection_probability > 0.3 else 'not_detected'
        }
    
    def create_text_fingerprints(self, text, n=5):
        """Create text fingerprints using n-grams"""
        # Clean text (remove punctuation, normalize)
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()
        
        fingerprints = set()
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            # Create hash fingerprint
            fingerprint = hashlib.md5(ngram.encode()).hexdigest()[:8]
            fingerprints.add(fingerprint)
        
        return fingerprints
    
    def test_unicode_analysis(self, original, modified):
        """Test Unicode character analysis detection"""
        orig_scripts = self.analyze_script_usage(original)
        mod_scripts = self.analyze_script_usage(modified)
        
        # Check for suspicious script mixing
        orig_latin_ratio = orig_scripts.get('LATIN', 0) / max(1, sum(orig_scripts.values()))
        mod_latin_ratio = mod_scripts.get('LATIN', 0) / max(1, sum(mod_scripts.values()))
        
        # Detection flags
        flags = []
        detection_score = 0
        
        # Check for Cyrillic characters in text that should be Latin
        if 'CYRILLIC' in mod_scripts and 'CYRILLIC' not in orig_scripts:
            flags.append('cyrillic_substitution_detected')
            detection_score += 0.4
        
        # Check for mixed scripts
        if len(mod_scripts) > len(orig_scripts):
            flags.append('additional_scripts_detected')
            detection_score += 0.3
        
        # Check for Latin ratio decrease
        if mod_latin_ratio < orig_latin_ratio - 0.05:
            flags.append('latin_ratio_decrease')
            detection_score += 0.2
        
        return {
            'method': 'unicode_analysis',
            'original_scripts': orig_scripts,
            'modified_scripts': mod_scripts,
            'detection_flags': flags,
            'detection_probability': min(detection_score, 1.0),
            'status': 'detected' if detection_score > 0.2 else 'not_detected'
        }
    
    def analyze_script_usage(self, text):
        """Analyze Unicode script usage in text"""
        script_counts = Counter()
        
        for char in text:
            if char.isalpha():
                try:
                    script = unicodedata.name(char).split()[0]
                    script_counts[script] += 1
                except:
                    script_counts['UNKNOWN'] += 1
        
        return dict(script_counts)
    
    def test_invisible_chars(self, original, modified):
        """Test for invisible character detection"""
        invisible_chars = ['\u200B', '\u200C', '\u200D', '\uFEFF', '\u2009', '\u200A']
        
        orig_invisible = sum(original.count(char) for char in invisible_chars)
        mod_invisible = sum(modified.count(char) for char in invisible_chars)
        
        invisible_increase = mod_invisible - orig_invisible
        
        # Detection probability based on invisible character density
        text_length = len(modified)
        invisible_density = mod_invisible / max(1, text_length)
        
        detection_probability = min(invisible_density * 100, 1.0)  # Penalize high density
        
        return {
            'method': 'invisible_char_detection',
            'original_invisible': orig_invisible,
            'modified_invisible': mod_invisible,
            'invisible_increase': invisible_increase,
            'invisible_density': invisible_density,
            'detection_probability': detection_probability,
            'status': 'detected' if detection_probability > 0.1 else 'not_detected'
        }
    
    def test_pattern_analysis(self, original, modified):
        """Test pattern-based detection"""
        # Analyze sentence structure patterns
        orig_patterns = self.extract_sentence_patterns(original)
        mod_patterns = self.extract_sentence_patterns(modified)
        
        # Calculate pattern similarity
        pattern_overlap = len(orig_patterns & mod_patterns)
        total_patterns = len(orig_patterns)
        
        pattern_similarity = pattern_overlap / max(1, total_patterns)
        
        # Check for suspicious patterns
        flags = []
        detection_score = pattern_similarity
        
        # Check for length preservation (suspicious)
        orig_lengths = [len(s.split()) for s in original.split('.') if s.strip()]
        mod_lengths = [len(s.split()) for s in modified.split('.') if s.strip()]
        
        if len(orig_lengths) == len(mod_lengths):
            avg_orig_len = sum(orig_lengths) / len(orig_lengths)
            avg_mod_len = sum(mod_lengths) / len(mod_lengths)
            
            if abs(avg_orig_len - avg_mod_len) < 0.5:  # Very similar average length
                flags.append('suspicious_length_preservation')
                detection_score += 0.2
        
        return {
            'method': 'pattern_analysis',
            'original_patterns': len(orig_patterns),
            'modified_patterns': len(mod_patterns),
            'pattern_overlap': pattern_overlap,
            'pattern_similarity': pattern_similarity,
            'detection_flags': flags,
            'detection_probability': min(detection_score, 1.0),
            'status': 'detected' if detection_score > 0.6 else 'not_detected'
        }
    
    def extract_sentence_patterns(self, text):
        """Extract sentence structure patterns"""
        sentences = re.split(r'[.!?]+', text)
        patterns = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence.split()) >= 5:  # Only analyze substantial sentences
                # Create pattern based on word lengths and structure
                words = sentence.split()
                pattern = []
                for word in words[:10]:  # First 10 words
                    if word.isalpha():
                        pattern.append(len(word))
                    else:
                        pattern.append(0)  # Non-alphabetic
                
                patterns.add(tuple(pattern))
        
        return patterns
    
    def test_statistical_analysis(self, original, modified):
        """Test statistical similarity detection"""
        # Character frequency analysis
        orig_char_freq = self.get_character_frequency(original)
        mod_char_freq = self.get_character_frequency(modified)
        
        # Calculate statistical similarity
        similarity_score = self.calculate_frequency_similarity(orig_char_freq, mod_char_freq)
        
        # Word frequency analysis
        orig_word_freq = self.get_word_frequency(original)
        mod_word_freq = self.get_word_frequency(modified)
        
        word_similarity = self.calculate_frequency_similarity(orig_word_freq, mod_word_freq)
        
        # Combined detection probability
        detection_probability = (similarity_score + word_similarity) / 2
        
        return {
            'method': 'statistical_analysis',
            'character_similarity': similarity_score,
            'word_similarity': word_similarity,
            'detection_probability': detection_probability,
            'status': 'detected' if detection_probability > 0.8 else 'not_detected'
        }
    
    def get_character_frequency(self, text):
        """Calculate character frequency distribution"""
        clean_text = ''.join(c.lower() for c in text if c.isalpha())
        total_chars = len(clean_text)
        
        if total_chars == 0:
            return {}
        
        char_count = Counter(clean_text)
        return {char: count/total_chars for char, count in char_count.items()}
    
    def get_word_frequency(self, text):
        """Calculate word frequency distribution"""
        words = re.findall(r'\b\w+\b', text.lower())
        total_words = len(words)
        
        if total_words == 0:
            return {}
        
        word_count = Counter(words)
        return {word: count/total_words for word, count in word_count.items()}
    
    def calculate_frequency_similarity(self, freq1, freq2):
        """Calculate similarity between frequency distributions"""
        all_keys = set(freq1.keys()) | set(freq2.keys())
        
        if not all_keys:
            return 0.0
        
        similarity = 0.0
        for key in all_keys:
            f1 = freq1.get(key, 0)
            f2 = freq2.get(key, 0)
            similarity += min(f1, f2)  # Overlap
        
        return similarity
    
    def calculate_overall_scores(self, detection_results):
        """Calculate overall detection scores"""
        scores = {
            'average_detection_probability': 0.0,
            'methods_detected': 0,
            'total_methods': len(detection_results),
            'high_risk_methods': 0,
            'detection_rate': 0.0
        }
        
        probabilities = []
        detected_count = 0
        high_risk_count = 0
        
        for method_name, result in detection_results.items():
            if 'error' in result:
                continue
            
            prob = result.get('detection_probability', 0)
            probabilities.append(prob)
            
            if result.get('status') == 'detected':
                detected_count += 1
            
            if prob > 0.7:
                high_risk_count += 1
        
        if probabilities:
            scores['average_detection_probability'] = sum(probabilities) / len(probabilities)
            scores['methods_detected'] = detected_count
            scores['detection_rate'] = detected_count / len(probabilities)
            scores['high_risk_methods'] = high_risk_count
        
        return scores
    
    def assess_risk_level(self, overall_scores):
        """Assess overall risk level"""
        avg_prob = overall_scores['average_detection_probability']
        detection_rate = overall_scores['detection_rate']
        high_risk_methods = overall_scores['high_risk_methods']
        
        risk_score = (avg_prob * 0.4) + (detection_rate * 0.4) + (high_risk_methods / max(1, overall_scores['total_methods']) * 0.2)
        
        if risk_score > 0.7:
            risk_level = 'HIGH'
            recommendation = "⚠️ High detection risk - consider more aggressive steganography"
        elif risk_score > 0.4:
            risk_level = 'MEDIUM'
            recommendation = "💡 Medium detection risk - current approach is reasonable"
        else:
            risk_level = 'LOW'
            recommendation = "✅ Low detection risk - steganography is effective"
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'confidence': min(0.95, 0.5 + (len(overall_scores) * 0.1))
        }
    
    def print_detection_summary(self, results):
        """Print comprehensive detection summary"""
        print("\n" + "=" * 60)
        print("📊 DETECTION TEST SUMMARY")
        print("=" * 60)
        
        overall = results['overall_scores']
        risk = results['risk_assessment']
        
        print(f"📄 Documents tested: {Path(results['test_info']['original_file']).name}")
        print(f"🧪 Detection methods: {overall['total_methods']}")
        print(f"⚠️ Methods detected: {overall['methods_detected']}")
        print(f"📊 Detection rate: {overall['detection_rate']:.1%}")
        print(f"🎯 Average probability: {overall['average_detection_probability']:.1%}")
        
        print(f"\n🚨 RISK ASSESSMENT:")
        print(f"   Risk level: {risk['risk_level']}")
        print(f"   Risk score: {risk['risk_score']:.2f}")
        print(f"   Confidence: {risk['confidence']:.1%}")
        print(f"   💡 {risk['recommendation']}")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for method, result in results['detection_results'].items():
            if 'error' in result:
                continue
            
            prob = result.get('detection_probability', 0)
            status = result.get('status', 'unknown')
            status_icon = "🚨" if status == 'detected' else "✅"
            
            print(f"   {status_icon} {method.replace('_', ' ').title()}: {prob:.1%}")
        
        print("=" * 60)
    
    def save_detection_results(self, results):
        """Save detection results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output/analysis_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = output_dir / f"detection_test_report_{timestamp}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"💾 Detection test report saved: {report_file}")
            return report_file
        
        except Exception as e:
            print(f"⚠️ Could not save report: {e}")
            return None


def main():
    """Main function for testing detection"""
    print("🔍 DETECTION TESTER TOOL")
    print("=" * 50)
    
    # Initialize tester
    tester = DetectionTester()
    
    # Look for original and processed documents
    backup_dir = Path("backup")
    output_dir = Path("output/processed_documents")
    
    if not backup_dir.exists() or not output_dir.exists():
        print("❌ No backup or output directories found")
        print("💡 Process a document first using: python main.py")
        return
    
    # Find matching pairs
    backup_files = list(backup_dir.glob("*.docx"))
    output_files = list(output_dir.glob("*.docx"))
    
    if not backup_files or not output_files:
        print("❌ No documents found for comparison")
        print("💡 Process a document first using: python main.py")
        return
    
    print(f"📁 Found {len(backup_files)} backup files")
    print(f"📁 Found {len(output_files)} processed files")
    
    # Test the most recent pair
    latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
    latest_output = max(output_files, key=lambda x: x.stat().st_mtime)
    
    print(f"\n🎯 Testing latest pair:")
    print(f"   📄 Original: {latest_backup.name}")
    print(f"   📄 Modified: {latest_output.name}")
    
    # Run comprehensive test
    results = tester.test_documents(latest_backup, latest_output)
    
    if results:
        print(f"\n✅ Detection testing completed!")
        print(f"📋 Check the analysis report for detailed results")
    else:
        print("❌ Testing failed")


if __name__ == "__main__":
    main()
