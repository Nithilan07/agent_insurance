import io
import base64
from pathlib import Path
import numpy as np
from datetime import datetime
import json
import warnings
import re
from typing import Union, Dict, List, Optional, Any
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
except ImportError as e:
    print(f"Error: Missing required package. Please install dependencies:")
    print("\nCore packages:")
    print("pip install torch torchvision Pillow numpy torchxrayvision scikit-image")
    print("\nOCR and Text Analysis:")
    print("pip install pytesseract opencv-python PyPDF2 transformers sentencepiece")
    raise


class MedicalTextAnalyzer:
    """Analyzes medical text using NLP and medical entity extraction"""
    
    def __init__(self, device):
        self.device = device
        print("🔤 Loading Medical Text Analysis Models...")
        
        try:
            # Use BioBERT for medical text understanding
            self.tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-v1.1")
            self.text_model = AutoModel.from_pretrained("dmis-lab/biobert-v1.1")
            self.text_model.to(device)
            self.text_model.eval()
            
            # Medical NER pipeline
            self.ner_pipeline = pipeline(
                "ner",
                model="samrawal/bert-base-uncased_clinical-ner",
                aggregation_strategy="simple",
                device=0 if device.type == "cuda" else -1
            )
            
            print("  ✓ BioBERT and Clinical NER models loaded")
        except Exception as e:
            print(f"  ✗ Failed to load text models: {e}")
            print("  → Will use rule-based text analysis as fallback")
            self.tokenizer = None
            self.text_model = None
            self.ner_pipeline = None
        
        # Medical keywords for rule-based extraction
        self.disease_keywords = {
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
        
        self.severity_keywords = {
            'critical': ['critical', 'severe', 'acute', 'emergency', 'life-threatening', 'urgent'],
            'moderate': ['moderate', 'significant', 'substantial', 'considerable'],
            'mild': ['mild', 'slight', 'minor', 'minimal']
        }
    
    def extract_medical_entities(self, text):
        """Extract medical entities using NER"""
        if self.ner_pipeline is None:
            return self._rule_based_extraction(text)
        
        try:
            entities = self.ner_pipeline(text)
            return entities
        except Exception as e:
            print(f"  Warning: NER failed, using rule-based extraction: {e}")
            return self._rule_based_extraction(text)
    
    def _rule_based_extraction(self, text):
        """Fallback rule-based entity extraction"""
        text_lower = text.lower()
        findings = []
        
        for category, keywords in self.disease_keywords.items():
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
    
    def analyze_severity(self, text):
        """Determine severity from text"""
        text_lower = text.lower()
        severity_scores = {'critical': 0, 'moderate': 0, 'mild': 0}
        
        for severity, keywords in self.severity_keywords.items():
            for keyword in keywords:
                severity_scores[severity] += text_lower.count(keyword)
        
        if severity_scores['critical'] > 0:
            return 'critical', severity_scores['critical']
        elif severity_scores['moderate'] > 0:
            return 'moderate', severity_scores['moderate']
        else:
            return 'mild', severity_scores['mild']
    
    def extract_lab_values(self, text):
        """Extract laboratory values from text"""
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


class OCRProcessor:
    """Handles OCR for scanned documents"""
    
    def __init__(self):
        print("📄 Initializing OCR Processor...")
        try:
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            print("  ✓ Tesseract OCR available")
        except Exception as e:
            print(f"  ✗ Tesseract not found: {e}")
            self.tesseract_available = False
    
    def extract_text_from_image(self, image_data: Union[bytes, np.ndarray, Image.Image]) -> Optional[str]:
        """Extract text from image using OCR"""
        if not self.tesseract_available:
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
    
    def extract_text_from_pdf(self, pdf_data: bytes) -> Optional[str]:
        """Extract text from PDF bytes"""
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


class MedicalAnalysisAgent:
    """
    Agent-based medical analyzer that processes files as parameters
    and returns JSON responses.
    
    Usage:
        agent = MedicalAnalysisAgent()
        
        # Analyze from file path
        result = agent.analyze_file('path/to/xray.jpg')
        
        # Analyze from bytes
        with open('scan.jpg', 'rb') as f:
            result = agent.analyze_bytes(f.read(), filename='scan.jpg')
        
        # Analyze from base64
        result = agent.analyze_base64(base64_string, filename='report.pdf')
    """
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.models = {}
        self.disease_mappings = {}
        
        print("\n" + "="*80)
        print("INITIALIZING MEDICAL ANALYSIS AGENT")
        print("="*80 + "\n")
        
        self._initialize_image_models()
        self.ocr_processor = OCRProcessor()
        self.text_analyzer = MedicalTextAnalyzer(self.device)
        
        print(f"\n✓ Agent ready on device: {self.device}\n")
    
    def _initialize_image_models(self):
        """Initialize pre-trained models for medical images"""
        print("🖼️  Loading Medical Image Models...")
        
        # Chest X-ray models
        try:
            self.models['chest_densenet'] = xrv.models.DenseNet(weights="densenet121-res224-all")
            self.models['chest_densenet'].to(self.device)
            self.models['chest_densenet'].eval()
            
            self.models['chest_resnet'] = xrv.models.ResNet(weights="resnet50-res512-all")
            self.models['chest_resnet'].to(self.device)
            self.models['chest_resnet'].eval()
            
            self.disease_mappings['chest'] = self.models['chest_densenet'].pathologies
            print(f"  ✓ Chest models loaded")
        except Exception as e:
            print(f"  ✗ Chest models failed: {e}")
            self.models['chest_densenet'] = None
            self.models['chest_resnet'] = None
        
        # Brain model
        try:
            brain_model = models.resnet50(pretrained=True)
            brain_model.fc = nn.Linear(brain_model.fc.in_features, 4)
            self.models['brain'] = brain_model.to(self.device)
            self.models['brain'].eval()
            self.disease_mappings['brain'] = ['Normal Brain', 'Glioma', 'Meningioma', 'Pituitary Tumor']
            print(f"  ✓ Brain model loaded")
        except Exception as e:
            print(f"  ✗ Brain model failed: {e}")
            self.models['brain'] = None
        
        # Fracture model
        try:
            fracture_model = models.mobilenet_v2(pretrained=True)
            fracture_model.classifier[1] = nn.Linear(fracture_model.classifier[1].in_features, 2)
            self.models['fracture'] = fracture_model.to(self.device)
            self.models['fracture'].eval()
            self.disease_mappings['fracture'] = ['Fractured', 'Not Fractured']
            print(f"  ✓ Fracture model loaded")
        except Exception as e:
            print(f"  ✗ Fracture model failed: {e}")
            self.models['fracture'] = None
        
        # General model
        try:
            general_model = models.densenet121(pretrained=True)
            general_model.classifier = nn.Linear(general_model.classifier.in_features, 10)
            self.models['general'] = general_model.to(self.device)
            self.models['general'].eval()
            self.disease_mappings['general'] = [
                'Normal', 'Infection', 'Inflammation', 'Mass/Lesion', 'Fluid',
                'Bone Abnormality', 'Soft Tissue Damage', 'Vascular', 'Deformity', 'Foreign Body'
            ]
            print(f"  ✓ General model loaded")
        except Exception as e:
            print(f"  ✗ General model failed: {e}")
            self.models['general'] = None
    
    def detect_file_type(self, filename: str) -> str:
        """Detect file type from filename"""
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
    
    def analyze_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyze a medical file from path
        
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
        
        return self.analyze_bytes(file_data, filename=file_path.name)
    
    def analyze_bytes(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze a medical file from bytes
        
        Args:
            file_data: Raw file bytes
            filename: Original filename (for type detection)
            
        Returns:
            JSON-serializable dict with analysis results
        """
        try:
            file_ext = Path(filename).suffix.lower()
            file_type = self.detect_file_type(filename)
            
            result = {
                'success': True,
                'filename': filename,
                'file_type': file_type,
                'timestamp': datetime.now().isoformat(),
                'analysis': {}
            }
            
            # Handle PDFs
            if file_ext == '.pdf':
                text = self.ocr_processor.extract_text_from_pdf(file_data)
                if text and len(text) > 20:
                    result['analysis'] = {
                        'type': 'document',
                        'extracted_text': text,
                        'text_analysis': self._analyze_text(text)
                    }
            
            # Handle text files
            elif file_ext == '.txt':
                text = file_data.decode('utf-8', errors='ignore')
                if text and len(text) > 20:
                    result['analysis'] = {
                        'type': 'document',
                        'extracted_text': text,
                        'text_analysis': self._analyze_text(text)
                    }
            
            # Handle images
            else:
                image = Image.open(io.BytesIO(file_data))
                result['analysis'] = self._process_image(image, file_type)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filename': filename,
                'timestamp': datetime.now().isoformat()
            }
    
    def analyze_base64(self, base64_data: str, filename: str) -> Dict[str, Any]:
        """
        Analyze a medical file from base64 string
        
        Args:
            base64_data: Base64 encoded file data
            filename: Original filename
            
        Returns:
            JSON-serializable dict with analysis results
        """
        try:
            file_data = base64.b64decode(base64_data)
            return self.analyze_bytes(file_data, filename)
        except Exception as e:
            return {
                'success': False,
                'error': f'Base64 decode error: {str(e)}',
                'filename': filename,
                'timestamp': datetime.now().isoformat()
            }
    
    def _process_image(self, image: Image.Image, file_type: str) -> Dict[str, Any]:
        """Process medical image"""
        result = {
            'type': 'image',
            'subtype': file_type,
            'predictions': {},
            'extracted_text': None
        }
        
        # Try OCR first (might be a scanned report)
        if file_type == 'text_document':
            text = self.ocr_processor.extract_text_from_image(image)
            if text and len(text) > 50:
                result['extracted_text'] = text
                result['text_analysis'] = self._analyze_text(text)
                return result
        
        # Process as medical image
        if file_type == 'chest':
            img_tensor = self._preprocess_for_chest(image)
            if img_tensor is not None:
                preds = self._predict_chest(img_tensor)
                if preds:
                    result['predictions']['chest'] = preds
        
        elif file_type == 'brain':
            img_tensor = self._preprocess_for_brain_and_bones(image)
            if img_tensor is not None:
                preds = self._predict_brain(img_tensor)
                if preds:
                    result['predictions']['brain'] = preds
        
        elif file_type == 'bone':
            img_tensor = self._preprocess_for_brain_and_bones(image)
            if img_tensor is not None:
                preds = self._predict_fracture(img_tensor)
                if preds:
                    result['predictions']['fracture'] = preds
        
        # General analysis
        img_tensor_general = self._preprocess_for_brain_and_bones(image)
        if img_tensor_general is not None:
            general_preds = self._predict_general(img_tensor_general)
            if general_preds:
                result['predictions']['general'] = general_preds
        
        return result
    
    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze medical text"""
        analysis = {
            'entities': [],
            'severity': None,
            'lab_values': {},
            'summary': ''
        }
        
        # Extract medical entities
        entities = self.text_analyzer.extract_medical_entities(text)
        analysis['entities'] = entities
        
        # Determine severity
        severity, score = self.text_analyzer.analyze_severity(text)
        analysis['severity'] = {'level': severity, 'score': int(score)}
        
        # Extract lab values
        lab_values = self.text_analyzer.extract_lab_values(text)
        analysis['lab_values'] = lab_values
        
        # Create summary
        if entities:
            unique_conditions = list(set([e.get('entity', e.get('word', 'unknown')) for e in entities]))
            analysis['summary'] = f"Detected conditions: {', '.join(unique_conditions[:5])}"
        
        return analysis
    
    def _preprocess_for_chest(self, image: Image.Image, target_size=224):
        """Preprocess for chest models"""
        try:
            img = image.convert('L')
            img = img.resize((target_size, target_size), Image.LANCZOS)
            img_array = np.array(img, dtype=np.float32)
            
            if img_array.max() > 0:
                img_array = img_array / img_array.max()
            
            img_tensor = torch.from_numpy(img_array).unsqueeze(0).unsqueeze(0)
            return img_tensor.to(self.device)
        except:
            return None
    
    def _preprocess_for_brain_and_bones(self, image: Image.Image, target_size=224):
        """Preprocess for brain/bone models"""
        try:
            img = image.convert('RGB')
            transform = transforms.Compose([
                transforms.Resize((target_size, target_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            img_tensor = transform(img).unsqueeze(0)
            return img_tensor.to(self.device)
        except:
            return None
    
    def _predict_chest(self, image_tensor):
        """Predict chest conditions"""
        if self.models['chest_densenet'] is None:
            return None
        try:
            with torch.no_grad():
                img_224 = torch.nn.functional.interpolate(image_tensor, size=(224, 224), mode='bilinear', align_corners=False)
                densenet_out = self.models['chest_densenet'](img_224)
                densenet_probs = torch.sigmoid(densenet_out).cpu().numpy()[0]
                
                img_512 = torch.nn.functional.interpolate(image_tensor, size=(512, 512), mode='bilinear', align_corners=False)
                resnet_out = self.models['chest_resnet'](img_512)
                resnet_probs = torch.sigmoid(resnet_out).cpu().numpy()[0]
                
                predictions = {}
                for i, disease in enumerate(self.disease_mappings['chest']):
                    predictions[disease] = float((densenet_probs[i] + resnet_probs[i]) / 2.0)
                return predictions
        except:
            return None
    
    def _predict_brain(self, image_tensor):
        """Predict brain conditions"""
        if self.models['brain'] is None:
            return None
        try:
            with torch.no_grad():
                outputs = self.models['brain'](image_tensor)
                probs = torch.softmax(outputs, dim=1).cpu().numpy()[0]
                return {self.disease_mappings['brain'][i]: float(probs[i]) for i in range(len(probs))}
        except:
            return None
    
    def _predict_fracture(self, image_tensor):
        """Predict fractures"""
        if self.models['fracture'] is None:
            return None
        try:
            with torch.no_grad():
                outputs = self.models['fracture'](image_tensor)
                probs = torch.softmax(outputs, dim=1).cpu().numpy()[0]
                return {self.disease_mappings['fracture'][i]: float(probs[i]) for i in range(len(probs))}
        except:
            return None
    
    def _predict_general(self, image_tensor):
        """General predictions"""
        if self.models['general'] is None:
            return None
        try:
            with torch.no_grad():
                outputs = self.models['general'](image_tensor)
                probs = torch.softmax(outputs, dim=1).cpu().numpy()[0]
                return {self.disease_mappings['general'][i]: float(probs[i]) for i in range(len(probs))}
        except:
            return None