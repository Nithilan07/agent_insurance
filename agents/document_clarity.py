"""
Document Quality Assessment Agent - Fixed PDF Handling

Properly handles both scanned images and digital PDFs by detecting document type
and applying appropriate quality metrics.

Usage:
    result = assess_quality_from_file('document.pdf')
    result = assess_quality_from_bytes(file_data, 'scan.jpg')
    result = assess_quality_from_base64(base64_string, 'document.pdf')
"""

import io
import os
import base64
import tempfile
from pathlib import Path
from typing import Tuple, Union, Dict, List, Any, Optional
from datetime import datetime
import numpy as np
import cv2
import pytesseract
from pdf2image import convert_from_path
from PIL import Image


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_CONFIG = {
    'clarity_threshold': 0.70,
    'alignment_weight': 0.25,
    'clarity_weight': 0.40,
    'readability_weight': 0.35,
    'ai_penalty_weight': 0.10
}


# ============================================================================
# DOCUMENT TYPE DETECTION
# ============================================================================

def detect_document_type(image: np.ndarray, verbose: bool = False) -> str:
    """
    Detect if document is a clean digital render or a scanned/photographed document.
    
    Returns:
        'digital' - Clean PDF render or digital document
        'scanned' - Scanned or photographed document
    """
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # Check 1: Laplacian variance (clarity/sharpness)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Check 2: Text sharpness using gradient magnitude
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        avg_gradient = np.mean(gradient_magnitude)
        
        # Check 3: Background uniformity
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        background_pixels = np.sum(binary == 255)
        background_ratio = background_pixels / gray.size
        
        # Check 4: Noise level in background regions
        background_mask = binary == 255
        if np.sum(background_mask) > 0:
            background_std = np.std(gray[background_mask])
        else:
            background_std = 255
        
        # Check 5: JPEG artifacts (scanned docs often have compression artifacts)
        dct = cv2.dct(np.float32(gray[:64, :64]))
        high_freq_energy = np.sum(np.abs(dct[32:, 32:]))
        
        # Check 6: Color consistency (digital docs have more consistent colors)
        if len(image.shape) == 3:
            color_var = np.var(image, axis=(0, 1)).mean()
        else:
            color_var = 0
        
        # Scoring system with detailed analysis
        digital_score = 0
        indicators = []
        
        # High Laplacian variance suggests sharp, clear digital document
        if laplacian_var > 500:
            digital_score += 2
            indicators.append(f"High clarity ({laplacian_var:.1f})")
        elif laplacian_var < 100:
            indicators.append(f"Low clarity ({laplacian_var:.1f})")
        
        # Strong gradients suggest sharp text edges (digital)
        if avg_gradient > 20:
            digital_score += 2
            indicators.append(f"Sharp text edges ({avg_gradient:.1f})")
        
        # Clean, uniform background
        if background_ratio > 0.65 and background_std < 10:
            digital_score += 2
            indicators.append(f"Clean background (ratio={background_ratio:.2f}, std={background_std:.1f})")
        elif background_ratio < 0.5:
            indicators.append(f"Noisy background (ratio={background_ratio:.2f})")
        
        # Low high-frequency energy suggests clean rendering
        if high_freq_energy < 1000:
            digital_score += 1
            indicators.append("Low compression artifacts")
        
        # Image dimensions typical of PDF renders (often 1654x2339 or similar)
        if h > 2000 or w > 1500:
            digital_score += 1
            indicators.append(f"Large dimensions ({w}x{h})")
        
        if verbose:
            print(f"  → Document type analysis:")
            print(f"     Laplacian variance: {laplacian_var:.1f}")
            print(f"     Gradient magnitude: {avg_gradient:.1f}")
            print(f"     Background ratio: {background_ratio:.2f}")
            print(f"     Background std: {background_std:.1f}")
            print(f"     Digital score: {digital_score}/8")
            print(f"     Indicators: {', '.join(indicators)}")
        
        # Decision threshold - be more generous toward digital classification
        return 'digital' if digital_score >= 3 else 'scanned'
        
    except Exception as e:
        print(f"  Warning: Document type detection failed: {str(e)}")
        return 'scanned'  # Default to scanned for safety


# ============================================================================
# CORE QUALITY ASSESSMENT FUNCTIONS
# ============================================================================

