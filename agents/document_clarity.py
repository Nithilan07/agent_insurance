"""
Document Quality Assessment Agent - Function-Based

Evaluates document clarity, alignment, readability, and AI-generation likelihood.
No classes - pure functions that accept parameters and return JSON.

Usage:
    # Analyze from file path
    result = assess_quality_from_file('document.pdf')
    
    # Analyze from bytes
    with open('scan.jpg', 'rb') as f:
        result = assess_quality_from_bytes(f.read(), 'scan.jpg')
    
    # Analyze from base64
    result = assess_quality_from_base64(base64_string, 'report.pdf')
"""

import io
import base64
from pathlib import Path
from typing import Union, Dict, List, Any, Optional
from datetime import datetime
import numpy as np
import cv2
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image


# ============================================================================
# CONFIGURATION
# ============================================================================

# Default thresholds and weights
DEFAULT_CONFIG = {
    'clarity_threshold': 0.8,
    'alignment_weight': 0.25,
    'clarity_weight': 0.40,
    'readability_weight': 0.35,
    'ai_penalty_weight': 0.10
}


# ============================================================================
# CORE QUALITY ASSESSMENT FUNCTIONS
# ============================================================================

def alignment_score(image: np.ndarray) -> float:
    """Measures skew or tilt in the document."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is None:
        return 1.0
    
    angles = [(theta - np.pi / 2) * 180 / np.pi for rho, theta in lines[:, 0]]
    median_angle = np.median(angles)
    score = max(0, 1 - abs(median_angle) / 15)
    return float(min(1, score))


def clarity_score(image: np.ndarray) -> float:
    """Measures blurriness using Laplacian variance."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    fm = cv2.Laplacian(gray, cv2.CV_64F).var()
    return float(min(fm / 500.0, 1.0))


def readability_score(image: np.ndarray) -> float:
    """Measures OCR text box detection ratio."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    
    try:
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        text_boxes = sum([1 for conf in data['conf'] if conf != '-1'])
        total_boxes = len(data['conf'])
        
        if total_boxes == 0:
            return 0.0
        
        return float(text_boxes / total_boxes)
    except Exception:
        return 0.0


def ai_generated_probability(image: np.ndarray) -> float:
    """Estimate chance that document is AI-generated."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Entropy-based smoothness score
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten() / hist.sum()
    entropy = -np.sum(hist * np.log2(hist + 1e-10))
    smoothness_score = 1 - (entropy / 8.0)
    
    # Frequency domain analysis
    f_transform = np.fft.fft2(gray)
    f_shift = np.fft.fftshift(f_transform)
    magnitude = np.abs(f_shift)
    
    rows, cols = gray.shape
    crow, ccol = rows // 2, cols // 2
    high_freq_region = magnitude.copy()
    high_freq_region[crow-30:crow+30, ccol-30:ccol+30] = 0
    high_freq_energy = np.sum(high_freq_region) / magnitude.size
    high_freq_score = 1 - min(high_freq_energy / 1000, 1.0)
    
    ai_prob = (0.5 * smoothness_score + 0.5 * high_freq_score) * 0.5
    return float(np.clip(ai_prob, 0, 1))


def evaluate_image(image: np.ndarray) -> Dict[str, float]:
    """Evaluate all quality metrics for a single image."""
    return {
        'alignment': alignment_score(image),
        'clarity': clarity_score(image),
        'readability': readability_score(image),
        'ai_generated': ai_generated_probability(image)
    }


def aggregate_scores(page_results: List[Dict]) -> Dict[str, float]:
    """Aggregate scores across all pages."""
    all_scores = {
        'alignment': [],
        'clarity': [],
        'readability': [],
        'ai_generated': []
    }
    
    for page in page_results:
        for metric, value in page['scores'].items():
            all_scores[metric].append(value)
    
    return {
        metric: float(np.mean(values))
        for metric, values in all_scores.items()
    }


