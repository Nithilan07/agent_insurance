# agents/missing_documents_agent.py

"""
UPGRADED + HARDENED Missing Documents Agent
-------------------------------------------
Handles:
 - accident
 - surgery / OT
 - ICU
 - maternity
 - identity proofs
 - hospital legal docs
 - implant docs
 - pre/post hospitalization docs
 - null safety (no crashes)
"""

from typing import Dict, List, Any


# --------------------------------
# Document Types (Extended)
# --------------------------------
CORE_REQUIRED = [
    "insurance_card",
    "final_bill",
    "discharge_summary",
    "payment_receipt",
]

OPTIONAL_DOCS = [
    "pharmacy_bill",
    "diagnostic_report",
    "prescription",
]

ACCIDENT_DOCS = [
    "mlc",
    "fir",
    "injury_certificate",
]

SURGERY_DOCS = [
    "ot_summary",
    "anaesthesia_notes",
    "consent_form",
    "implant_bill",
]

ICU_DOCS = [
    "icu_flow_chart",
    "ventilator_logs",
    "nursing_notes",
]

MATERNITY_DOCS = [
    "delivery_notes",
    "newborn_records",
]

IDENTITY_DOCS = [
    "aadhaar",
    "pan",
    "employee_id",
]

HOSPITAL_LEGAL_DOCS = [
    "hospital_registration_certificate",
    "doctor_registration_number",
]

PRE_POST_REQUIRED = [
    "pre_hospitalization_bills",
    "post_hospitalization_bills",
]


# --------------------------------
# Main Function
# --------------------------------

def determine_missing_documents(
    uploaded_docs: List[str],
    admission_info: Dict[str, Any] = None,
    extracted_status_flags: Dict[str, bool] = None
) -> Dict[str, Any]:

    # Null safety
    uploaded_docs = uploaded_docs or []
    admission_info = admission_info or {}
    extracted_status_flags = extracted_status_flags or {}

    required = set(CORE_REQUIRED)
    recommended = []

    # Null-safe booleans
    is_accident = bool(admission_info.get("is_accident_case", False))
    is_surgical = bool(admission_info.get("is_surgical_case", False))
    is_maternity = bool(admission_info.get("is_maternity_case", False))

    # Null-safe treatment_type
    treatment_type = admission_info.get("treatment_type") or ""
    treatment_type = str(treatment_type).lower()

    is_icu = "icu" in treatment_type

    # --------------------------------
    # Case-based dynamic requirements
    # --------------------------------
    if is_accident:
        required.update(ACCIDENT_DOCS)
        recommended.append(
            "Since this is an accident, MLC, FIR, and Injury Certificate are required."
        )

    if is_surgical:
        required.update(SURGERY_DOCS)
        recommended.append(
            "Since surgery was performed, OT notes, anaesthesia notes, implant bills, and consent forms are required."
        )

    if is_icu:
        required.update(ICU_DOCS)
        recommended.append(
            "ICU case detected — ICU flow chart, nursing notes, and ventilator logs are required."
        )

    if is_maternity:
        required.update(MATERNITY_DOCS)
        recommended.append(
            "Maternity case — upload delivery notes and newborn records."
        )

    # Identity + hospital legal docs (only if not already added)
    if IDENTITY_DOCS:
        required.update(IDENTITY_DOCS)
        recommended.append("Identity proofs (Aadhaar / PAN) ensure insurer validation.")

    if HOSPITAL_LEGAL_DOCS:
        required.update(HOSPITAL_LEGAL_DOCS)

    # Pre & Post hospitalization bills (only if not already added)
    if PRE_POST_REQUIRED:
        required.update(PRE_POST_REQUIRED)
        recommended.append(
            "Upload pre-hospitalization (30 days) and post-hospitalization (60 days) bills for full coverage."
        )

    # --------------------------------
    # Check missing docs
    # --------------------------------
    uploaded_set = set(uploaded_docs)
    missing = [doc for doc in required if doc not in uploaded_set]

    # --------------------------------
    # Check extracted status flags (null-safe)
    # --------------------------------
    map_status = {
        "has_final_bill": "final_bill",
        "has_discharge_summary": "discharge_summary",
        "has_payment_receipt": "payment_receipt",
        "has_pharmacy_bills": "pharmacy_bill",
        "has_diagnostic_reports": "diagnostic_report",
        "has_doctor_prescription": "prescription",
        "has_mlc": "mlc",
        "has_fir": "fir",
    }

    for flag, doc_type in map_status.items():
        val = extracted_status_flags.get(flag)
        # Only add missing if explicitly false
        if val is False:
            if doc_type not in missing:
                missing.append(doc_type)

    # --------------------------------
    # Optional docs
    # --------------------------------
    optional_missing = [d for d in OPTIONAL_DOCS if d not in uploaded_set]

    # --------------------------------
    # Final recommendations
    # --------------------------------
    if missing:
        recommended.append(
            "Upload missing mandatory documents to avoid claim rejection."
        )

    recommended.append(
        "Submit clear scans — insurers reject blurred or incomplete documents."
    )

    return {
        "required_docs": sorted(required),
        "uploaded_docs": sorted(uploaded_set),
        "missing_docs": sorted(set(missing)),
        "optional_docs": optional_missing,
        "recommended_actions": recommended
    }