def alignment_score(image: np.ndarray, doc_type: str = 'scanned') -> float:
    """Measures skew or tilt in the document."""
    try:
        # Digital documents are typically perfectly aligned
        if doc_type == 'digital':
            return 1.0
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None:
            return 1.0
        
        angles = [(theta - np.pi / 2) * 180 / np.pi for rho, theta in lines[:, 0]]
        median_angle = np.median(angles)
        score = max(0, 1 - abs(median_angle) / 15)
        return float(min(1, score))
    except Exception as e:
        print(f"  Warning: Alignment score calculation failed: {str(e)}")
        return 0.5


def clarity_score(image: np.ndarray, doc_type: str = 'scanned') -> float:
    """Measures clarity - adjusted for document type."""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        fm = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if doc_type == 'digital':
            # Digital docs should have high clarity - normalize differently
            # They typically have variance > 1000
            return float(min(fm / 1000.0, 1.0))
        else:
            # Scanned docs - original normalization
            return float(min(fm / 500.0, 1.0))
            
    except Exception as e:
        print(f"  Warning: Clarity score calculation failed: {str(e)}")
        return 0.5


def readability_score(image: np.ndarray, doc_type: str = 'scanned') -> float:
    """Measures text readability using OCR."""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Try multiple preprocessing approaches
        preprocessed_images = []
        
        if doc_type == 'digital':
            # For digital documents, minimal preprocessing
            preprocessed_images.append(gray)
            # Also try with slight thresholding
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed_images.append(binary)
        else:
            # For scanned documents, try multiple approaches
            # 1. Otsu's thresholding
            _, binary1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed_images.append(binary1)
            
            # 2. Adaptive thresholding
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                            cv2.THRESH_BINARY, 11, 2)
            preprocessed_images.append(adaptive)
            
            # 3. Original with denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            _, binary2 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed_images.append(binary2)
        
        # Try OCR on all preprocessed versions and take the best result
        best_ratio = 0
        
        for proc_img in preprocessed_images:
            try:
                data = pytesseract.image_to_data(proc_img, output_type=pytesseract.Output.DICT)
                
                # Count confident text detections
                confident_detections = sum([1 for conf in data['conf'] 
                                          if isinstance(conf, (int, float)) and conf > 30])
                total_boxes = len([c for c in data['conf'] if c != -1])
                
                if total_boxes > 0:
                    ratio = confident_detections / total_boxes
                    best_ratio = max(best_ratio, ratio)
            except:
                continue
        
        # Digital documents should have high text detection
        if doc_type == 'digital':
            # Be more lenient - digital docs are inherently readable
            return float(min(best_ratio * 1.3, 1.0))
        
        return float(min(best_ratio * 1.1, 1.0))
        
    except Exception as e:
        print(f"  Warning: Readability score calculation failed: {str(e)}")
        return 0.5


def ai_generated_probability(image: np.ndarray, doc_type: str = 'scanned') -> float:
    """Estimate chance that document is AI-generated."""
    try:
        # Digital PDFs are NOT AI-generated - they're just digital documents
        if doc_type == 'digital':
            return 0.0  # No AI generation penalty for clean PDFs
        
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
        
    except Exception as e:
        print(f"  Warning: AI probability calculation failed: {str(e)}")
        return 0.3


def evaluate_image(image: np.ndarray, verbose: bool = False) -> Dict[str, Any]:
    """Evaluate all quality metrics for a single image."""
    # First detect document type
    doc_type = detect_document_type(image, verbose=verbose)
    
    if verbose:
        print(f"     → Detected type: {doc_type}")
    
    scores = {
        'alignment': alignment_score(image, doc_type),
        'clarity': clarity_score(image, doc_type),
        'readability': readability_score(image, doc_type),
        'ai_generated': ai_generated_probability(image, doc_type)
    }
    
    if verbose:
        print(f"     → Scores: clarity={scores['clarity']:.3f}, "
              f"readability={scores['readability']:.3f}, "
              f"alignment={scores['alignment']:.3f}")
    
    return {
        'scores': scores,
        'document_type': doc_type
    }


def aggregate_scores(page_results: List[Dict]) -> Dict[str, Any]:
    """Aggregate scores across all pages."""
    all_scores = {
        'alignment': [],
        'clarity': [],
        'readability': [],
        'ai_generated': []
    }
    
    doc_types = []
    
    for page in page_results:
        for metric, value in page['scores'].items():
            all_scores[metric].append(value)
        doc_types.append(page.get('detected_type', 'unknown'))
    
    # Determine overall document type (majority vote)
    from collections import Counter
    type_counts = Counter(doc_types)
    overall_type = type_counts.most_common(1)[0][0] if type_counts else 'unknown'
    
    return {
        'scores': {
            metric: float(np.mean(values))
            for metric, values in all_scores.items()
        },
        'overall_document_type': overall_type
    }


