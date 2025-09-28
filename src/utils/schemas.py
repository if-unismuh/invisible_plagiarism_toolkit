# schemas.py
"""
Data schemas and validation for Invisible Plagiarism Toolkit
Type safety and configuration validation
"""

from typing import Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum
import json

class AggressionLevel(Enum):
    STEALTH = "stealth"
    BALANCED = "balanced" 
    AGGRESSIVE = "aggressive"

class DetectionTarget(Enum):
    TURNITIN = "turnitin"
    COPYSCAPE = "copyscape"
    GRAMMARLY = "grammarly"
    PLAGIARISM_CHECKER = "plagiarism_checker"

@dataclass
class ZeroWidthConfig:
    enabled: bool = True
    chars: List[str] = None
    insertion_rate: float = 0.05
    target_locations: List[str] = None
    randomization: bool = True
    
    def __post_init__(self):
        if self.chars is None:
            self.chars = ["\u200B", "\u200C", "\u200D", "\uFEFF"]
        if self.target_locations is None:
            self.target_locations = ["headers", "after_punctuation", "between_words"]
        
        # Validation
        if not 0 <= self.insertion_rate <= 0.5:
            raise ValueError("insertion_rate must be between 0 and 0.5")

@dataclass 
class UnicodeSubstitutionConfig:
    enabled: bool = True
    substitution_rate: float = 0.03
    target_chars: List[str] = None
    priority_words: List[str] = None
    stealth_level: str = "medium"
    
    def __post_init__(self):
        if self.target_chars is None:
            self.target_chars = ["a", "e", "o", "p", "c", "x", "y"]
        if self.priority_words is None:
            self.priority_words = ["BAB", "PENDAHULUAN", "METODE", "HASIL", "KESIMPULAN"]
            
        # Validation
        if not 0 <= self.substitution_rate <= 0.3:
            raise ValueError("substitution_rate must be between 0 and 0.3")

@dataclass
class SafetySettings:
    preserve_readability: bool = True
    maintain_formatting: bool = True
    backup_original: bool = True
    max_changes_per_paragraph: int = 5
    avoid_obvious_patterns: bool = True
    
    def __post_init__(self):
        if self.max_changes_per_paragraph < 1:
            raise ValueError("max_changes_per_paragraph must be >= 1")

@dataclass
class ProcessingConfig:
    zero_width_chars: ZeroWidthConfig
    unicode_substitution: UnicodeSubstitutionConfig
    safety_settings: SafetySettings
    detection_targets: Dict[str, Dict]
    target_elements: Dict[str, Dict]
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'ProcessingConfig':
        """Create ProcessingConfig from dictionary"""
        invisible_techniques = config_dict.get('invisible_techniques', {})
        
        return cls(
            zero_width_chars=ZeroWidthConfig(**invisible_techniques.get('zero_width_chars', {})),
            unicode_substitution=UnicodeSubstitutionConfig(**invisible_techniques.get('unicode_substitution', {})),
            safety_settings=SafetySettings(**config_dict.get('safety_settings', {})),
            detection_targets=config_dict.get('detection_targets', {}),
            target_elements=config_dict.get('target_elements', {})
        )

@dataclass
class ProcessingStats:
    total_documents: int = 0
    headers_modified: int = 0
    chars_substituted: int = 0
    invisible_chars_inserted: int = 0
    metadata_modified: int = 0
    processing_time: float = 0
    risk_score: float = 0
    invisibility_score: float = 0
    
    def to_dict(self) -> Dict:
        return {
            'total_documents': self.total_documents,
            'headers_modified': self.headers_modified,
            'chars_substituted': self.chars_substituted,
            'invisible_chars_inserted': self.invisible_chars_inserted,
            'metadata_modified': self.metadata_modified,
            'processing_time': self.processing_time,
            'risk_score': self.risk_score,
            'invisibility_score': self.invisibility_score
        }

def validate_config_file(config_path: str) -> ProcessingConfig:
    """Validate and load configuration file"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        return ProcessingConfig.from_dict(config_dict)
    except Exception as e:
        raise ValueError(f"Invalid configuration file: {e}")