def make_decision(scores: Dict[str, float], config: Dict = None) -> Dict[str, Any]:
    """
    Determine if document is readable and acceptable.
    
    Args:
        scores: Dictionary of quality scores
        config: Optional configuration with weights and threshold
        
    Returns:
        Decision with weighted score and breakdown
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    ai_penalty = scores['ai_generated'] * 0.3
    
    weighted_score = (
        config['alignment_weight'] * scores['alignment'] +
        config['clarity_weight'] * scores['clarity'] +
        config['readability_weight'] * scores['readability'] -
        config['ai_penalty_weight'] * ai_penalty
    )
    
    is_acceptable = weighted_score > config['clarity_threshold']
    
    recommendations = generate_recommendations(scores, weighted_score, config['clarity_threshold'])
    
    return {
        'acceptable': is_acceptable,
        'weighted_score': float(weighted_score),
        'ai_penalty': float(ai_penalty),
        'threshold': config['clarity_threshold'],
        'status': 'READABLE ✅' if is_acceptable else 'NOT READABLE ❌',
        'recommendations': recommendations
    }


def generate_recommendations(scores: Dict[str, float], weighted_score: float, threshold: float) -> List[str]:
    """Generate recommendations based on scores."""
    recommendations = []
    
    if scores['clarity'] < 0.5:
        recommendations.append("⚠ Low clarity - document may be blurry or low resolution")
    
    if scores['alignment'] < 0.5:
        recommendations.append("⚠ Poor alignment - document may be skewed or tilted")
    
    if scores['readability'] < 0.5:
        recommendations.append("⚠ Low readability - OCR detection is poor")
    
    if scores['ai_generated'] > 0.6:
        recommendations.append("ℹ Document shows characteristics of AI generation")
    
    if weighted_score <= threshold:
        recommendations.append("❌ Document does not meet quality standards for processing")
    else:
        recommendations.append("✅ Document meets quality standards")
    
    return recommendations


# ============================================================================
# FILE CONVERSION FUNCTIONS
# ============================================================================

def pdf_bytes_to_images(pdf_data: bytes) -> List[np.ndarray]:
    """Convert PDF bytes to list of OpenCV images."""
    pil_images = convert_from_bytes(pdf_data, dpi=200)
    return [cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR) for img in pil_images]


def bytes_to_image(image_data: bytes) -> np.ndarray:
    """Convert image bytes to OpenCV image."""
    image = Image.open(io.BytesIO(image_data))
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


# ============================================================================
# MAIN ASSESSMENT FUNCTIONS
# ============================================================================

def assess_quality_from_file(file_path: Union[str, Path], config: Dict = None) -> Dict[str, Any]:
    """
    Assess document quality from file path.
    
    Args:
        file_path: Path to the document
        config: Optional configuration dict
        
    Returns:
        JSON-serializable dict with quality analysis
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {
            'success': False,
            'error': f'File not found: {file_path}',
            'timestamp': datetime.now().isoformat()
        }
    
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    return assess_quality_from_bytes(file_data, file_path.name, config)


def assess_quality_from_bytes(file_data: bytes, filename: str, config: Dict = None) -> Dict[str, Any]:
    """
    Assess document quality from bytes.
    
    Args:
        file_data: Raw file bytes
        filename: Original filename
        config: Optional configuration dict
        
    Returns:
        JSON-serializable dict with quality analysis
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    try:
        file_ext = Path(filename).suffix.lower()
        
        # Convert to images
        if file_ext == '.pdf':
            images = pdf_bytes_to_images(file_data)
            doc_type = 'pdf'
        elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            images = [bytes_to_image(file_data)]
            doc_type = 'image'
        else:
            return {
                'success': False,
                'error': f'Unsupported file type: {file_ext}',
                'filename': filename,
                'timestamp': datetime.now().isoformat()
            }
        
        # Evaluate all pages/images
        page_results = []
        for i, img in enumerate(images):
            page_scores = evaluate_image(img)
            page_results.append({
                'page': i + 1,
                'scores': page_scores
            })
        
        # Calculate aggregate scores
        agg_scores = aggregate_scores(page_results)
        
        # Make decision
        decision_result = make_decision(agg_scores, config)
        
        return {
            'success': True,
            'filename': filename,
            'document_type': doc_type,
            'total_pages': len(images),
            'timestamp': datetime.now().isoformat(),
            'aggregate_scores': agg_scores,
            'decision': decision_result,
            'page_details': page_results
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        }


def assess_quality_from_base64(base64_data: str, filename: str, config: Dict = None) -> Dict[str, Any]:
    """
    Assess document quality from base64 string.
    
    Args:
        base64_data: Base64 encoded file data
        filename: Original filename
        config: Optional configuration dict
        
    Returns:
        JSON-serializable dict with quality analysis
    """
    try:
        file_data = base64.b64decode(base64_data)
        return assess_quality_from_bytes(file_data, filename, config)
    except Exception as e:
        return {
            'success': False,
            'error': f'Base64 decode error: {str(e)}',
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        }


def assess_image_array(image: np.ndarray, identifier: str = "image", config: Dict = None) -> Dict[str, Any]:
    """
    Assess quality of a single image array (useful for integrating with other systems).
    
    Args:
        image: OpenCV image (BGR format)
        identifier: Identifier for the image
        config: Optional configuration dict
        
    Returns:
        JSON-serializable dict with quality analysis
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    try:
        scores = evaluate_image(image)
        decision_result = make_decision(scores, config)
        
        return {
            'success': True,
            'identifier': identifier,
            'document_type': 'image_array',
            'timestamp': datetime.now().isoformat(),
            'scores': scores,
            'decision': decision_result
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'identifier': identifier,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def quick_assess(file_path: str) -> Dict[str, Any]:
    """Quick assessment of a document - convenience function."""
    return assess_quality_from_file(file_path)