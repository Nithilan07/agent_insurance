# agents/document_classifier.py
"""
Ultimate Document Classifier (Levels 1-4 combined, Option C output)

Outputs a detailed debug-style result with:
 - final_type
 - confidence
 - scores (per type normalized 0..1)
 - matched_keywords, matched_headers, matched_structural_features
 - top_3 predictions

Designed for medical/insurance documents:
 - final_bill, discharge_summary, diagnostic_report, pharmacy_bill,
   prescription, insurance_card, mlc, fir, payment_receipt, unknown
"""

import re
from typing import Dict, List, Any
from collections import defaultdict, Counter
import math

# ----------------------------
# Configuration: weighted keywords
# ----------------------------
# For each document type we define HIGH / MEDIUM / LOW impact keywords (Level 1/3)
KEYWORDS = {
    "final_bill": {
        "high": ["final bill", "grand total", "amount payable", "hospital bill", "invoice", "bill no", "tax", "gst"],
        "medium": ["amount", "total amount", "invoice no", "item", "qty", "rate", "amount paid"],
        "low": ["service charge", "room rent", "doctor fees", "consultation"]
    },
    "discharge_summary": {
        "high": ["discharge summary", "final diagnosis", "condition at discharge", "hospital course", "treatment given", "advice on discharge"],
        "medium": ["history of present illness", "course in hospital", "condition on discharge", "medication on discharge"],
        "low": ["follow up", "follow-up", "discharge instructions"]
    },
    "diagnostic_report": {
        "high": ["lab report", "investigation report", "radiology report", "impression", "findings", "test result", "reference range"],
        "medium": ["hemoglobin", "wbc", "platelets", "creatinine", "cbc", "glucose", "report no"],
        "low": ["sample collected", "collection date", "performed by"]
    },
    "pharmacy_bill": {
        "high": ["pharmacy", "mrp", "batch no", "expiry", "strip", "tablet", "medicine", "pharma bill"],
        "medium": ["qty", "mrp", "selling price", "pharmacist"],
        "low": ["prescribed by", "mfg", "manufacturer"]
    },
    "prescription": {
        "high": ["prescription", "rx", "sig", "take", "tablet", "mg", "dosage"],
        "medium": ["dated", "consultant", "regn no", "signature"],
        "low": ["dispense", "refill"]
    },
    "insurance_card": {
        "high": ["policy no", "insurance id", "member id", "tpa", "validity", "sum insured"],
        "medium": ["insurer", "group id", "plan", "cover"],
        "low": ["customer care", "claim", "telephone"]
    },
    "mlc": {
        "high": ["mlc", "medico legal", "medico-legal", "medico legal case", "injury details"],
        "medium": ["casualty", "police intimation", "legal case"],
        "low": ["legal", "medico"]
    },
    "fir": {
        "high": ["fir", "first information report", "police station", "complaint no"],
        "medium": ["investigation", "registered", "case no"],
        "low": ["offence", "section"]
    },
    "payment_receipt": {
        "high": ["receipt", "amount paid", "payment received", "transaction id", "payment mode"],
        "medium": ["ref no", "paid on", "paid by"],
        "low": ["receipt no", "cashier"]
    }
}

# ----------------------------
# Level 2: headers/section tokens typical for document types
# ----------------------------
HEADERS = {
    "discharge_summary": ["history of present illness", "hospital course", "treatment given", "condition at discharge", "discharge instructions", "final diagnosis", "advice on discharge"],
    "diagnostic_report": ["findings:", "impression:", "report:", "investigation report", "technique:"],
    "final_bill": ["description", "amount", "grand total", "invoice", "bill no", "amount payable"],
    "pharmacy_bill": ["m.r.p", "batch no", "expiry", "qty", "mrp", "pharmacy"],
    "prescription": ["rx", "prescription", "sig:", "take", "dosage"],
    "insurance_card": ["policy no", "member id", "insurance id", "tpa", "validity"],
    "mlc": ["mlc no", "medico legal", "medico-legal", "casualty"],
    "fir": ["fir no", "first information report", "police station"],
    "payment_receipt": ["receipt no", "amount paid", "transaction id", "payment mode"]
}

