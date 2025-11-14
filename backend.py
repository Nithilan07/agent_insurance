# backend.py
"""
FULL FASTAPI BACKEND FOR INSURANCE PIPELINE
-------------------------------------------
✓ Accepts PDF/Image uploads
✓ Runs OCR using agents/ocr_agent.py
✓ Runs orchestration pipeline
✓ Generates Claim Report + Pre-Filled Claim Form PDFs
✓ Provides download links for generated PDFs
"""

import os
import uuid
import shutil
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Import your agents
from agents.ocr_agent import extract_text
from agents.orchestrator import process_documents

# Directories for storage
BASE_UPLOAD = "uploaded_files"
BASE_OUTPUT = "generated_outputs"

os.makedirs(BASE_UPLOAD, exist_ok=True)
os.makedirs(BASE_OUTPUT, exist_ok=True)

app = FastAPI(title="Health Insurance AI Agent Backend")

# Allow all origins (adjust this later for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# -----------------------------------------------------------
# ROUTE: PROCESS DOCUMENTS (UPLOAD → OCR → ORCHESTRATOR)
# -----------------------------------------------------------
@app.post("/process")
async def process_insurance_documents(
    files: List[UploadFile] = File(...),
    generate_pdfs: bool = Form(True)
):
    """
    Upload multiple PDF/Image files.
    Backend will:
      - save them
      - run OCR
      - run all agents (classification, extraction, coverage, missing-docs)
      - generate PDFs if requested
      - return JSON + PDF download links
    """
    try:
        req_id = str(uuid.uuid4())[:8]
        upload_dir = os.path.join(BASE_UPLOAD, req_id)
        output_dir = os.path.join(BASE_OUTPUT, req_id)

        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        saved_files = []

        # Save files to disk
        for f in files:
            filepath = os.path.join(upload_dir, f.filename)
            with open(filepath, "wb") as buffer:
                buffer.write(await f.read())
            saved_files.append(filepath)

        # Run OCR on each
        doc_texts: Dict[str, str] = {}
        ocr_debug = {}

        for path in saved_files:
            ocr_res = extract_text(path)

            filename = ocr_res.get("filename", os.path.basename(path))
            text = ocr_res.get("text", "")
            err = ocr_res.get("error")

            doc_texts[filename] = text
            ocr_debug[filename] = {
                "sample": text[:200],
                "error": err
            }

        # Run entire pipeline (orchestrator)
        result = process_documents(
            doc_texts,
            generate_pdfs=generate_pdfs,
            output_dir=output_dir
        )

        # Build PDF download URLs
        pdf_urls = {}
        for key, path in result.get("generated_pdfs", {}).items():
            if path and os.path.exists(path):
                pdf_urls[key] = f"/download/{req_id}/{os.path.basename(path)}"

        # Extract missing documents list from the structured response
        missing_docs_result = result.get("missing_documents", {})
        missing_docs_list = missing_docs_result.get("missing_docs", []) if isinstance(missing_docs_result, dict) else (missing_docs_result if isinstance(missing_docs_result, list) else [])
        
        # Construct API response
        return JSONResponse({
            "request_id": req_id,
            "ocr_debug": ocr_debug,
            "classified_documents": result.get("classified"),
            "missing_documents": missing_docs_list,  # Return as array for UI compatibility
            "missing_documents_full": missing_docs_result,  # Also include full structured data
            "coverage_result": result.get("coverage_result"),
            "report": result.get("report"),
            "diagnostics": result.get("diagnostics"),
            "generated_pdfs": pdf_urls
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------
# ROUTE: DOWNLOAD PDF
# -----------------------------------------------------------
@app.get("/download/{req_id}/{filename}")
def download_pdf(req_id: str, filename: str):
    filepath = os.path.join(BASE_OUTPUT, req_id, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=filename
    )


# -----------------------------------------------------------
# ROUTE: CLEANUP FILES (OPTIONAL)
# -----------------------------------------------------------
@app.post("/cleanup/{req_id}")
def cleanup(req_id: str):
    upload_dir = os.path.join(BASE_UPLOAD, req_id)
    output_dir = os.path.join(BASE_OUTPUT, req_id)

    removed = {}

    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
        removed["uploaded_files"] = True

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        removed["generated_files"] = True

    return removed


# -----------------------------------------------------------
# HEALTH CHECK
# -----------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}
