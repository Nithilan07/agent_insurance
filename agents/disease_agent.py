"""
Medical Analysis Agent - Function-Based

Analyzes medical images and documents without classes.
Accepts files as parameters and returns JSON responses.

Usage:
    # Initialize once
    initialize_models()
    
    # Analyze from file path
    result = analyze_from_file('chest_xray.jpg')
    
    # Analyze from bytes
    with open('scan.jpg', 'rb') as f:
        result = analyze_from_bytes(f.read(), 'scan.jpg')
    
    # Analyze from base64
    result = analyze_from_base64(base64_string, 'brain_scan.jpg')
"""

import io
import base64
from pathlib import Path
from typing import Dict, List, Any, Union, Optional
from datetime import datetime
import numpy as np
import warnings
import re
warnings.filterwarnings('ignore')

try:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
    from torchvision import models
    from PIL import Image
    import torchxrayvision as xrv
    import pytesseract
    import cv2
    import PyPDF2
    from transformers import pipeline, AutoTokenizer, AutoModel
    DEPS_AVAILABLE = True
except ImportError as e:
    DEPS_AVAILABLE = False
    print(f"Error: Missing required packages")


# ============================================================================
# GLOBAL STATE (initialized once)
# ============================================================================

MODELS = {}
DISEASE_MAPPINGS = {}
DEVICE = None
TEXT_ANALYZER = {}
OCR_AVAILABLE = False


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_models():
    """Initialize all models once. Call this before using the agent."""
    global MODELS, DISEASE_MAPPINGS, DEVICE, TEXT_ANALYZER, OCR_AVAILABLE
    
    if not DEPS_AVAILABLE:
        return {"success": False, "error": "Required dependencies not installed"}
    
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print("\n" + "="*80)
    print("INITIALIZING MEDICAL ANALYSIS AGENT")
    print("="*80 + "\n")
    
    # Initialize image models
    print("🖼️  Loading Medical Image Models...")
    
    # Chest X-ray models
    try:
        MODELS['chest_densenet'] = xrv.models.DenseNet(weights="densenet121-res224-all")
        MODELS['chest_densenet'].to(DEVICE)
        MODELS['chest_densenet'].eval()
        
        MODELS['chest_resnet'] = xrv.models.ResNet(weights="resnet50-res512-all")
        MODELS['chest_resnet'].to(DEVICE)
        MODELS['chest_resnet'].eval()
        
        DISEASE_MAPPINGS['chest'] = MODELS['chest_densenet'].pathologies
        print(f"  ✓ Chest models loaded")
    except Exception as e:
        print(f"  ✗ Chest models failed: {e}")
        MODELS['chest_densenet'] = None
        MODELS['chest_resnet'] = None
    
    # Brain model
    try:
        brain_model = models.resnet50(pretrained=True)
        brain_model.fc = nn.Linear(brain_model.fc.in_features, 4)
        MODELS['brain'] = brain_model.to(DEVICE)
        MODELS['brain'].eval()
        DISEASE_MAPPINGS['brain'] = ['Normal Brain', 'Glioma', 'Meningioma', 'Pituitary Tumor']
        print(f"  ✓ Brain model loaded")
    except Exception as e:
        print(f"  ✗ Brain model failed: {e}")
        MODELS['brain'] = None
    
    # Fracture model
    try:
        fracture_model = models.mobilenet_v2(pretrained=True)
        fracture_model.classifier[1] = nn.Linear(fracture_model.classifier[1].in_features, 2)
        MODELS['fracture'] = fracture_model.to(DEVICE)
        MODELS['fracture'].eval()
        DISEASE_MAPPINGS['fracture'] = ['Fractured', 'Not Fractured']
        print(f"  ✓ Fracture model loaded")
    except Exception as e:
        print(f"  ✗ Fracture model failed: {e}")
        MODELS['fracture'] = None
    
    # General model
    try:
        general_model = models.densenet121(pretrained=True)
        general_model.classifier = nn.Linear(general_model.classifier.in_features, 10)
        MODELS['general'] = general_model.to(DEVICE)
        MODELS['general'].eval()
        DISEASE_MAPPINGS['general'] = [
            'Normal', 'Infection', 'Inflammation', 'Mass/Lesion', 'Fluid',
            'Bone Abnormality', 'Soft Tissue Damage', 'Vascular', 'Deformity', 'Foreign Body'
        ]
        print(f"  ✓ General model loaded")
    except Exception as e:
        print(f"  ✗ General model failed: {e}")
        MODELS['general'] = None
    
    # Initialize text analyzer
    print("\n🔤 Loading Medical Text Analysis Models...")
    _initialize_text_analyzer()
    
    # Initialize OCR
    print("\n📄 Initializing OCR Processor...")
    OCR_AVAILABLE = _check_ocr_available()
    
    print(f"\n✓ Agent ready on device: {DEVICE}\n")
    
    return {"success": True, "device": str(DEVICE)}


