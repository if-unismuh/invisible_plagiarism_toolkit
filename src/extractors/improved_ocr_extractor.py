#!/usr/bin/env python3
"""
Improved OCR Extractor for Turnitin PDF
========================================
Enhanced version dengan:
- Image preprocessing untuk better OCR
- Adaptive thresholding
- Noise reduction
- Multi-scale extraction
- Better text cleanup
- Fallback mechanisms

Author: DevNoLife
Version: 2.0 (Improved)
"""

import cv2
import numpy as np
import pytesseract
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import logging


class ImprovedOCRExtractor:
    """Enhanced OCR extractor dengan preprocessing"""

    def __init__(self, lang: str = "ind+eng"):
        """
        Initialize OCR extractor

        Args:
            lang: Tesseract language (default: ind+eng)
        """
        self.lang = lang
        self.logger = logging.getLogger(self.__class__.__name__)

        # OCR confidence thresholds
        self.min_confidence_strict = 60  # For clean text
        self.min_confidence_lenient = 30  # For noisy text

        # Preprocessing flags
        self.enable_denoising = True
        self.enable_contrast = True
        self.enable_binarization = True

    def preprocess_image(self, img: np.ndarray, mode: str = "balanced") -> np.ndarray:
        """
        Preprocess image untuk better OCR accuracy

        Args:
            img: Input image (RGB)
            mode: Preprocessing mode (gentle/balanced/aggressive)

        Returns:
            Preprocessed image
        """

        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img.copy()

        # 1. Noise reduction (optional)
        if self.enable_denoising:
            if mode == "aggressive":
                # Bilateral filter - preserve edges while removing noise
                gray = cv2.bilateralFilter(gray, 9, 75, 75)
            elif mode == "balanced":
                # Gaussian blur - gentle noise reduction
                gray = cv2.GaussianBlur(gray, (3, 3), 0)
            # gentle mode: no denoising

        # 2. Contrast enhancement (optional)
        if self.enable_contrast:
            if mode in ["balanced", "aggressive"]:
                # CLAHE (Contrast Limited Adaptive Histogram Equalization)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                gray = clahe.apply(gray)

        # 3. Binarization (optional)
        if self.enable_binarization:
            if mode == "aggressive":
                # Adaptive thresholding - good for varying lighting
                gray = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 11, 2
                )
            elif mode == "balanced":
                # Otsu's thresholding - automatic threshold selection
                _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # gentle mode: no binarization

        return gray

    def extract_text_from_region(self, img: np.ndarray, bbox: Tuple[int, int, int, int],
                                preprocessing: str = "balanced") -> Dict[str, Any]:
        """
        Extract text from specific region dengan preprocessing

        Args:
            img: Full page image
            bbox: Region coordinates (x0, y0, x1, y1)
            preprocessing: Preprocessing mode

        Returns:
            Dict dengan text, confidence, word_count
        """
        x0, y0, x1, y1 = bbox

        # Expand bbox sedikit untuk catch edge words
        padding = 5
        x0 = max(0, x0 - padding)
        y0 = max(0, y0 - padding)
        x1 = min(img.shape[1], x1 + padding)
        y1 = min(img.shape[0], y1 + padding)

        # Crop region
        region = img[y0:y1, x0:x1].copy()

        if region.size == 0:
            return {'text': '', 'confidence': 0.0, 'word_count': 0}

        # Try multiple preprocessing strategies
        strategies = [preprocessing]

        # Add fallback strategies if initial fails
        if preprocessing == "balanced":
            strategies.extend(["aggressive", "gentle"])
        elif preprocessing == "gentle":
            strategies.append("balanced")
        elif preprocessing == "aggressive":
            strategies.append("balanced")

        best_result = {'text': '', 'confidence': 0.0, 'word_count': 0}

        for strategy in strategies:
            try:
                # Preprocess
                processed = self.preprocess_image(region, mode=strategy)

                # OCR dengan detailed output
                ocr_data = pytesseract.image_to_data(
                    processed,
                    output_type=pytesseract.Output.DICT,
                    lang=self.lang,
                    config='--psm 6'  # Assume uniform block of text
                )

                # Extract words dengan confidence filtering
                words = []
                confidences = []

                for i in range(len(ocr_data['text'])):
                    word = (ocr_data['text'][i] or '').strip()
                    if not word:
                        continue

                    try:
                        conf = float(ocr_data['conf'][i])
                    except (ValueError, TypeError):
                        continue

                    # Adaptive confidence threshold
                    min_conf = self.min_confidence_lenient if strategy == "aggressive" else self.min_confidence_strict

                    if conf >= min_conf:
                        words.append(word)
                        confidences.append(conf)

                if not words:
                    continue

                # Calculate average confidence
                avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
                text = ' '.join(words)

                # Check if this is better than previous attempts
                if len(words) > best_result['word_count'] or \
                   (len(words) == best_result['word_count'] and avg_conf > best_result['confidence']):
                    best_result = {
                        'text': text,
                        'confidence': avg_conf,
                        'word_count': len(words),
                        'strategy': strategy
                    }

                # If we got good results, stop trying
                if avg_conf > 70 and len(words) > 3:
                    break

            except Exception as e:
                self.logger.warning(f"OCR failed with {strategy} strategy: {e}")
                continue

        return best_result

    def extract_text_from_full_page(self, img: np.ndarray,
                                   preprocessing: str = "balanced") -> List[Dict[str, Any]]:
        """
        Extract all text from full page (word-level) dengan preprocessing

        Args:
            img: Page image
            preprocessing: Preprocessing mode

        Returns:
            List of word dicts dengan bbox, text, confidence
        """

        # Preprocess entire image
        processed = self.preprocess_image(img, mode=preprocessing)

        try:
            # OCR dengan word-level bboxes
            ocr_data = pytesseract.image_to_data(
                processed,
                output_type=pytesseract.Output.DICT,
                lang=self.lang,
                config='--psm 3'  # Fully automatic page segmentation
            )
        except Exception as e:
            self.logger.error(f"Tesseract failed: {e}")
            return []

        words = []
        for i in range(len(ocr_data['text'])):
            word = (ocr_data['text'][i] or '').strip()
            if not word:
                continue

            try:
                conf = float(ocr_data['conf'][i])
            except (ValueError, TypeError):
                continue

            # Adaptive threshold
            min_conf = self.min_confidence_lenient if preprocessing == "aggressive" else self.min_confidence_strict

            if conf < min_conf:
                continue

            x = ocr_data['left'][i]
            y = ocr_data['top'][i]
            w = ocr_data['width'][i]
            h = ocr_data['height'][i]

            words.append({
                'bbox': (x, y, x + w, y + h),
                'text': word,
                'confidence': conf
            })

        return words

    def clean_extracted_text(self, text: str) -> str:
        """
        Clean extracted text dari OCR artifacts

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        import re

        # Remove excessive whitespace
        text = ' '.join(text.split())

        # Fix common OCR errors for Indonesian/English
        replacements = {
            # Common OCR mistakes
            '0': 'O',  # Zero → O (in context)
            '|': 'I',  # Pipe → I
            '1': 'l',  # One → l (in context)

            # Fix broken words (optional - may cause issues)
            # r'\s+([.,;:!?])': r'\1',  # Remove space before punctuation
        }

        # Apply replacements carefully (context-aware)
        # For now, just basic cleanup

        # Remove non-printable characters
        text = ''.join(char for char in text if char.isprintable() or char.isspace())

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace("'", "'").replace("'", "'")

        return text.strip()

    def extract_with_multiscale(self, img: np.ndarray, bbox: Tuple[int, int, int, int]) -> str:
        """
        Try OCR dengan multiple scales untuk better accuracy

        Args:
            img: Page image
            bbox: Region to extract

        Returns:
            Best text extraction
        """
        x0, y0, x1, y1 = bbox
        region = img[y0:y1, x0:x1].copy()

        if region.size == 0:
            return ""

        scales = [1.0, 1.5, 2.0]  # Try different scales
        best_text = ""
        best_confidence = 0.0

        for scale in scales:
            # Resize region
            if scale != 1.0:
                new_w = int(region.shape[1] * scale)
                new_h = int(region.shape[0] * scale)
                scaled = cv2.resize(region, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            else:
                scaled = region

            # Extract
            result = self.extract_text_from_region(
                np.vstack([np.zeros((y0, scaled.shape[1], 3), dtype=np.uint8),
                           np.hstack([np.zeros((scaled.shape[0], x0, 3), dtype=np.uint8), scaled,
                                     np.zeros((scaled.shape[0], img.shape[1] - x1, 3), dtype=np.uint8)]),
                           np.zeros((img.shape[0] - y1, scaled.shape[1], 3), dtype=np.uint8)]),
                (x0, y0, x0 + scaled.shape[1], y0 + scaled.shape[0])
            )

            if result['confidence'] > best_confidence:
                best_confidence = result['confidence']
                best_text = result['text']

        return best_text


def enhance_ocr_accuracy(img: np.ndarray, bbox: Tuple[int, int, int, int],
                        lang: str = "ind+eng") -> Dict[str, Any]:
    """
    Helper function untuk enhanced OCR extraction

    Args:
        img: Page image
        bbox: Bounding box (x0, y0, x1, y1)
        lang: Tesseract language

    Returns:
        Dict dengan text, confidence, details
    """
    extractor = ImprovedOCRExtractor(lang=lang)
    result = extractor.extract_text_from_region(img, bbox, preprocessing="balanced")

    # Clean text
    if result['text']:
        result['text'] = extractor.clean_extracted_text(result['text'])

    return result


def extract_words_from_page(img: np.ndarray, lang: str = "ind+eng",
                           preprocessing: str = "balanced") -> List[Dict[str, Any]]:
    """
    Helper function untuk extract all words dari page

    Args:
        img: Page image
        lang: Tesseract language
        preprocessing: Preprocessing mode

    Returns:
        List of word dicts
    """
    extractor = ImprovedOCRExtractor(lang=lang)
    words = extractor.extract_text_from_full_page(img, preprocessing=preprocessing)

    # Clean each word
    for word in words:
        word['text'] = extractor.clean_extracted_text(word['text'])

    return [w for w in words if w['text']]  # Filter empty


if __name__ == '__main__':
    # Test dengan sample image
    print("="*70)
    print("IMPROVED OCR EXTRACTOR - TEST")
    print("="*70)

    # Create sample test image
    test_img = np.ones((200, 800, 3), dtype=np.uint8) * 255

    # Add some text with noise
    import cv2
    cv2.putText(test_img, "BAB I PENDAHULUAN", (50, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)

    # Add noise
    noise = np.random.randint(0, 30, test_img.shape, dtype=np.uint8)
    test_img = cv2.add(test_img, noise)

    # Test extraction
    extractor = ImprovedOCRExtractor(lang="eng")

    # Test different preprocessing modes
    for mode in ["gentle", "balanced", "aggressive"]:
        print(f"\nTesting with {mode} preprocessing:")
        result = extractor.extract_text_from_region(
            test_img,
            (0, 0, 800, 200),
            preprocessing=mode
        )
        print(f"  Text: {result['text']}")
        print(f"  Confidence: {result['confidence']:.1f}%")
        print(f"  Word count: {result['word_count']}")

    print("\n" + "="*70)
    print("Test complete!")
