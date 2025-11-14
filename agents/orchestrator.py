"""
Multi-Agent Orchestrator with Document Quality Check and Diagnostic Indicators

Pipeline:
1. Document Quality Assessment (check clarity, alignment, readability)
2. Document Classification (only if quality check passes)
3. Specialized Agents (bill, discharge, missing docs, coverage)
4. Report Generation
"""

from typing import Dict, Any, List, Tuple
import re
import os
import base64

# Import agents
from agents.document_classifier import classify_document
from agents.bill_agent import extract_bill_full
from agents.discharge_agent import analyze_discharge_summary
from agents.missing_documents_agent import determine_missing_documents
from agents.coverage_agent import calculate_coverage
from agents.report_agent import build_claim_readiness_report
from utils.pdf_generator import generate_report_pdf, generate_claim_form_pdf

# Import quality assessment (function-based)
from agents.document_clarity import assess_quality_from_bytes

from policy_lookup import find_insurer  
from schemas.bill_schema import FullBillData


# -------------------------
# Configuration
# -------------------------
QUALITY_CONFIG = {
    'clarity_threshold': 0.75,  # Slightly lower for real-world documents
    'alignment_weight': 0.25,
    'clarity_weight': 0.40,
    'readability_weight': 0.35,
    'ai_penalty_weight': 0.10
}