def _initialize_text_analyzer():
    """Initialize text analysis models."""
    try:
        TEXT_ANALYZER['tokenizer'] = AutoTokenizer.from_pretrained("dmis-lab/biobert-v1.1")
        TEXT_ANALYZER['model'] = AutoModel.from_pretrained("dmis-lab/biobert-v1.1")
        TEXT_ANALYZER['model'].to(DEVICE)
        TEXT_ANALYZER['model'].eval()
        
        TEXT_ANALYZER['ner'] = pipeline(
            "ner",
            model="samrawal/bert-base-uncased_clinical-ner",
            aggregation_strategy="simple",
            device=0 if DEVICE.type == "cuda" else -1
        )
        print("  ✓ BioBERT and Clinical NER models loaded")
    except Exception as e:
        print(f"  ✗ Failed to load text models: {e}")
        TEXT_ANALYZER['tokenizer'] = None
        TEXT_ANALYZER['model'] = None
        TEXT_ANALYZER['ner'] = None
    
    # Medical keywords for rule-based extraction
    TEXT_ANALYZER['disease_keywords'] = {
        'cardiovascular': ['heart attack', 'myocardial infarction', 'cardiac', 'coronary', 'hypertension', 
                          'arrhythmia', 'atherosclerosis', 'cardiomegaly', 'heart failure'],
        'respiratory': ['pneumonia', 'asthma', 'copd', 'tuberculosis', 'bronchitis', 'emphysema',
                       'pneumothorax', 'pleural effusion', 'covid', 'lung infection'],
        'neurological': ['stroke', 'seizure', 'epilepsy', 'migraine', 'alzheimer', 'parkinson',
                        'meningitis', 'encephalitis', 'brain tumor', 'glioma', 'concussion'],
        'orthopedic': ['fracture', 'broken bone', 'dislocation', 'arthritis', 'osteoporosis',
                      'sprain', 'torn ligament', 'cartilage damage'],
        'gastrointestinal': ['gastritis', 'ulcer', 'hepatitis', 'cirrhosis', 'pancreatitis',
                            'colitis', 'ibs', 'crohn', 'appendicitis'],
        'endocrine': ['diabetes', 'thyroid', 'hyperthyroidism', 'hypothyroidism', 'metabolic'],
        'infectious': ['infection', 'sepsis', 'abscess', 'cellulitis', 'bacterial', 'viral', 'fungal'],
        'oncology': ['cancer', 'tumor', 'malignancy', 'metastasis', 'carcinoma', 'lymphoma', 'leukemia']
    }
    
    TEXT_ANALYZER['severity_keywords'] = {
        'critical': ['critical', 'severe', 'acute', 'emergency', 'life-threatening', 'urgent'],
        'moderate': ['moderate', 'significant', 'substantial', 'considerable'],
        'mild': ['mild', 'slight', 'minor', 'minimal']
    }


def _check_ocr_available():
    """Check if OCR is available."""
    try:
        pytesseract.get_tesseract_version()
        print("  ✓ Tesseract OCR available")
        return True
    except Exception as e:
        print(f"  ✗ Tesseract not found: {e}")
        return False