# ----------------------------
# Level 4: structural detectors - functions that inspect text shapes
# ----------------------------

def has_table_like_structure(text: str) -> bool:
    """
    Detect presence of table-like rows (multiple lines with numbers/amounts).
    Heuristic: many lines containing amounts and 2+ whitespace-separated tokens.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    count = 0
    for ln in lines:
        # detect currency/amount patterns
        if re.search(r"₹\s*\d|[0-9]{1,3}(?:,\d{3})+", ln) or re.search(r"\btotal\b", ln, flags=re.I):
            # detect columns by presence of multiple tokens separated by two or more spaces or multiple columns via tabs
            if re.search(r"\s{2,}|\t|\s+\|\s+", ln) or len(ln.split()) >= 3:
                count += 1
    return count >= 3  # threshold

def has_lab_value_pattern(text: str) -> bool:
    """
    Detect laboratory value patterns like 'Hemoglobin: 13.1 g/dL' or 'Hb 13.1 g/dL' or numbers + reference ranges.
    """
    # common lab analytes and value formats
    patterns = [
        r"\b(?:hb|hemoglobin)\b\s*[:\-]?\s*\d+(\.\d+)?",
        r"\b(?:wbc|rbc|platelet|platelets)\b\s*[:\-]?\s*\d+",
        r"\b\d+(\.\d+)?\s*(g\/dl|mg\/dl|mmol\/l)\b",
        r"\b(?:reference range|normal range|ref range)\b"
    ]
    for p in patterns:
        if re.search(p, text, flags=re.I):
            return True
    return False

def is_short_card_like(text: str) -> bool:
    """
    Insurance cards are short, blocky lines with tokens like policy no, member id, validity.
    Heuristic: <= 20 lines, presence of policy/member, few long paragraphs.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) > 20:
        return False
    has_policy = any(re.search(r"policy\s*no|policy number|insurance id|member id", ln, flags=re.I) for ln in lines)
    many_short_lines = sum(1 for ln in lines if len(ln.split()) <= 6) >= max(1, len(lines)//2)
    return has_policy and many_short_lines

def has_rx_structure(text: str) -> bool:
    """
    Prescriptions are typically short, contain drug names with dosages and 'tab', 'mg', 'od', 'bd'.
    """
    if re.search(r"\b(mg|mcg|g|ml|tablet|tab|capsule|od|bd|tds|qid)\b", text, flags=re.I):
        # presence of doctor signature or reg no is stronger
        if re.search(r"signature|regn|reg no|dr\.", text, flags=re.I) or len(text.split()) < 400:
            return True
    return False

def has_pharmacy_table(text: str) -> bool:
    """
    Detect lists of medicine rows with qty and MRP
    """
    # look for MRP or "batch"
    if re.search(r"\bmrp\b|\bbatch\b|\bexpiry\b", text, flags=re.I):
        # and some numeric patterns
        if re.search(r"\bqty\b|\bpcs\b|\bx\b|\d+\s*x\s*\d+", text, flags=re.I):
            return True
    return False

def has_mlc_fir_structure(text: str) -> bool:
    """
    MLC/FIR often contain specific legal headings and police station names.
    """
    if re.search(r"\b(mlc no|medico[- ]legal|police station|fir no|first information report)\b", text, flags=re.I):
        return True
    return False

# ----------------------------
# Scoring helpers
# ----------------------------
WEIGHTS = {"high": 3.0, "medium": 1.5, "low": 0.5}

def score_by_keywords(text: str) -> Dict[str, float]:
    """
    Level 1 + Level 3: count matches for high/medium/low keywords and compute weighted score.
    Returns raw scores per doc type (not normalized).
    """
    text_low = text.lower()
    scores = {}
    matched = {dt: [] for dt in KEYWORDS.keys()}
    for doc_type, groups in KEYWORDS.items():
        s = 0.0
        hits = []
        for level, kws in groups.items():
            for kw in kws:
                # keyword may be a phrase; use word-boundary search
                if re.search(r"\b" + re.escape(kw) + r"\b", text_low, flags=re.I):
                    s += WEIGHTS[level]
                    hits.append((level, kw))
        scores[doc_type] = s
        matched[doc_type] = hits
    return scores, matched

def score_by_headers(text: str) -> Dict[str, float]:
    """
    Level 2: header/section detection. Each matched header gives +1 score.
    """
    text_low = text.lower()
    header_scores = {}
    header_hits = {}
    for doc_type, headers in HEADERS.items():
        s = 0.0
        hits = []
        for h in headers:
            if re.search(re.escape(h), text_low, flags=re.I):
                s += 1.0
                hits.append(h)
        header_scores[doc_type] = s
        header_hits[doc_type] = hits
    return header_scores, header_hits

def score_by_structure(text: str) -> Dict[str, float]:
    """
    Level 4: structural features. Each structural detector contributes to some document types.
    Returns scores mapping.
    """
    struct_scores = defaultdict(float)
    struct_hits = defaultdict(list)

    if has_table_like_structure(text):
        # strongly indicates final bill or pharmacy bill (tables of amounts)
        struct_scores["final_bill"] += 2.0
        struct_hits["final_bill"].append("table_like")
        struct_scores["pharmacy_bill"] += 1.0
        struct_hits["pharmacy_bill"].append("table_like")

    if has_lab_value_pattern(text):
        struct_scores["diagnostic_report"] += 2.0
        struct_hits["diagnostic_report"].append("lab_values")

    if is_short_card_like(text):
        struct_scores["insurance_card"] += 2.0
        struct_hits["insurance_card"].append("card_like")

    if has_rx_structure(text):
        struct_scores["prescription"] += 1.5
        struct_hits["prescription"].append("rx_structure")

    if has_pharmacy_table(text):
        struct_scores["pharmacy_bill"] += 2.0
        struct_hits["pharmacy_bill"].append("pharmacy_table")

    if has_mlc_fir_structure(text):
        struct_scores["mlc"] += 1.5
        struct_hits["mlc"].append("mlc_fir_tokens")
        struct_scores["fir"] += 1.2
        struct_hits["fir"].append("mlc_fir_tokens")

    # Payment receipt structural heuristics: 'Receipt' with txn id + amount
    if re.search(r"receipt\s+no|transaction id|amount paid", text, flags=re.I):
        struct_scores["payment_receipt"] += 1.5
        struct_hits["payment_receipt"].append("receipt_pattern")

    return struct_scores, struct_hits

# ----------------------------
# Main classifier function
# ----------------------------

def classify_document(text: str, debug: bool = True) -> Dict[str, Any]:
    """
    Classify the provided OCR/text into document types with detailed debug info.
    Returns a dictionary with:
      - final_type
      - confidence (0..1)
      - scores {doc_type: score}
      - top_3: list of {type, score}
      - matched_keywords, matched_headers, matched_structural_features (lists)
    """
    if not text or not text.strip():
        return {
            "final_type": "unknown",
            "confidence": 0.0,
            "scores": {},
            "top_3": [],
            "matched_keywords": [],
            "matched_headers": [],
            "matched_structures": []
        }

    text = text if isinstance(text, str) else str(text)
    # Run keyword scoring (L1+L3)
    kw_scores_raw, kw_matched = score_by_keywords(text)

    # Run header scoring (L2)
    header_scores_raw, header_matched = score_by_headers(text)

    # Run structural scoring (L4)
    struct_scores_raw, struct_matched = score_by_structure(text)

    # Combine scores with weights (tunable)
    # We'll give: keywords_weight = 0.6, headers_weight = 0.25, structure_weight = 0.15
    kw_w = 0.6
    header_w = 0.25
    struct_w = 0.15

    # Normalize raw kw scores by max observed to avoid domination
    max_kw = max(kw_scores_raw.values()) if kw_scores_raw else 1.0
    max_header = max(header_scores_raw.values()) if header_scores_raw else 1.0
    max_struct = max(struct_scores_raw.values()) if struct_scores_raw else 1.0

    combined_scores = {}
    combined_breakdown = {}

    for doc_type in set(list(KEYWORDS.keys()) + list(HEADERS.keys()) + list(struct_scores_raw.keys())):
        k = kw_scores_raw.get(doc_type, 0.0) / (max_kw or 1.0)
        h = header_scores_raw.get(doc_type, 0.0) / (max_header or 1.0)
        s = struct_scores_raw.get(doc_type, 0.0) / (max_struct or 1.0)
        combined = kw_w * k + header_w * h + struct_w * s
        combined_scores[doc_type] = combined
        combined_breakdown[doc_type] = {"kw_norm": k, "header_norm": h, "struct_norm": s, "combined": combined}

    # Normalize combined scores to 0..1
    max_comb = max(combined_scores.values()) if combined_scores else 0.0
    if max_comb > 0:
        for dt in combined_scores:
            combined_scores[dt] = combined_scores[dt] / max_comb

    # Prepare matched lists for debug
    matched_keywords = []
    for dt, hits in kw_matched.items():
        for level, kw in hits:
            matched_keywords.append({"doc_type": dt, "level": level, "keyword": kw})

    matched_headers = []
    for dt, hits in header_matched.items():
        for h in hits:
            matched_headers.append({"doc_type": dt, "header": h})

    matched_structures = []
    for dt, hits in struct_matched.items():
        for h in hits:
            matched_structures.append({"doc_type": dt, "feature": h})

    # Sort top 3
    sorted_types = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    top_3 = [{"type": t, "score": round(s, 4)} for t, s in sorted_types[:3]]

    final_type = top_3[0]["type"] if top_3 else "unknown"
    final_score = top_3[0]["score"] if top_3 else 0.0

    # If confidence is low (e.g., < 0.35) mark unknown
    confidence = float(final_score)
    if confidence < 0.20:
        final_type = "unknown"

    result = {
        "final_type": final_type,
        "confidence": round(confidence, 4),
        "scores": {k: round(v, 4) for k, v in combined_scores.items()},
        "breakdown": combined_breakdown,
        "top_3": top_3,
        "matched_keywords": matched_keywords,
        "matched_headers": matched_headers,
        "matched_structures": matched_structures
    }

    if debug:
        return result
    else:
        # minimal output
        return {
            "final_type": result["final_type"],
            "confidence": result["confidence"]
        }


# ----------------------------
# Quick CLI test
# ----------------------------
if __name__ == "__main__":
    samples = {
        "bill": """FINAL BILL
Hospital Name: Apollo Hospitals
Invoice No: INV-1234
Room Charges      Qty  Rate    Amount
Room Rent              3,000   15,000
Doctor Fees            8,000
Pharmacy               1,200
Grand Total: ₹24,200""",

        "discharge": """DISCHARGE SUMMARY
Hospital Course:
The patient presented with acute abdomen...
Final Diagnosis: Acute appendicitis
Treatment Given: Appendectomy performed.
Condition at discharge: Stable. Advice on discharge: Use antibiotics for 5 days.
Doctor: Dr. X""",

        "lab": """LAB REPORT
Test Name       Result       Reference Range
Hemoglobin      13.1 g/dL    12.0 - 16.0
WBC             8.1 x10^3/uL 4.0 - 11.0
Impression: All within normal limits""",

        "pharmacy": """PHARMACY BILL
Invoice: PH-9988
Medicine Name   Batch   Qty  MRP    Amount
Paracetamol     B123    10   12.00  120.00
Antibiotic      A222    7    35.00  245.00
Total MRP: 365.00""",

        "insurance_card": """HEALTH INSURANCE CARD
Insurer: HDFC ERGO
Policy No: 4071123456
Member ID: M-9988
Validity: 01-01-2025 to 31-12-2025
TPA: MediAssist""",

        "mlc": """MEDICO-LEGAL CASE REPORT (MLC)
MLC No: MLC-5566
Patient brought to casualty after road traffic accident.
Injury details: fracture left leg.
Police intimated: Yes.""",

        "receipt": """PAYMENT RECEIPT
Receipt No: R-778899
Amount Paid: ₹12,345
Transaction ID: TXN998877
Payment Mode: CARD"""
    }

    for name, txt in samples.items():
        print("\n\n=== SAMPLE:", name.upper(), "===")
        out = classify_document(txt, debug=True)
        import json
        print(json.dumps(out, indent=2))