def make_decision(scores: Dict[str, float], config: Dict = None, doc_type: str = 'scanned') -> Dict[str, Any]:
    """Determine if document is readable and acceptable."""
    if config is None:
        config = DEFAULT_CONFIG
    
    # Adjust AI penalty based on document type
    if doc_type == 'digital':
        ai_penalty = 0  # No AI penalty for digital documents
        # Use more lenient threshold for digital documents
        effective_threshold = config['clarity_threshold'] * 0.85
    else:
        ai_penalty = scores['ai_generated'] * 0.3
        effective_threshold = config['clarity_threshold']
    
    weighted_score = (
        config['alignment_weight'] * scores['alignment'] +
        config['clarity_weight'] * scores['clarity'] +
        config['readability_weight'] * scores['readability'] -
        config['ai_penalty_weight'] * ai_penalty
    )
    
    is_acceptable = weighted_score > effective_threshold
    
    recommendations = generate_recommendations(scores, weighted_score, effective_threshold, doc_type)
    
    return {
        'acceptable': is_acceptable,
        'weighted_score': float(weighted_score),
        'ai_penalty': float(ai_penalty),
        'threshold': effective_threshold,
        'document_type': doc_type,
        'status': 'READABLE ✅' if is_acceptable else 'NOT READABLE ❌',
        'recommendations': recommendations
    }


def generate_recommendations(scores: Dict[str, float], weighted_score: float, threshold: float, doc_type: str = 'scanned') -> List[str]:
    """Generate recommendations based on scores."""
    recommendations = []
    
    # Add document type info
    if doc_type == 'digital':
        recommendations.append("ℹ️ Digital document detected (clean PDF/digital render)")
    else:
        recommendations.append("ℹ️ Scanned/photographed document detected")
    
    # Type-specific recommendations
    if doc_type == 'scanned':
        if scores['clarity'] < 0.5:
            recommendations.append("⚠️ Low clarity - document may be blurry or low resolution")
        
        if scores['alignment'] < 0.5:
            recommendations.append("⚠️ Poor alignment - document may be skewed or tilted")
        
        if scores['ai_generated'] > 0.6:
            recommendations.append("ℹ️ Document shows characteristics of AI generation")
    else:
        # Digital document recommendations
        if scores['readability'] < 0.5:
            recommendations.append("⚠️ Low text detection - may be image-heavy or have rendering issues")
    
    # Universal readability check
    if scores['readability'] < 0.5:
        recommendations.append("⚠️ Low readability - OCR detection is poor")
    
    # Final verdict
    if weighted_score <= threshold:
        recommendations.append("❌ Document does not meet quality standards for processing")
        recommendations.append("   Please upload a clearer scan or higher quality image")
    else:
        recommendations.append("✅ Document meets quality standards")
    
    return recommendations


# ============================================================================
# FILE CONVERSION FUNCTIONS
# ============================================================================

def pdf_path_to_images(pdf_path: Union[str, Path], dpi: int = 200) -> List[np.ndarray]:
    """Convert PDF file to list of OpenCV images using convert_from_path."""
    try:
        pil_images = convert_from_path(pdf_path, dpi=dpi)
        return [cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR) for img in pil_images]
    except Exception as e:
        raise ValueError(f"Failed to convert PDF to images: {str(e)}")