# ============================================================================
# TEXT ANALYSIS FUNCTIONS
# ============================================================================

def extract_medical_entities(text: str) -> List[Dict]:
    """Extract medical entities using NER or rule-based approach."""
    if TEXT_ANALYZER.get('ner') is not None:
        try:
            entities = TEXT_ANALYZER['ner'](text)
            return entities
        except Exception as e:
            print(f"  Warning: NER failed, using rule-based extraction: {e}")
    
    return _rule_based_extraction(text)


def _rule_based_extraction(text: str) -> List[Dict]:
    """Fallback rule-based entity extraction."""
    text_lower = text.lower()
    findings = []
    
    for category, keywords in TEXT_ANALYZER['disease_keywords'].items():
        for keyword in keywords:
            if keyword in text_lower:
                idx = text_lower.find(keyword)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(keyword) + 50)
                context = text[start:end]
                
                findings.append({
                    'entity': keyword,
                    'category': category,
                    'context': context.strip()
                })
    
    return findings


def analyze_severity(text: str) -> tuple:
    """Determine severity from text."""
    text_lower = text.lower()
    severity_scores = {'critical': 0, 'moderate': 0, 'mild': 0}
    
    for severity, keywords in TEXT_ANALYZER['severity_keywords'].items():
        for keyword in keywords:
            severity_scores[severity] += text_lower.count(keyword)
    
    if severity_scores['critical'] > 0:
        return 'critical', severity_scores['critical']
    elif severity_scores['moderate'] > 0:
        return 'moderate', severity_scores['moderate']
    else:
        return 'mild', severity_scores['mild']


def extract_lab_values(text: str) -> Dict:
    """Extract laboratory values from text."""
    lab_patterns = {
        'blood_pressure': r'bp:?\s*(\d{2,3})/(\d{2,3})',
        'heart_rate': r'hr:?\s*(\d{2,3})',
        'temperature': r'temp:?\s*(\d{2,3}\.?\d?)',
        'glucose': r'glucose:?\s*(\d{2,4})',
        'hemoglobin': r'hb|hemoglobin:?\s*(\d{1,2}\.?\d?)',
        'wbc': r'wbc:?\s*(\d{1,5})',
    }
    
    lab_results = {}
    text_lower = text.lower()
    
    for lab_name, pattern in lab_patterns.items():
        matches = re.findall(pattern, text_lower)
        if matches:
            lab_results[lab_name] = matches
    
    return lab_results


def analyze_text(text: str) -> Dict[str, Any]:
    """Analyze medical text."""
    analysis = {
        'entities': [],
        'severity': None,
        'lab_values': {},
        'summary': ''
    }
    
    # Extract medical entities
    entities = extract_medical_entities(text)
    analysis['entities'] = entities
    
    # Determine severity
    severity, score = analyze_severity(text)
    analysis['severity'] = {'level': severity, 'score': int(score)}
    
    # Extract lab values
    lab_values = extract_lab_values(text)
    analysis['lab_values'] = lab_values
    
    # Create summary
    if entities:
        unique_conditions = list(set([e.get('entity', e.get('word', 'unknown')) for e in entities]))
        analysis['summary'] = f"Detected conditions: {', '.join(unique_conditions[:5])}"
    
    return analysis


# ============================================================================
# OCR FUNCTIONS
# ============================================================================

def extract_text_from_image(image_data: Union[bytes, np.ndarray, Image.Image]) -> Optional[str]:
    """Extract text from image using OCR."""
    if not OCR_AVAILABLE:
        return None
    
    try:
        # Convert to numpy array
        if isinstance(image_data, bytes):
            img = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        elif isinstance(image_data, Image.Image):
            img = np.array(image_data)
        else:
            img = image_data
        
        # Preprocess for better OCR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Extract text
        text = pytesseract.image_to_string(thresh, config='--psm 6')
        return text.strip()
    except Exception as e:
        print(f"  Error during OCR: {e}")
        return None


