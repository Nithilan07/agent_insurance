# agents/report_agent.py
from typing import Dict, Any
from datetime import date

def build_claim_readiness_report(full_bill: Dict[str, Any], coverage_result: Dict[str, Any], policy_lookup: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a final claim readiness report combining:
      - extracted bill/discharge data (full_bill)
      - coverage calculation result (coverage_result)
      - policy/features used (policy_lookup)
    Returns a serializable dict with summary, verdict, reasons and next steps.
    """

    report_date = date.today().isoformat()

    # High-level summary
    totals = coverage_result.get("totals", {})
    verdict = coverage_result.get("verdict", "Unknown")
    reasons = coverage_result.get("reasons", []) or []
    recommended = coverage_result.get("recommended_actions", []) or []

    # Compose patient & hospital brief
    patient = full_bill.get("patient_details", {}) or {}
    hosp = full_bill.get("hospital_details", {}) or {}
    admission = full_bill.get("admission_details", {}) or {}

    summary = {
        "report_date": report_date,
        "patient_name": patient.get("patient_name"),
        "policy_number": patient.get("policy_number") or patient.get("insurance_id"),
        "insurer_guess": policy_lookup.get("insurer_name") if policy_lookup else None,
        "hospital": hosp.get("hospital_name"),
        "admission_date": admission.get("admission_date"),
        "discharge_date": admission.get("discharge_date"),
        "diagnosis": admission.get("diagnosis"),
    }

    # Financial summary
    financial = {
        "total_bill_amount": totals.get("total_bill_amount"),
        "total_payable_before_copay": totals.get("total_payable_before_copay"),
        "co_pay_amount": totals.get("co_pay_amount"),
        "final_insurance_payable": totals.get("final_insurance_payable"),
        "user_payable_estimate": totals.get("user_payable_estimate"),
    }

    # Build concise human verdict message
    if verdict == "Eligible":
        human_verdict = "Your claim appears eligible. Submit the highlighted documents to proceed."
    elif verdict.startswith("Eligible -"):
        human_verdict = "Partially ready: some documents or fields are missing. Please upload the flagged items."
    elif verdict.startswith("May be Rejected"):
        human_verdict = "This claim may be rejected or needs manual review. See reasons and recommended actions below."
    else:
        human_verdict = "Review required."

    # Which documents are missing (from full_bill document_status)
    doc_status = full_bill.get("document_status", {}) or {}
    missing_docs = []
    # map flags to friendly names
    map_flags = {
        "has_final_bill": "Final Hospital Bill",
        "has_discharge_summary": "Discharge Summary",
        "has_payment_receipt": "Payment Receipt",
        "has_pharmacy_bills": "Pharmacy Bills",
        "has_diagnostic_reports": "Diagnostic Reports",
        "has_doctor_prescription": "Doctor Prescription",
        "has_mlc": "Medical Legal Certificate (MLC)",
        "has_fir": "Police FIR"
    }
    for k, friendly in map_flags.items():
        if not doc_status.get(k, False):
            missing_docs.append(friendly)

    # consolidated report
    report = {
        "summary": summary,
        "financial_summary": financial,
        "breakdown": coverage_result.get("breakdown"),
        "verdict": verdict,
        "human_verdict": human_verdict,
        "reasons": reasons,
        "recommended_actions": recommended,
        "missing_documents": missing_docs,
        "policy_features_used": coverage_result.get("policy_features_used"),
        "raw_coverage_result": coverage_result,
        "raw_extracted_bill": full_bill
    }

    return report
