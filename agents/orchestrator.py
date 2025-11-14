# agents/orchestrator.py
"""
Multi-Agent Orchestrator with Diagnostic Indicators
"""

from typing import Dict, Any, List, Tuple
import re
import os

# Import agents
from agents.document_classifier import classify_document
from agents.bill_agent import extract_bill_full
from agents.discharge_agent import analyze_discharge_summary
from agents.missing_documents_agent import determine_missing_documents
from agents.coverage_agent import calculate_coverage
from agents.report_agent import build_claim_readiness_report
from utils.pdf_generator import generate_report_pdf, generate_claim_form_pdf

from policy_lookup import find_insurer  
from schemas.bill_schema import FullBillData


# -------------------------
# Helpers
# -------------------------
def try_extract_policy_number_from_text(text: str) -> str:
    m = re.search(r"(policy\s*(no|number)[:\s\-]*([A-Za-z0-9\/\-]+))", text, flags=re.I)
    if m:
        return m.group(3).strip()

    m2 = re.search(r"\b([A-Z0-9]{6,20})\b", text)
    if m2:
        return m2.group(1)
    return None


# -------------------------
# Main Pipeline
# -------------------------
def process_documents(doc_texts: Dict[str, str], generate_pdfs: bool = False, output_dir: str = ".") -> Dict[str, Any]:

    # ------------------------------------------------------------
    # DIAGNOSTIC FLAGS (NEW)
    # ------------------------------------------------------------
    diag = {
        "classifier": False,
        "bill_agent": False,
        "discharge_agent": False,
        "missing_docs_agent": False,
        "coverage_agent": False,
        "report_agent": False,
        "pdf_report": False,
        "pdf_form": False
    }

    # ------------------------------------------------------------
    # 1) CLASSIFICATION
    # ------------------------------------------------------------
    classified = {}
    uploaded_types: List[str] = []

    for fname, txt in doc_texts.items():
        res = classify_document(txt, debug=True)
        diag["classifier"] = True

        dtype = res.get("final_type", "unknown")
        classified[fname] = {"type": dtype, "debug": res, "text": txt}
        uploaded_types.append(dtype)

    uploaded_types = list(set(uploaded_types))

    # ------------------------------------------------------------
    # 2) ROUTE TO BILL AGENT
    # ------------------------------------------------------------
    bill_model = None
    bill_dict_partial = None
    admission_info = {}
    extracted_flags = {}

    for fname, meta in classified.items():
        if meta["type"] == "final_bill":
            try:
                bill_model = extract_bill_full(meta["text"])
                diag["bill_agent"] = True

                bill_dict_partial = (
                    bill_model.model_dump() if hasattr(bill_model, "model_dump") else bill_model.dict()
                )
                break
            except Exception:
                pass

    # Fallback using discharge summary
    if not bill_model:
        for fname, meta in classified.items():
            if meta["type"] == "discharge_summary":
                ds = analyze_discharge_summary(meta["text"])
                diag["discharge_agent"] = True  # because we used it

                tmp = {
                    "patient_details": {},
                    "hospital_details": {},
                    "admission_details": {
                        "admission_date": ds.get("admission_date"),
                        "discharge_date": ds.get("discharge_date"),
                        "diagnosis": ds.get("final_diagnosis") or ds.get("diagnosis"),
                        "is_accident_case": ds.get("is_accident_case"),
                        "is_surgical_case": ds.get("is_surgical_case"),
                        "is_maternity_case": ds.get("is_maternity_case"),
                    },
                    "legal_documents": {"mlc_required": ds.get("mlc_required", False)},
                    "billing_breakdown": {},
                    "payment_details": {},
                    "document_status": {"has_discharge_summary": True}
                }
                try:
                    bill_model = FullBillData(**tmp)
                    bill_dict_partial = (
                        bill_model.model_dump() if hasattr(bill_model, "model_dump") else bill_model.dict()
                    )
                except:
                    bill_model = None
                break

    # ------------------------------------------------------------
    # 3) DISCHARGE AGENT (when available)
    # ------------------------------------------------------------
    discharge_info = {}
    for fname, meta in classified.items():
        if meta["type"] == "discharge_summary":
            try:
                discharge_info = analyze_discharge_summary(meta["text"])
                diag["discharge_agent"] = True
                admission_info.update(discharge_info)
                extracted_flags["has_discharge_summary"] = True
                break
            except:
                pass

    # ------------------------------------------------------------
    # 4) POLICY LOOKUP
    # ------------------------------------------------------------
    policy_lookup_info = {"insurer_name": None, "features": None}
    found_policy_id = None

    for fname, meta in classified.items():
        if meta["type"] == "insurance_card":
            p = try_extract_policy_number_from_text(meta["text"])
            if p:
                found_policy_id = p

    if bill_dict_partial:
        p = bill_dict_partial.get("patient_details", {}).get("policy_number")
        found_policy_id = found_policy_id or p

    if found_policy_id:
        mapping = find_insurer(found_policy_id)
        if mapping:
            policy_lookup_info["insurer_name"] = mapping.get("insurer_name")
            policy_lookup_info["features"] = mapping.get("features")

    # ------------------------------------------------------------
    # 5) BUILD FULL BILL DATA
    # ------------------------------------------------------------
    if bill_model:
        full_bill_dict = (
            bill_model.model_dump() if hasattr(bill_model, "model_dump") else bill_model.dict()
        )
    else:
        full_bill_dict = bill_dict_partial or {
            "patient_details": {},
            "hospital_details": {},
            "admission_details": admission_info,
            "legal_documents": {},
            "billing_breakdown": {},
            "payment_details": {},
            "document_status": {}
        }

    # Add document flags
    doc_status = full_bill_dict.get("document_status", {})

    for fname, meta in classified.items():
        t = meta["type"]
        if t == "final_bill":
            doc_status["has_final_bill"] = True
        if t == "discharge_summary":
            doc_status["has_discharge_summary"] = True
        if t == "pharmacy_bill":
            doc_status["has_pharmacy_bills"] = True
        if t == "diagnostic_report":
            doc_status["has_diagnostic_reports"] = True
        if t == "prescription":
            doc_status["has_doctor_prescription"] = True
        if t == "mlc":
            doc_status["has_mlc"] = True
        if t == "fir":
            doc_status["has_fir"] = True
        if t == "payment_receipt":
            doc_status["has_payment_receipt"] = True

    full_bill_dict["document_status"] = doc_status

    uploaded_doc_types = list(set([meta["type"] for meta in classified.values()]))

    # ------------------------------------------------------------
    # 6) MISSING DOCUMENTS AGENT
    # ------------------------------------------------------------
    missing_result = determine_missing_documents(
        uploaded_docs=uploaded_doc_types,
        admission_info=full_bill_dict.get("admission_details", {}),
        extracted_status_flags=full_bill_dict.get("document_status", {})
    )
    diag["missing_docs_agent"] = True

    # ------------------------------------------------------------
    # 7) COVERAGE AGENT
    # ------------------------------------------------------------
    try:
        fb_obj = FullBillData(**full_bill_dict)
    except:
        fb_obj = FullBillData()

    coverage_result = calculate_coverage(fb_obj, policy_lookup_info.get("features") or {})
    diag["coverage_agent"] = True

    # ------------------------------------------------------------
    # 8) REPORT AGENT
    # ------------------------------------------------------------
    report = build_claim_readiness_report(full_bill_dict, coverage_result, policy_lookup_info)
    diag["report_agent"] = True

    # ------------------------------------------------------------
    # 9) PDF GENERATION
    # ------------------------------------------------------------
    generated = {}

    if generate_pdfs:
        os.makedirs(output_dir, exist_ok=True)

        report_pdf_path = os.path.join(output_dir, "claim_report.pdf")
        form_pdf_path = os.path.join(output_dir, "pre_filled_claim_form.pdf")

        # Report PDF
        try:
            generate_report_pdf(report, report_pdf_path)
            diag["pdf_report"] = True
        except Exception as e:
            diag["pdf_report"] = f"ERROR: {e}"

        # Claim Form PDF
        try:
            generate_claim_form_pdf(full_bill_dict, form_pdf_path)
            diag["pdf_form"] = True
        except Exception as e:
            diag["pdf_form"] = f"ERROR: {e}"

        generated["report_pdf"] = report_pdf_path
        generated["claim_form_pdf"] = form_pdf_path

    # ------------------------------------------------------------
    # Return complete result
    # ------------------------------------------------------------
    return {
        "classified": classified,
        "uploaded_doc_types": uploaded_doc_types,
        "policy_lookup": policy_lookup_info,
        "missing_documents": missing_result,
        "coverage_result": coverage_result,
        "report": report,
        "generated_pdfs": generated,
        "diagnostics": diag
    }