def extract_text_from_pdf(pdf_data: bytes) -> Optional[str]:
    """Extract text from PDF bytes."""
    try:
        text = ""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        
        return text.strip()
    except Exception as e:
        print(f"  Error reading PDF: {e}")
        return None


# ============================================================================
# IMAGE PROCESSING FUNCTIONS
# ============================================================================

def detect_file_type(filename: str) -> str:
    """Detect file type from filename."""
    filename_lower = filename.lower()
    
    # Check if it's a text document/report
    text_keywords = ['report', 'discharge', 'summary', 'lab', 'test', 'result', 'prescription']
    if any(kw in filename_lower for kw in text_keywords):
        return 'text_document'
    
    # Medical image types
    if any(word in filename_lower for word in ['chest', 'lung', 'thorax', 'cxr']):
        return 'chest'
    elif any(word in filename_lower for word in ['brain', 'head', 'mri', 'ct']):
        return 'brain'
    elif any(word in filename_lower for word in ['bone', 'fracture', 'arm', 'leg', 'hand', 'foot']):
        return 'bone'
    else:
        return 'general'


def preprocess_for_chest(image: Image.Image, target_size: int = 224):
    """Preprocess for chest models."""
    try:
        img = image.convert('L')
        img = img.resize((target_size, target_size), Image.LANCZOS)
        img_array = np.array(img, dtype=np.float32)
        
        if img_array.max() > 0:
            img_array = img_array / img_array.max()
        
        img_tensor = torch.from_numpy(img_array).unsqueeze(0).unsqueeze(0)
        return img_tensor.to(DEVICE)
    except:
        return None


