# agents/ocr_agent.py
"""
OCR AGENT (Tesseract + PDFMiner Hybrid)
---------------------------------------
✓ Works on macOS
✓ Works for vector PDFs (extract text)
✓ Works for scanned PDFs (Tesseract OCR)
✓ Handles Indian hospital fonts
✓ Prevents garbage output
"""

import os
import re
import numpy as np
from typing import Dict, Any

from pdf2image import convert_from_path
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import pytesseract
from pdfminer.high_level import extract_text as pdf_text


# ------------------------------------------------------------
# Clean extracted text
# ------------------------------------------------------------
def clean_text(text: str) -> str:
    text = text.replace("\x0c", " ")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


# ------------------------------------------------------------
# Detect if PDF has selectable text (vector PDF)
# ------------------------------------------------------------
def pdf_has_text(path: str) -> bool:
    try:
        txt = pdf_text(path)
        return len(txt.strip()) > 10
    except:
        return False


# ------------------------------------------------------------
# Image enhancement to improve OCR
# ------------------------------------------------------------
def enhance_image(img: Image.Image) -> Image.Image:
    img = img.convert("L")  # grayscale
    img = img.filter(ImageFilter.MedianFilter())
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageEnhance.Sharpness(img).enhance(1.8)
    return img


# ------------------------------------------------------------
# OCR using Tesseract
# ------------------------------------------------------------
def tesseract_ocr(img: Image.Image) -> str:
    config = "--psm 6 --oem 1 -l eng+equ"
    return pytesseract.image_to_string(img, config=config)


# ------------------------------------------------------------
# OCR for scanned PDF
# ------------------------------------------------------------
def ocr_pdf(path: str) -> str:
    pages = convert_from_path(path, dpi=300)
    final_text = []

    for idx, pg in enumerate(pages, start=1):
        print(f"--- OCR Page {idx} ---")
        pg = enhance_image(pg)
        text = tesseract_ocr(pg)
        print(text)
        final_text.append(text)

    return "\n".join(final_text)


# ------------------------------------------------------------
# Main extract_text() function
# ------------------------------------------------------------
# ------------------------------------------------------------
# Main extract_text() function WITH PRINTING
# ------------------------------------------------------------
def extract_text(file_path: str) -> Dict[str, Any]:
    print(f"\nOCR Agent: Processing {file_path}")

    ext = file_path.lower()

    # -------------- PDF --------------
    if ext.endswith(".pdf"):
        if pdf_has_text(file_path):
            print("Vector PDF detected → Extracting text with PDFMiner")
            raw_text = pdf_text(file_path)
        else:
            print("Scanned PDF detected → Using Tesseract OCR")
            raw_text = ocr_pdf(file_path)

        cleaned = clean_text(raw_text)

        print("\n================ OCR EXTRACTED TEXT ================")
        print(cleaned if cleaned.strip() else "(No text extracted)")
        print("====================================================\n")

        return {
            "filename": os.path.basename(file_path),
            "text": cleaned
        }

    # -------------- IMAGE --------------
    try:
        img = Image.open(file_path)
        img = enhance_image(img)
        raw_text = tesseract_ocr(img)
        cleaned = clean_text(raw_text)

        print("\n================ OCR EXTRACTED TEXT ================")
        print(cleaned if cleaned.strip() else "(No text extracted)")
        print("====================================================\n")

        return {
            "filename": os.path.basename(file_path),
            "text": cleaned
        }

    except Exception as e:
        print(f"ERROR in OCR: {e}")

        return {
            "filename": os.path.basename(file_path),
            "text": "",
            "error": str(e)
        }

