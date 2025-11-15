import re
from typing import Dict, Any

def extract_field(patterns, text):
    """Try multiple regex patterns and return the first match."""
    for pat in patterns:
        match = re.search(pat, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def analyze_discharge_summary(text: str) -> Dict[str, Any]:
    lower = text.lower()

    # -------------------------
    # Extract main fields
    # -------------------------
    diagnosis = extract_field([
        r"diagnosis[:\-]\s*(.+)",
        r"final diagnosis[:\-]\s*(.+)",
        r"provisional diagnosis[:\-]\s*(.+)"
    ], text)

    final_diagnosis = extract_field([
        r"final diagnosis[:\-]\s*(.+)"
    ], text)

    procedure = extract_field([
        r"procedure[:\-]\s*(.+)",
        r"surgery performed[:\-]\s*(.+)"
    ], text)

    doctor_name = extract_field([
        r"doctor[:\-]\s*(.+)",
        r"consultant[:\-]\s*(.+)",
        r"attending physician[:\-]\s*(.+)"
    ], text)

    treatment_given = extract_field([
        r"treatment given[:\-]\s*(.+)"
    ], text)

    admission_date = extract_field([
        r"admission date[:\-]\s*([0-9\/\-]+)"
    ], text)

    discharge_date = extract_field([
        r"discharge date[:\-]\s*([0-9\/\-]+)"
    ], text)

    # -------------------------
    # Case-type detection
    # -------------------------
    accident_words = ["accident", "injury", "trauma", "rta", "fall", "burns", "assault"]
    is_accident_case = any(word in lower for word in accident_words)

    surgical_words = ["surgery", "operation", "ot", "procedure", "orif", "fixation"]
    is_surgical_case = any(word in lower for word in surgical_words)

    maternity_words = ["delivery", "labour", "cesarean", "c-section", "maternity"]
    is_maternity_case = any(word in lower for word in maternity_words)

    # -------------------------
    # MLC detection logic
    # -------------------------
    mlc_required = is_accident_case

    mlc_number = extract_field([
        r"mlc\s*no[:\-]\s*(.+)"
    ], text)

    fir_number = extract_field([
        r"fir\s*no[:\-]\s*(.+)"
    ], text)

    # -------------------------
    # PACKAGE ALL RESULTS
    # -------------------------
    return {
        "diagnosis": diagnosis,
        "final_diagnosis": final_diagnosis or diagnosis,
        "procedure": procedure,
        "doctor_name": doctor_name,
        "treatment_given": treatment_given,
        "admission_date": admission_date,
        "discharge_date": discharge_date,

        "is_accident_case": is_accident_case,
        "is_surgical_case": is_surgical_case,
        "is_maternity_case": is_maternity_case,
        "mlc_required": mlc_required,

        "mlc_number": mlc_number,
        "fir_number": fir_number,

        "summary_text": text  # keep original text
    }