def preprocess_for_brain_and_bones(image: Image.Image, target_size: int = 224):
    """Preprocess for brain/bone models."""
    try:
        img = image.convert('RGB')
        transform = transforms.Compose([
            transforms.Resize((target_size, target_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        img_tensor = transform(img).unsqueeze(0)
        return img_tensor.to(DEVICE)
    except:
        return None


def predict_chest(image_tensor):
    """Predict chest conditions."""
    if MODELS.get('chest_densenet') is None:
        return None
    try:
        with torch.no_grad():
            img_224 = torch.nn.functional.interpolate(image_tensor, size=(224, 224), mode='bilinear', align_corners=False)
            densenet_out = MODELS['chest_densenet'](img_224)
            densenet_probs = torch.sigmoid(densenet_out).cpu().numpy()[0]
            
            img_512 = torch.nn.functional.interpolate(image_tensor, size=(512, 512), mode='bilinear', align_corners=False)
            resnet_out = MODELS['chest_resnet'](img_512)
            resnet_probs = torch.sigmoid(resnet_out).cpu().numpy()[0]
            
            predictions = {}
            for i, disease in enumerate(DISEASE_MAPPINGS['chest']):
                predictions[disease] = float((densenet_probs[i] + resnet_probs[i]) / 2.0)
            return predictions
    except:
        return None


def predict_brain(image_tensor):
    """Predict brain conditions."""
    if MODELS.get('brain') is None:
        return None
    try:
        with torch.no_grad():
            outputs = MODELS['brain'](image_tensor)
            probs = torch.softmax(outputs, dim=1).cpu().numpy()[0]
            return {DISEASE_MAPPINGS['brain'][i]: float(probs[i]) for i in range(len(probs))}
    except:
        return None


def predict_fracture(image_tensor):
    """Predict fractures."""
    if MODELS.get('fracture') is None:
        return None
    try:
        with torch.no_grad():
            outputs = MODELS['fracture'](image_tensor)
            probs = torch.softmax(outputs, dim=1).cpu().numpy()[0]
            return {DISEASE_MAPPINGS['fracture'][i]: float(probs[i]) for i in range(len(probs))}
    except:
        return None


def predict_general(image_tensor):
    """General predictions."""
    if MODELS.get('general') is None:
        return None
    try:
        with torch.no_grad():
            outputs = MODELS['general'](image_tensor)
            probs = torch.softmax(outputs, dim=1).cpu().numpy()[0]
            return {DISEASE_MAPPINGS['general'][i]: float(probs[i]) for i in range(len(probs))}
    except:
        return None


def process_image(image: Image.Image, file_type: str) -> Dict[str, Any]:
    """Process medical image."""
    result = {
        'type': 'image',
        'subtype': file_type,
        'predictions': {},
        'extracted_text': None
    }
    
    # Try OCR first (might be a scanned report)
    if file_type == 'text_document':
        text = extract_text_from_image(image)
        if text and len(text) > 50:
            result['extracted_text'] = text
            result['text_analysis'] = analyze_text(text)
            return result
    
    # Process as medical image
    if file_type == 'chest':
        img_tensor = preprocess_for_chest(image)
        if img_tensor is not None:
            preds = predict_chest(img_tensor)
            if preds:
                result['predictions']['chest'] = preds
    
    elif file_type == 'brain':
        img_tensor = preprocess_for_brain_and_bones(image)
        if img_tensor is not None:
            preds = predict_brain(img_tensor)
            if preds:
                result['predictions']['brain'] = preds
    
    elif file_type == 'bone':
        img_tensor = preprocess_for_brain_and_bones(image)
        if img_tensor is not None:
            preds = predict_fracture(img_tensor)
            if preds:
                result['predictions']['fracture'] = preds
    
    # General analysis
    img_tensor_general = preprocess_for_brain_and_bones(image)
    if img_tensor_general is not None:
        general_preds = predict_general(img_tensor_general)
        if general_preds:
            result['predictions']['general'] = general_preds
    
    return result


def process_document(pdf_data: bytes, filename: str) -> Dict[str, Any]:
    """Process PDF or text document."""
    result = {
        'type': 'document',
        'extracted_text': None,
        'text_analysis': None
    }
    
    # Extract text
    if filename.lower().endswith('.pdf'):
        text = extract_text_from_pdf(pdf_data)
    else:  # .txt
        text = pdf_data.decode('utf-8', errors='ignore')
    
    if text and len(text) > 20:
        result['extracted_text'] = text
        result['text_analysis'] = analyze_text(text)
    
    return result


# ============================================================================
# MAIN ANALYSIS FUNCTIONS
# ============================================================================

def analyze_from_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Analyze a medical file from path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        JSON-serializable dict with analysis results
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
    
    return analyze_from_bytes(file_data, file_path.name)


def analyze_from_bytes(file_data: bytes, filename: str) -> Dict[str, Any]:
    """
    Analyze a medical file from bytes.
    
    Args:
        file_data: Raw file bytes
        filename: Original filename (for type detection)
        
    Returns:
        JSON-serializable dict with analysis results
    """
    try:
        file_ext = Path(filename).suffix.lower()
        file_type = detect_file_type(filename)
        
        result = {
            'success': True,
            'filename': filename,
            'file_type': file_type,
            'timestamp': datetime.now().isoformat(),
            'analysis': {}
        }
        
        # Handle PDFs
        if file_ext == '.pdf':
            result['analysis'] = process_document(file_data, filename)
        
        # Handle text files
        elif file_ext == '.txt':
            result['analysis'] = process_document(file_data, filename)
        
        # Handle images
        else:
            image = Image.open(io.BytesIO(file_data))
            result['analysis'] = process_image(image, file_type)
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        }


def analyze_from_base64(base64_data: str, filename: str) -> Dict[str, Any]:
    """
    Analyze a medical file from base64 string.
    
    Args:
        base64_data: Base64 encoded file data
        filename: Original filename
        
    Returns:
        JSON-serializable dict with analysis results
    """
    try:
        file_data = base64.b64decode(base64_data)
        return analyze_from_bytes(file_data, filename)
    except Exception as e:
        return {
            'success': False,
            'error': f'Base64 decode error: {str(e)}',
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        }