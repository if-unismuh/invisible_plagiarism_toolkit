# unicode_steganography.py
"""
Unicode Steganography Module
Advanced Unicode character substitution and steganographic techniques
Focus on visually identical but technically different characters

Author: DevNoLife
Version: 1.0
"""

import json
import random
import unicodedata
from typing import Dict, List, Tuple, Optional

class UnicodeSteg:
    def __init__(self):
        print("🔤 Initializing Unicode Steganography Module...")
        
        # Define comprehensive character mappings
        self.mappings = self.create_comprehensive_mappings()
        
        # Statistical tracking
        self.stats = {
            'substitutions_made': 0,
            'characters_processed': 0,
            'detection_risk_score': 0
        }
        
        print("✅ Unicode steganography ready!")
        print(f"📊 Available mappings: {len(self.mappings)} character sets")
    
    def create_comprehensive_mappings(self):
        """Create comprehensive character mapping database"""
        return {
            # Latin to Cyrillic (most common and effective)
            'latin_cyrillic': {
                # Uppercase
                'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
                'I': 'І', 'J': 'Ј', 'K': 'К', 'M': 'М', 'N': 'Н',
                'O': 'О', 'P': 'Р', 'S': 'Ѕ', 'T': 'Т', 'X': 'Х',
                'Y': 'Ү', 'Z': 'Ζ',
                # Lowercase  
                'a': 'а', 'c': 'с', 'e': 'е', 'i': 'і', 'j': 'ј',
                'o': 'о', 'p': 'р', 's': 'ѕ', 'x': 'х', 'y': 'у'
            },
            
            # Latin to Greek (secondary option)
            'latin_greek': {
                'A': 'Α', 'B': 'Β', 'E': 'Ε', 'H': 'Η', 'I': 'Ι',
                'K': 'Κ', 'M': 'Μ', 'N': 'Ν', 'O': 'Ο', 'P': 'Ρ',
                'T': 'Τ', 'X': 'Χ', 'Y': 'Υ', 'Z': 'Ζ',
                'a': 'α', 'o': 'ο', 'p': 'ρ', 'x': 'χ', 'y': 'υ'
            },
            
            # Mathematical symbols (for special cases)
            'math_symbols': {
                'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄',
                'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞'
            },
            
            # Special Indonesian academic words
            'indonesian_academic': {
                'BAB': 'ВАВ',           # Cyrillic B-A-B
                'PENDAHULUAN': 'РENDAHULUAN',  # Cyrillic P
                'METODE': 'МETODE',     # Cyrillic M
                'PENELITIAN': 'РENELITIAN',    # Cyrillic P
                'HASIL': 'НASIL',       # Cyrillic H
                'PEMBAHASAN': 'РEMBAHASAN',    # Cyrillic P
                'KESIMPULAN': 'КESIMPULAN',    # Cyrillic K
                'DAFTAR': 'DАFTAR',     # Cyrillic A
                'PUSTAKA': 'РUSTAKA',   # Cyrillic P
                'ANALISIS': 'АNALISIS', # Cyrillic A
                'DATA': 'DАTA',         # Cyrillic A
                'TEORI': 'ТЕORI',       # Cyrillic T-E-O
                'KONSEP': 'КONSEP',     # Cyrillic K
                'FAKTOR': 'FАKTOR',     # Cyrillic A
                'VARIABEL': 'VАRIABEL', # Cyrillic A
                'HIPOTESIS': 'НIPOTESIS'  # Cyrillic H
            },
            
            # Common connecting words
            'connectors': {
                'dan': 'dаn',           # Cyrillic a
                'atau': 'аtau',         # Cyrillic a
                'dengan': 'dengаn',     # Cyrillic a
                'untuk': 'untuk',       # Keep same (low risk)
                'dalam': 'dаlam',       # Cyrillic a
                'pada': 'pаda',         # Cyrillic a
                'dari': 'dаri',         # Cyrillic a
                'yang': 'yаng',         # Cyrillic a
                'ini': 'іni',           # Cyrillic i
                'itu': 'іtu',           # Cyrillic i
                'adalah': 'аdalah',     # Cyrillic a
                'akan': 'аkan',         # Cyrillic a
                'telah': 'telаh',       # Cyrillic a
                'dapat': 'dаpat',       # Cyrillic a
                'juga': 'jugа',         # Cyrillic a
                'hanya': 'hаnya',       # Cyrillic a
                'sangat': 'sаngat',     # Cyrillic a
                'lebih': 'lebіh',       # Cyrillic i
                'sering': 'serіng',     # Cyrillic i
                'baik': 'bаik',         # Cyrillic a
                'besar': 'besаr',       # Cyrillic a
                'penting': 'pentіng'    # Cyrillic i
            }
        }
    
    def analyze_text_for_substitution(self, text: str) -> Dict:
        """Analyze text to determine optimal substitution strategy"""
        analysis = {
            'text_length': len(text),
            'substitutable_chars': 0,
            'risk_level': 'low',
            'recommended_mapping': 'latin_cyrillic',
            'target_words': [],
            'substitution_opportunities': []
        }
        
        # Count substitutable characters
        for mapping_name, mapping in self.mappings.items():
            for char in text:
                if char in mapping:
                    analysis['substitutable_chars'] += 1
        
        # Identify target words (Indonesian academic terms)
        academic_words = self.mappings['indonesian_academic']
        for word in academic_words:
            if word in text.upper():
                analysis['target_words'].append(word)
        
        # Determine risk level based on text type
        if any(word in text.upper() for word in ['BAB', 'PENDAHULUAN', 'METODE']):
            analysis['risk_level'] = 'high'  # Academic paper
            analysis['recommended_mapping'] = 'indonesian_academic'
        elif len(text) < 50:
            analysis['risk_level'] = 'medium'  # Header or title
        
        return analysis
    
    def apply_strategic_substitution(self, text: str, aggressiveness: float = 0.1) -> Tuple[str, Dict]:
        """Apply strategic Unicode substitution with specified aggressiveness"""
        result = text
        substitution_log = {
            'original_text': text,
            'substitutions_made': [],
            'total_changes': 0,
            'aggressiveness_used': aggressiveness
        }
        
        # Analyze text first
        analysis = self.analyze_text_for_substitution(text)
        
        # Choose mapping based on analysis
        if analysis['recommended_mapping'] == 'indonesian_academic':
            # Prioritize academic words
            academic_mapping = self.mappings['indonesian_academic']
            for original, replacement in academic_mapping.items():
                if original in result and random.random() < aggressiveness * 2:
                    result = result.replace(original, replacement)
                    substitution_log['substitutions_made'].append({
                        'original': original,
                        'replacement': replacement,
                        'type': 'academic_word'
                    })
                    substitution_log['total_changes'] += 1
        
        # Apply character-level substitutions
        cyrillic_mapping = self.mappings['latin_cyrillic']
        connector_mapping = self.mappings['connectors']
        
        # Process connectors first (higher priority)
        for original, replacement in connector_mapping.items():
            if original in result and random.random() < aggressiveness:
                # Use word boundary to avoid partial replacements
                import re
                pattern = r'\b' + re.escape(original) + r'\b'
                if re.search(pattern, result, re.IGNORECASE):
                    result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
                    substitution_log['substitutions_made'].append({
                        'original': original,
                        'replacement': replacement,
                        'type': 'connector'
                    })
                    substitution_log['total_changes'] += 1
        
        # Apply individual character substitutions
        if aggressiveness > 0.05:  # Only if moderately aggressive
            new_result = ""
            for char in result:
                if char in cyrillic_mapping and random.random() < aggressiveness * 0.5:
                    replacement = cyrillic_mapping[char]
                    new_result += replacement
                    substitution_log['substitutions_made'].append({
                        'original': char,
                        'replacement': replacement,
                        'type': 'character'
                    })
                    substitution_log['total_changes'] += 1
                else:
                    new_result += char
            result = new_result
        
        return result, substitution_log
    
    def create_invisible_variation(self, text: str, variation_type: str = 'mixed') -> str:
        """Create invisible variations using zero-width characters"""
        invisible_chars = {
            'zwsp': '\u200B',    # Zero Width Space
            'zwnj': '\u200C',    # Zero Width Non-Joiner
            'zwj': '\u200D',     # Zero Width Joiner
            'zwnbsp': '\uFEFF',  # Zero Width No-Break Space
            'vs15': '\uFE0E',    # Variation Selector-15
            'vs16': '\uFE0F'     # Variation Selector-16
        }
        
        if variation_type == 'minimal':
            # Only use zero-width space
            chars_to_use = [invisible_chars['zwsp']]
        elif variation_type == 'aggressive':
            # Use all available invisible characters
            chars_to_use = list(invisible_chars.values())
        else:  # mixed
            # Use most common invisible characters
            chars_to_use = [invisible_chars['zwsp'], invisible_chars['zwnj']]
        
        result = ""
        for i, char in enumerate(text):
            result += char
            
            # Insert invisible characters after spaces and punctuation
            if char in ' .,;:!?()[]{}' and random.random() < 0.1:
                invisible_char = random.choice(chars_to_use)
                result += invisible_char
        
        return result
    
    def detect_unicode_substitutions(self, text: str) -> Dict:
        """Detect potential Unicode substitutions in text"""
        detections = {
            'suspicious_characters': [],
            'mixed_scripts': False,
            'substitution_probability': 0.0,
            'analysis': {}
        }
        
        script_counts = {}
        
        for char in text:
            if char.isalpha():
                script = unicodedata.name(char, 'UNKNOWN').split()[0] if unicodedata.name(char, None) else 'UNKNOWN'
                script_counts[script] = script_counts.get(script, 0) + 1
                
                # Check if character looks suspicious
                if script in ['CYRILLIC', 'GREEK'] and char in 'AEIOUaeiou':
                    detections['suspicious_characters'].append({
                        'character': char,
                        'position': text.index(char),
                        'script': script,
                        'unicode_name': unicodedata.name(char, 'UNKNOWN')
                    })
        
        # Determine if mixed scripts are used
        if len(script_counts) > 1:
            detections['mixed_scripts'] = True
        
        # Calculate substitution probability
        total_chars = sum(script_counts.values())
        if total_chars > 0:
            non_latin_chars = sum(count for script, count in script_counts.items() 
                                if script not in ['LATIN', 'UNKNOWN'])
            detections['substitution_probability'] = non_latin_chars / total_chars
        
        detections['analysis'] = script_counts
        
        return detections
    
    def generate_mapping_file(self, filename: str = 'data/unicode_mappings.json'):
        """Generate comprehensive mapping file"""
        import os
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.mappings, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Unicode mappings saved to {filename}")
        return filename
    
    def test_invisibility(self, original: str, modified: str) -> Dict:
        """Test how invisible the modifications are"""
        test_results = {
            'visual_similarity': 0.0,
            'length_difference': abs(len(modified) - len(original)),
            'character_differences': 0,
            'invisible_char_count': 0,
            'substitution_detection': None
        }
        
        # Count character differences
        for orig_char, mod_char in zip(original, modified):
            if orig_char != mod_char:
                test_results['character_differences'] += 1
        
        # Count invisible characters
        for char in modified:
            if unicodedata.category(char) == 'Cf':  # Format characters (invisible)
                test_results['invisible_char_count'] += 1
        
        # Calculate visual similarity
        visible_orig = ''.join(c for c in original if unicodedata.category(c) != 'Cf')
        visible_mod = ''.join(c for c in modified if unicodedata.category(c) != 'Cf')
        
        if len(visible_orig) == len(visible_mod):
            similar_chars = sum(1 for a, b in zip(visible_orig, visible_mod) if a.lower() == b.lower())
            test_results['visual_similarity'] = similar_chars / len(visible_orig) if visible_orig else 1.0
        
        # Run substitution detection
        test_results['substitution_detection'] = self.detect_unicode_substitutions(modified)
        
        return test_results
    
    def create_steganographic_header(self, header_text: str, stealth_level: str = 'medium') -> Tuple[str, Dict]:
        """Create steganographic version of header with specified stealth level"""
        aggressiveness_map = {
            'low': 0.02,      # Very subtle
            'medium': 0.05,   # Moderate  
            'high': 0.1,      # More obvious but effective
            'maximum': 0.2    # Highly aggressive
        }
        
        aggressiveness = aggressiveness_map.get(stealth_level, 0.05)
        
        # Apply strategic substitution
        modified_text, substitution_log = self.apply_strategic_substitution(header_text, aggressiveness)
        
        # Add invisible characters if stealth level allows
        if stealth_level in ['medium', 'high', 'maximum']:
            variation_type = 'minimal' if stealth_level == 'medium' else 'mixed'
            modified_text = self.create_invisible_variation(modified_text, variation_type)
        
        # Test the result
        invisibility_test = self.test_invisibility(header_text, modified_text)
        
        result_log = {
            'original': header_text,
            'modified': modified_text,
            'stealth_level': stealth_level,
            'substitution_log': substitution_log,
            'invisibility_test': invisibility_test,
            'recommendation': self.get_stealth_recommendation(invisibility_test)
        }
        
        return modified_text, result_log
    
    def get_stealth_recommendation(self, invisibility_test: Dict) -> str:
        """Get recommendation based on invisibility test results"""
        visual_sim = invisibility_test['visual_similarity']
        detection_prob = invisibility_test['substitution_detection']['substitution_probability']
        
        if visual_sim > 0.95 and detection_prob < 0.1:
            return "Excellent stealth - very low detection risk"
        elif visual_sim > 0.9 and detection_prob < 0.2:
            return "Good stealth - low detection risk"
        elif visual_sim > 0.8 and detection_prob < 0.3:
            return "Moderate stealth - medium detection risk"
        else:
            return "High detection risk - consider reducing aggressiveness"


