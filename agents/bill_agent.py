import re
from schemas.bill_schema import FullBillData

# ----------------------------------------------------
# Generic field extractor
# ----------------------------------------------------
def extract_field(patterns, text):
    """Try multiple regex patterns and return the first matched value."""
    for pat in patterns:
        try:
            match = re.search(pat, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        except:
            continue
    return None


# ----------------------------------------------------
# Safe money extractor
# ----------------------------------------------------
def money(pattern, text):
    """
    Extract currency amounts safely.
    Accepts grouped OR patterns like: (room rent|room charges|room)
    """
    try:
        pat = rf"{pattern}[:\-]?\s*₹?\s*([0-9,]+)"
        match = re.search(pat, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).replace(",", "").strip()
        return None
    except:
        return None


# ----------------------------------------------------
# Extract full bill details
# ----------------------------------------------------
def extract_bill_full(text: str) -> FullBillData:
    data = FullBillData()
    lower = text.lower()

    # ============================================================
    # PATIENT DETAILS
    # ============================================================
    data.patient_details.patient_name = extract_field([
        r"patient\s*name[:\-]\s*(.+)",
        r"name of patient[:\-]\s*(.+)"
    ], text)

    data.patient_details.patient_age = extract_field([
        r"age[:\-]\s*([\d]+)"
    ], text)

    data.patient_details.patient_gender = extract_field([
        r"gender[:\-]\s*(male|female|other)"
    ], text)

    data.patient_details.uhid_number = extract_field([
        r"uhid[:\-]\s*(.+)"
    ], text)

    data.patient_details.ip_number = extract_field([
        r"(ip no|ip number)[:\-]\s*(.+)"
    ], text)

    data.patient_details.policy_number = extract_field([
        r"policy\s*no[:\-]\s*(.+)"
    ], text)

    data.patient_details.insurance_id = extract_field([
        r"insurance\s*id[:\-]\s*(.+)"
    ], text)

    # ============================================================
    # HOSPITAL DETAILS
    # ============================================================
    data.hospital_details.hospital_name = extract_field([
        r"hospital\s*name[:\-]\s*(.+)"
    ], text)

    data.hospital_details.hospital_address = extract_field([
        r"address[:\-]\s*(.+)"
    ], text)

    data.hospital_details.tpa_name = extract_field([
        r"tpa[:\-]\s*(.+)",
        r"tpa name[:\-]\s*(.+)"
    ], text)

    # ============================================================
    # ADMISSION DETAILS
    # ============================================================
    data.admission_details.admission_date = extract_field([
        r"admission\s*date[:\-]\s*([0-9\/\-]+)"
    ], text)

    data.admission_details.discharge_date = extract_field([
        r"discharge\s*date[:\-]\s*([0-9\/\-]+)"
    ], text)

    data.admission_details.diagnosis = extract_field([
        r"diagnosis[:\-]\s*(.+)",
        r"provisional\s*diagnosis[:\-]\s*(.+)"
    ], text)

    # Auto-detect accident cases
    accident_keywords = ["accident", "injury", "trauma", "rta", "burns", "assault"]
    data.admission_details.is_accident_case = any(k in lower for k in accident_keywords)

    # Auto-detect maternity cases
    maternity_keywords = ["delivery", "cesarean", "c-section", "labour", "maternity"]
    data.admission_details.is_maternity_case = any(k in lower for k in maternity_keywords)

    # Auto-detect surgical cases
    surgical_keywords = ["surgery", "surgeon", "operation", "ot"]
    data.admission_details.is_surgical_case = any(k in lower for k in surgical_keywords)

    # ============================================================
    # LEGAL DOCUMENTS
    # ============================================================
    data.legal_documents.mlc_required = data.admission_details.is_accident_case

    data.legal_documents.mlc_number = extract_field([
        r"mlc\s*no[:\-]\s*(.+)"
    ], text)

    data.legal_documents.police_fir_number = extract_field([
        r"fir\s*no[:\-]\s*(.+)"
    ], text)

    data.legal_documents.accident_date = extract_field([
        r"accident\s*date[:\-]\s*(.+)"
    ], text)

    data.legal_documents.accident_description = extract_field([
        r"accident\s*description[:\-]\s*(.+)"
    ], text)

    # ============================================================
    # BILLING BREAKDOWN
    # ============================================================
    b = data.billing_breakdown

    b.room_rent_per_day       = money("(room rent per day|room rent)", text)
    b.room_charges_total      = money("(room charges|room rent|room)", text)
    b.icu_charges             = money("(icu charges|icu)", text)
    b.nursing_charges         = money("(nursing charges|nursing)", text)
    b.doctor_fees             = money("(doctor fee|doctor fees|consultation)", text)
    b.consultation_fees       = money("(consultation)", text)
    b.visiting_specialist_fees = money("(visiting specialist|specialist)", text)
    b.surgeon_fees            = money("(surgeon fees|surgeon)", text)
    b.anaesthetist_fees       = money("(anaesthetist|anaesthesia)", text)
    b.ot_charges              = money("(ot charges|operation theatre|ot)", text)
    b.ot_consumables          = money("(ot consumables|consumables)", text)
    b.implant_costs           = money("(implant|implant cost)", text)

    b.pharmacy                = money("(pharmacy|medicine|medicines)", text)
    b.injection_charges       = money("(injection charges|injections)", text)

    b.diagnostics.lab_tests   = money("(lab tests|laboratory|labs)", text)
    b.diagnostics.radiology_tests = money("(radiology|xray|ct|mri|ultrasound)", text)
    b.diagnostics.ct_scan     = money("(ct scan)", text)
    b.diagnostics.mri_scan    = money("(mri)", text)
    b.diagnostics.xray        = money("(xray|x-ray)", text)
    b.diagnostics.ultrasound  = money("(ultrasound|usg)", text)

    b.ventilator_charges      = money("(ventilator)", text)
    b.oxygen_charges          = money("(oxygen)", text)
    b.blood_charges           = money("(blood)", text)
    b.ambulance_charges       = money("(ambulance)", text)
    b.service_charges         = money("(service charges|service)", text)
    b.registration_charges    = money("(registration)", text)
    b.misc_charges            = money("(misc|miscellaneous)", text)
    b.discounts               = money("(discount|concession)", text)
    b.non_payable_items_total = money("(non payable|non-payable)", text)
    b.payable_items_total     = money("(payable items|payable)", text)

    b.total_amount            = money("(total amount|grand total|amount payable)", text)

    # ============================================================
    # PAYMENT DETAILS
    # ============================================================
    p = data.payment_details

    p.paid_by_user = money("(paid by user|cash paid|amount paid)", text)
    p.paid_by_insurance = money("(paid by insurance|insurance paid)", text)

    p.payment_status = extract_field([
        r"payment\s*status[:\-]\s*(.+)"
    ], text)

    p.payment_mode = extract_field([
        r"payment\s*mode[:\-]\s*(.+)"
    ], text)

    p.receipt_number = extract_field([
        r"receipt\s*no[:\-]\s*(.+)"
    ], text)

    # ============================================================
    # DOCUMENT STATUS (auto-detect)
    # ============================================================
    d = data.document_status

    d.has_discharge_summary = "discharge summary" in lower
    d.has_final_bill = "final bill" in lower
    d.has_payment_receipt = "receipt" in lower
    d.has_pharmacy_bills = "pharmacy" in lower
    d.has_diagnostic_reports = "diagnostic" in lower or "lab" in lower
    d.has_doctor_prescription = "prescription" in lower
    d.has_mlc = "mlc" in lower
    d.has_fir = "fir" in lower

    return data