# FastAPI
def _fastapi_app():
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except:
        return None

    app = FastAPI(title="Insurance Agent Orchestrator")

    class ProcessRequest(BaseModel):
        files: Dict[str, str]
        generate_pdfs: bool = False

    @app.post("/process")
    def process(req: ProcessRequest):
        try:
            return process_documents(req.files, generate_pdfs=req.generate_pdfs)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app

app = _fastapi_app()


if __name__ == "__main__":
    samples = {
        "bill.txt": """FINAL BILL
Hospital Name: Apollo Hospitals
Invoice No: INV-1234
Room Charges      Qty  Rate    Amount
Room Rent              3,000   15,000
Doctor Fees            8,000
Pharmacy               1,200
Grand Total: ₹24,200
""",
        "discharge.txt": """DISCHARGE SUMMARY
Admission Date: 12/11/2025
Discharge Date: 14/11/2025
Final Diagnosis: RTA with Fracture
Procedure: ORIF Surgery
Doctor: Dr Arun
MLC No: MLC-5566
FIR No: FIR-9988
""",
        "insurance_card.txt": """HEALTH INSURANCE CARD
Policy No: 4071123456
Member ID: M-9988
Insurer: HDFC ERGO
"""
    }

    out = process_documents(samples, generate_pdfs=True)
    import json
    print(json.dumps(out, indent=2))