def create_invisible_chars_file():
    """Create invisible characters database file"""
    invisible_chars = {
        "zero_width": {
            "ZWSP": "\u200B",
            "ZWNJ": "\u200C", 
            "ZWJ": "\u200D",
            "ZWNBSP": "\uFEFF"
        },
        "minimal_width": {
            "THIN_SPACE": "\u2009",
            "HAIR_SPACE": "\u200A",
            "SIX_PER_EM": "\u2006",
            "PUNCTUATION_SPACE": "\u2008"
        },
        "variation_selectors": {
            "VS15": "\uFE0E",
            "VS16": "\uFE0F"
        },
        "insertion_patterns": {
            "after_punctuation": [".", ",", ";", ":", "!", "?"],
            "between_words": [" "],
            "in_headers": ["BAB", "PENDAHULUAN", "METODE", "HASIL", "KESIMPULAN"],
            "strategic_positions": ["start_sentence", "end_paragraph"]
        },
        "detection_avoidance": {
            "max_consecutive": 2,
            "insertion_rate": 0.05,
            "randomization": True,
            "avoid_patterns": True
        }
    }
    
    import os
    os.makedirs('data', exist_ok=True)
    
    with open('data/invisible_chars.json', 'w', encoding='utf-8') as f:
        json.dump(invisible_chars, f, ensure_ascii=False, indent=2)
    
    print("✅ Invisible characters database created: data/invisible_chars.json")