def pdf_bytes_to_images(pdf_data: bytes, temp_suffix: str = '.pdf', dpi: int = 200) -> List[np.ndarray]:
    """Convert PDF bytes to list of OpenCV images."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=temp_suffix) as tmp_file:
            tmp_file.write(pdf_data)
            tmp_path = tmp_file.name
        
        images = pdf_path_to_images(tmp_path, dpi=dpi)
        return images
        
    except Exception as e:
        raise ValueError(f"Failed to convert PDF bytes to images: {str(e)}")
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as cleanup_error:
                print(f"  Warning: Failed to cleanup temp file {tmp_path}: {str(cleanup_error)}")


def bytes_to_image(image_data: bytes) -> np.ndarray:
    """Convert image bytes to OpenCV image."""
    try:
        image = Image.open(io.BytesIO(image_data))
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise ValueError(f"Failed to convert image bytes: {str(e)}")


# ============================================================================
# MAIN ASSESSMENT FUNCTIONS
# ============================================================================

def assess_quality_from_file(file_path: Union[str, Path], config: Dict = None, verbose: bool = True) -> Dict[str, Any]:
    """Assess document quality from file path."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {
            'success': False,
            'error': f'File not found: {file_path}',
            'timestamp': datetime.now().isoformat()
        }
    
    if config is None:
        config = DEFAULT_CONFIG
    
    try:
        file_ext = file_path.suffix.lower()
        
        # Convert to images
        if file_ext == '.pdf':
            images = pdf_path_to_images(file_path)
            source_type = 'pdf'
        elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            with open(file_path, 'rb') as f:
                images = [bytes_to_image(f.read())]
            source_type = 'image'
        else:
            return {
                'success': False,
                'error': f'Unsupported file type: {file_ext}',
                'filename': file_path.name,
                'timestamp': datetime.now().isoformat()
            }
        
        # Evaluate all pages/images
        page_results = []
        for i, img in enumerate(images):
            if verbose:
                print(f"  → Processing page {i+1}/{len(images)}...")
            
            page_eval = evaluate_image(img)
            page_results.append({
                'page': i + 1,
                'scores': page_eval['scores'],
                'detected_type': page_eval['document_type']
            })
        
        # Calculate aggregate scores
        agg_result = aggregate_scores(page_results)
        agg_scores = agg_result['scores']
        overall_type = agg_result['overall_document_type']
        
        if verbose:
            print(f"  → Detected as: {overall_type}")
            print(f"  → Aggregate scores calculated")
        
        # Make decision
        decision_result = make_decision(agg_scores, config, overall_type)
        
        return {
            'success': True,
            'filename': file_path.name,
            'source_type': source_type,
            'detected_document_type': overall_type,
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
            'filename': file_path.name,
            'timestamp': datetime.now().isoformat()
        }


def assess_quality_from_bytes(file_data: bytes, filename: str, config: Dict = None, verbose: bool = True) -> Dict[str, Any]:
    """Assess document quality from bytes."""
    if config is None:
        config = DEFAULT_CONFIG
    
    try:
        file_ext = Path(filename).suffix.lower()
        
        if verbose:
            print(f"  → Processing {filename} ({len(file_data)} bytes)")
        
        # Convert to images
        if file_ext == '.pdf':
            images = pdf_bytes_to_images(file_data, temp_suffix=file_ext)
            source_type = 'pdf'
        elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            images = [bytes_to_image(file_data)]
            source_type = 'image'
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
            if verbose:
                print(f"  → Analyzing page {i+1}/{len(images)}...")
            
            page_eval = evaluate_image(img, verbose=verbose)
            page_results.append({
                'page': i + 1,
                'scores': page_eval['scores'],
                'detected_type': page_eval['document_type']
            })
        
        # Calculate aggregate scores
        agg_result = aggregate_scores(page_results)
        agg_scores = agg_result['scores']
        overall_type = agg_result['overall_document_type']
        
        # Make decision
        decision_result = make_decision(agg_scores, config, overall_type)
        
        return {
            'success': True,
            'filename': filename,
            'source_type': source_type,
            'detected_document_type': overall_type,
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


def assess_quality_from_base64(base64_data: str, filename: str, config: Dict = None, verbose: bool = True) -> Dict[str, Any]:
    """Assess document quality from base64 string."""
    try:
        file_data = base64.b64decode(base64_data)
        return assess_quality_from_bytes(file_data, filename, config, verbose)
    except Exception as e:
        return {
            'success': False,
            'error': f'Base64 decode error: {str(e)}',
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_assess(file_path: str, config: Dict = None) -> Dict[str, Any]:
    """Quick assessment of a document."""
    return assess_quality_from_file(file_path, config=config)


def validate_document_bytes(file_data: bytes, filename: str, min_threshold: float = 0.70) -> Tuple[bool, Dict[str, Any]]:
    """Validate document quality and return pass/fail with full results."""
    config = DEFAULT_CONFIG.copy()
    config['clarity_threshold'] = min_threshold
    
    result = assess_quality_from_bytes(file_data, filename, config=config, verbose=False)
    
    if not result.get('success'):
        return False, result
    
    is_acceptable = result.get('decision', {}).get('acceptable', False)
    return is_acceptable, result


def assess_multiple_files(file_paths: List[Union[str, Path]], config: Dict = None, verbose: bool = True) -> Dict[str, Dict[str, Any]]:
    """Assess quality of multiple files."""
    results = {}
    
    for i, path in enumerate(file_paths, 1):
        if verbose:
            print(f"\n[{i}/{len(file_paths)}] Assessing {Path(path).name}...")
        
        result = assess_quality_from_file(path, config=config, verbose=verbose)
        results[Path(path).name] = result
    
    return results