# -------------------------
# Helpers
# -------------------------
def try_extract_policy_number_from_text(text: str) -> str:
    """Extract policy number from text."""
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
def process_documents(
    doc_data: Dict[str, Any],  # Changed to accept both text and bytes
    generate_pdfs: bool = False,
    output_dir: str = ".",
    skip_quality_check: bool = False
) -> Dict[str, Any]:
    print('Analyss started for documents:', list(doc_data.keys()))
    """
    Process documents through quality check, classification, and analysis pipeline.
    
    Args:
        doc_data: Dict with filenames as keys and values as either:
                  - str (extracted text)
                  - dict with {'text': str, 'bytes': bytes, 'filename': str}
        generate_pdfs: Whether to generate PDF reports
        output_dir: Output directory for PDFs
        skip_quality_check: Force skip quality assessment
        
    Returns:
        Complete analysis results with diagnostics
    """

    # ------------------------------------------------------------
    # DIAGNOSTIC FLAGS
    # ------------------------------------------------------------
    diag = {
        "quality_check": False,
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
    # 0) DOCUMENT QUALITY CHECK (NEW STEP)
    # ------------------------------------------------------------
    quality_results = {}
    doc_texts = {}  # Will store only quality-approved texts
    rejected_docs = {}
    
    print("\n" + "="*80)
    print("STEP 0: DOCUMENT QUALITY ASSESSMENT")
    print("="*80 + "\n")
    
    for fname, data in doc_data.items():
        try:
            # All documents MUST have bytes for quality check
            if isinstance(data, str):
                rejected_docs[fname] = {
                    "text": data,
                    "quality_result": None,
                    "reason": "No image data provided - quality check requires document bytes/image"
                }
                print(f"✗ {fname}: REJECTED - Text-only input (no image for quality check)")
                continue
            
            # Extract components
            text = data.get('text', '')
            file_bytes = data.get('bytes')
            original_filename = data.get('filename', fname)
            
            # Quality check is mandatory
            if not file_bytes:
                rejected_docs[fname] = {
                    "text": text,
                    "quality_result": None,
                    "reason": "No image/file bytes provided for quality assessment"
                }
                print(f"✗ {fname}: REJECTED - Missing file bytes")
                continue
            
            # Perform quality check
            quality_result = assess_quality_from_bytes(
                file_bytes, 
                original_filename, 
                config=QUALITY_CONFIG
            )
            
            quality_results[fname] = quality_result
            diag["quality_check"] = True
            
            # Check if document passes quality threshold
            if quality_result.get('success') and quality_result['decision']['acceptable']:
                doc_texts[fname] = text
                print(f"✓ {fname}: PASSED quality check")
                print(f"  Weighted Score: {quality_result['decision']['weighted_score']:.3f}")
                for metric, value in quality_result['aggregate_scores'].items():
                    indicator = "✓" if value > 0.5 else "✗"
                    print(f"    {indicator} {metric.capitalize():<15}: {value:.3f}")
            else:
                rejected_docs[fname] = {
                    "text": text,
                    "quality_result": quality_result,
                    "reason": "Failed quality assessment"
                }
                print(f"✗ {fname}: FAILED quality check")
                if quality_result.get('decision'):
                    print(f"  Weighted Score: {quality_result['decision']['weighted_score']:.3f}")
                    print(f"  Recommendations:")
                    for rec in quality_result['decision']['recommendations']:
                        print(f"    {rec}")
                    
        except Exception as e:
            print(f"⚠ {fname}: Quality check error: {str(e)}")
            diag["quality_check"] = f"ERROR on {fname}: {e}"
            rejected_docs[fname] = {
                "text": data.get('text', '') if isinstance(data, dict) else data,
                "quality_result": None,
                "reason": f"Quality check error: {str(e)}"
            }
            print(f"✗ {fname}: REJECTED due to error")


    # ------------------------------------------------------------
    # 1) CLASSIFICATION
    # ------------------------------------------------------------
    print("\n" + "="*80)
    print("STEP 1: DOCUMENT CLASSIFICATION")
    print("="*80 + "\n")
    
    classified = {}
    uploaded_types: List[str] = []

    try:
        for fname, txt in doc_texts.items():
            if not txt or not txt.strip():
                classified[fname] = {
                    "type": "unknown", 
                    "debug": {"error": "Empty text"}, 
                    "text": "",
                    "quality_passed": quality_results.get(fname, {}).get('decision', {}).get('acceptable', False)
                }
                uploaded_types.append("unknown")
                continue
            
            try:
                res = classify_document(txt, debug=True)
                diag["classifier"] = True

                dtype = res.get("final_type", "unknown")
                classified[fname] = {
                    "type": dtype, 
                    "debug": res, 
                    "text": txt,
                    "quality_passed": quality_results.get(fname, {}).get('decision', {}).get('acceptable', True)
                }
                uploaded_types.append(dtype)
                print(f"✓ {fname}: Classified as {dtype.upper()}")
                
            except Exception as e:
                classified[fname] = {
                    "type": "unknown", 
                    "debug": {"error": str(e)}, 
                    "text": txt,
                    "quality_passed": False
                }
                uploaded_types.append("unknown")
                print(f"✗ {fname}: Classification error: {str(e)}")
                
    except Exception as e:
        diag["classifier"] = f"ERROR: {e}"

    uploaded_types = list(set(uploaded_types))

    # ------------------------------------------------------------
    # 2) ROUTE TO BILL AGENT
    # ------------------------------------------------------------
    print("\n" + "="*80)
    print("STEP 2: BILL EXTRACTION")
    print("="*80 + "\n")
    
    bill_model = None
    bill_dict_partial = None
    admission_info = {}
    extracted_flags = {}

    for fname, meta in classified.items():
        if meta["type"] == "final_bill":
            try:
                bill_model = extract_bill_full(meta["text"])
                diag["bill_agent"] = True
                print(f"✓ Extracted bill data from {fname}")

                bill_dict_partial = (
                    bill_model.model_dump() if hasattr(bill_model, "model_dump") else bill_model.dict()
                )
                break
            except Exception as e:
                print(f"✗ Bill extraction failed: {str(e)}")

    # Fallback using discharge summary
    if not bill_model:
        print("  → Attempting fallback from discharge summary")
        for fname, meta in classified.items():
            if meta["type"] == "discharge_summary":
                try:
                    ds = analyze_discharge_summary(meta["text"])
                    diag["discharge_agent"] = True

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
                    bill_model = FullBillData(**tmp)
                    bill_dict_partial = (
                        bill_model.model_dump() if hasattr(bill_model, "model_dump") else bill_model.dict()
                    )
                    print(f"  ✓ Created bill data from discharge summary")
                except Exception as e:
                    bill_model = None
                    print(f"  ✗ Fallback failed: {str(e)}")
                break

    # ------------------------------------------------------------
    # 3) DISCHARGE AGENT (when available)
    # ------------------------------------------------------------
    print("\n" + "="*80)
    print("STEP 3: DISCHARGE SUMMARY ANALYSIS")
    print("="*80 + "\n")
    
    discharge_info = {}
    for fname, meta in classified.items():
        if meta["type"] == "discharge_summary":
            try:
                discharge_info = analyze_discharge_summary(meta["text"])
                diag["discharge_agent"] = True
                admission_info.update(discharge_info)
                extracted_flags["has_discharge_summary"] = True
                print(f"✓ Analyzed discharge summary from {fname}")
                break
            except Exception as e:
                print(f"✗ Discharge analysis failed: {str(e)}")

    # ------------------------------------------------------------
    # 4) POLICY LOOKUP
    # ------------------------------------------------------------
    print("\n" + "="*80)
    print("STEP 4: POLICY LOOKUP")
    print("="*80 + "\n")
    
    policy_lookup_info = {"insurer_name": None, "features": None}
    found_policy_id = None

    for fname, meta in classified.items():
        if meta["type"] == "insurance_card":
            p = try_extract_policy_number_from_text(meta["text"])
            if p:
                found_policy_id = p
                print(f"✓ Found policy number: {found_policy_id}")

    if bill_dict_partial:
        p = bill_dict_partial.get("patient_details", {}).get("policy_number")
        found_policy_id = found_policy_id or p

    if found_policy_id:
        mapping = find_insurer(found_policy_id)
        if mapping:
            policy_lookup_info["insurer_name"] = mapping.get("insurer_name")
            policy_lookup_info["features"] = mapping.get("features")
            print(f"  Insurer: {policy_lookup_info['insurer_name']}")

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
    print("\n" + "="*80)
    print("STEP 5: MISSING DOCUMENTS CHECK")
    print("="*80 + "\n")
    
    try:
        missing_result = determine_missing_documents(
            uploaded_docs=uploaded_doc_types,
            admission_info=full_bill_dict.get("admission_details", {}),
            extracted_status_flags=full_bill_dict.get("document_status", {})
        )
        diag["missing_docs_agent"] = True
        if missing_result.get("missing_docs"):
            print(f"⚠ Missing documents: {', '.join(missing_result['missing_docs'])}")
        else:
            print("✓ All required documents present")
    except Exception as e:
        diag["missing_docs_agent"] = f"ERROR: {e}"
        missing_result = {
            "required_docs": [],
            "uploaded_docs": uploaded_doc_types,
            "missing_docs": [],
            "optional_docs": [],
            "recommended_actions": [f"Error determining missing documents: {str(e)}"]
        }

    # ------------------------------------------------------------
    # 7) COVERAGE AGENT
    # ------------------------------------------------------------
    print("\n" + "="*80)
    print("STEP 6: COVERAGE CALCULATION")
    print("="*80 + "\n")
    
    try:
        fb_obj = FullBillData(**full_bill_dict)
    except Exception as e:
        diag["coverage_agent"] = f"WARNING: Bill data validation error: {e}"
        fb_obj = FullBillData()

    try:
        coverage_result = calculate_coverage(fb_obj, policy_lookup_info.get("features") or {})
        diag["coverage_agent"] = True
        print(f"✓ Coverage calculated")
        print(f"  Total Bill: ₹{coverage_result['totals']['total_bill_amount']:.2f}")
        print(f"  Insurance Payable: ₹{coverage_result['totals']['final_insurance_payable']:.2f}")
    except Exception as e:
        diag["coverage_agent"] = f"ERROR: {e}"
        coverage_result = {
            "policy_features_used": {},
            "totals": {
                "total_bill_amount": 0,
                "total_payable_before_copay": 0,
                "co_pay_amount": 0,
                "final_insurance_payable": 0,
                "user_payable_estimate": 0,
            },
            "breakdown": {},
            "reasons": [f"Error calculating coverage: {str(e)}"],
            "recommended_actions": ["Please check your documents and try again."],
            "verdict": "Error"
        }

    # ------------------------------------------------------------
    # 8) REPORT AGENT
    # ------------------------------------------------------------
    print("\n" + "="*80)
    print("STEP 7: REPORT GENERATION")
    print("="*80 + "\n")
    
    try:
        report = build_claim_readiness_report(full_bill_dict, coverage_result, policy_lookup_info)
        diag["report_agent"] = True
        print(f"✓ Report generated")
        print(f"  Verdict: {report.get('verdict', 'Unknown')}")
    except Exception as e:
        diag["report_agent"] = f"ERROR: {e}"
        report = {
            "summary": {},
            "financial_summary": {},
            "breakdown": {},
            "verdict": "Error",
            "human_verdict": f"Error generating report: {str(e)}",
            "reasons": [f"Report generation error: {str(e)}"],
            "recommended_actions": ["Please try again or contact support."],
            "missing_documents": [],
            "policy_features_used": {}
        }

    # ------------------------------------------------------------
    # 9) PDF GENERATION
    # ------------------------------------------------------------
    generated = {}

    if generate_pdfs:
        print("\n" + "="*80)
        print("STEP 8: PDF GENERATION")
        print("="*80 + "\n")
        
        os.makedirs(output_dir, exist_ok=True)

        report_pdf_path = os.path.join(output_dir, "claim_report.pdf")
        form_pdf_path = os.path.join(output_dir, "pre_filled_claim_form.pdf")

        # Report PDF
        try:
            generate_report_pdf(report, report_pdf_path)
            diag["pdf_report"] = True
            print(f"✓ Report PDF: {report_pdf_path}")
        except Exception as e:
            diag["pdf_report"] = f"ERROR: {e}"
            print(f"✗ Report PDF failed: {str(e)}")

        # Claim Form PDF
        try:
            generate_claim_form_pdf(full_bill_dict, form_pdf_path)
            diag["pdf_form"] = True
            print(f"✓ Claim Form PDF: {form_pdf_path}")
        except Exception as e:
            diag["pdf_form"] = f"ERROR: {e}"
            print(f"✗ Claim Form PDF failed: {str(e)}")

        generated["report_pdf"] = report_pdf_path
        generated["claim_form_pdf"] = form_pdf_path

    # ------------------------------------------------------------
    # Return complete result
    # ------------------------------------------------------------
    print("\n" + "="*80)
    print("PIPELINE COMPLETE")
    print("="*80 + "\n")
    
    return {
        "status": "success",
        "quality_results": quality_results,
        "rejected_documents": rejected_docs,
        "classified": classified,
        "uploaded_doc_types": uploaded_doc_types,
        "policy_lookup": policy_lookup_info,
        "missing_documents": missing_result,
        "coverage_result": coverage_result,
        "report": report,
        "generated_pdfs": generated,
        "diagnostics": diag
    }


# -------------------------
# FastAPI Integration
# -------------------------
def _fastapi_app():
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except:
        return None

    app = FastAPI(title="Insurance Agent Orchestrator with Quality Check")

    class ProcessRequest(BaseModel):
        files: Dict[str, Any]  # Can be text or dict with text+bytes
        generate_pdfs: bool = False
        skip_quality_check: bool = False

    @app.post("/process")
    def process(req: ProcessRequest):
        try:
            return process_documents(
                req.files, 
                generate_pdfs=req.generate_pdfs,
                skip_quality_check=req.skip_quality_check
            )
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