def create_header_patterns_file():
    """Create header patterns database file"""
    header_patterns = {
        "header_indicators": {
            "chapter_patterns": ["BAB", "CHAPTER", "BAGIAN", "SECTION"],
            "section_patterns": ["PENDAHULUAN", "METODE", "HASIL", "KESIMPULAN", "DAFTAR PUSTAKA"],
            "subsection_patterns": ["Latar Belakang", "Rumusan Masalah", "Tujuan", "Manfaat"],
            "formatting_clues": {
                "all_caps": True,
                "short_length": 6,
                "centered": True,
                "bold": True,
                "isolated": True
            }
        },
        "priority_headers": [
            {"text": "BAB I", "priority": "highest", "techniques": ["unicode_substitution", "invisible_chars"]},
            {"text": "PENDAHULUAN", "priority": "highest", "techniques": ["unicode_substitution"]}, 
            {"text": "BAB II", "priority": "high", "techniques": ["unicode_substitution"]},
            {"text": "TINJAUAN PUSTAKA", "priority": "high", "techniques": ["invisible_chars"]},
            {"text": "BAB III", "priority": "high", "techniques": ["unicode_substitution"]}, 
            {"text": "METODE PENELITIAN", "priority": "highest", "techniques": ["unicode_substitution"]},
            {"text": "BAB IV", "priority": "high", "techniques": ["unicode_substitution"]},
            {"text": "HASIL DAN PEMBAHASAN", "priority": "highest", "techniques": ["unicode_substitution"]},
            {"text": "BAB V", "priority": "highest", "techniques": ["unicode_substitution"]},
            {"text": "KESIMPULAN", "priority": "highest", "techniques": ["unicode_substitution"]}
        ],
        "detection_patterns": {
            "common_academic_phrases": [
                "berdasarkan hasil penelitian",
                "penelitian menunjukkan bahwa", 
                "dapat disimpulkan bahwa",
                "tujuan penelitian ini",
                "metode yang digunakan",
                "analisis data menunjukkan"
            ],
            "high_risk_words": [
                "penelitian", "analisis", "metode", "hasil", "kesimpulan",
                "data", "variabel", "hipotesis", "teori", "konsep"
            ]
        }
    }
    
    import os
    os.makedirs('data', exist_ok=True)
    
    with open('data/header_patterns.json', 'w', encoding='utf-8') as f:
        json.dump(header_patterns, f, ensure_ascii=False, indent=2)
    
    print("✅ Header patterns database created: data/header_patterns.json")


def main():
    """Test Unicode steganography module"""
    print("🔤 UNICODE STEGANOGRAPHY MODULE - TEST")
    print("=" * 50)
    
    # Initialize module
    steg = UnicodeSteg()
    
    # Generate mapping files
    steg.generate_mapping_file()
    create_invisible_chars_file()
    create_header_patterns_file()
    
    # Test with sample headers
    test_headers = [
        "BAB I",
        "PENDAHULUAN", 
        "A. Latar Belakang",
        "METODE PENELITIAN",
        "HASIL DAN PEMBAHASAN",
        "KESIMPULAN"
    ]
    
    print("\n🧪 Testing header steganography:")
    for header in test_headers:
        print(f"\n📄 Original: '{header}'")
        
        modified, log = steg.create_steganographic_header(header, 'medium')
        
        print(f"🔀 Modified: '{modified}'")
        print(f"📊 Changes: {log['substitution_log']['total_changes']}")
        print(f"💡 Recommendation: {log['recommendation']}")
        print(f"👁️ Visual similarity: {log['invisibility_test']['visual_similarity']:.2%}")
    
    print(f"\n✅ Unicode steganography testing completed!")


if __name__ == "__main__":
    main()
            
