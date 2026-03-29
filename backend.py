# backend.py
"""
FULL FASTAPI BACKEND FOR INSURANCE PIPELINE
-------------------------------------------
✓ Accepts PDF/Image uploads
✓ Runs OCR using agents/ocr_agent.py
✓ Passes both TEXT and FILE BYTES to orchestrator
✓ Runs orchestration pipeline with document quality check
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
      - run OCR to extract text
      - pass BOTH text AND file bytes to orchestrator
      - run all agents (quality check, classification, extraction, coverage, missing-docs)
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

        # Save files to disk and keep bytes in memory
        file_data_map = {}
        
        for f in files:
            # Read file bytes
            file_bytes = await f.read()
            
            # Save to disk
            filepath = os.path.join(upload_dir, f.filename)
            with open(filepath, "wb") as buffer:
                buffer.write(file_bytes)
            
            saved_files.append(filepath)
            
            # Store bytes for later use
            file_data_map[f.filename] = {
                'bytes': file_bytes,
                'filepath': filepath
            }

        # Run OCR on each file
        doc_data: Dict[str, Dict] = {}
        ocr_debug = {}

        for filename, file_info in file_data_map.items():
            filepath = file_info['filepath']
            
            # Run OCR
            ocr_res = extract_text(filepath)
            
            text = ocr_res.get("text", "")
            err = ocr_res.get("error")
            
            # Store BOTH text and bytes for orchestrator
            doc_data[filename] = {
                'text': text,
                'bytes': file_info['bytes'],
                'filename': filename
            }
            
            # Debug info for response
            ocr_debug[filename] = {
                "sample": text[:200],
                "error": err,
                "file_size": len(file_info['bytes'])
            }

        # Run entire pipeline (orchestrator) with BOTH text and bytes
        result = process_documents(
            doc_data,  # Now contains text + bytes + filename
            generate_pdfs=generate_pdfs,
            output_dir=output_dir,
            skip_quality_check=False  # Enable quality check
        )

        # Build PDF download URLs
        pdf_urls = {}
        for key, path in result.get("generated_pdfs", {}).items():
            if path and os.path.exists(path):
                pdf_urls[key] = f"/download/{req_id}/{os.path.basename(path)}"

        # Extract quality results
        quality_results = result.get("quality_results", {})
        rejected_docs = result.get("rejected_documents", {})
        
        # Extract missing documents list from the structured response
        missing_docs_result = result.get("missing_documents", {})
        missing_docs_list = missing_docs_result.get("missing_docs", []) if isinstance(missing_docs_result, dict) else (missing_docs_result if isinstance(missing_docs_result, list) else [])
        
        # Construct API response
        return JSONResponse({
            "request_id": req_id,
            "ocr_debug": ocr_debug,
            "quality_results": quality_results,  # Quality check results for each file
            "rejected_documents": rejected_docs,  # Documents that failed quality check
            "classified_documents": result.get("classified"),
            "missing_documents": missing_docs_list,  # Return as array for UI compatibility
            "missing_documents_full": missing_docs_result,  # Also include full structured data
            "coverage_result": result.get("coverage_result"),
            "report": result.get("report"),
            "diagnostics": result.get("diagnostics"),
            "generated_pdfs": pdf_urls
        })

    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


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
# ROUTE: CHECK QUALITY OF SINGLE DOCUMENT
# -----------------------------------------------------------
@app.post("/check-quality")
async def check_document_quality(file: UploadFile = File(...)):
    """
    Quick quality check endpoint for a single document.
    Useful for pre-upload validation.
    """
    try:
        from agents.document_clarity import assess_quality_from_bytes
        
        file_bytes = await file.read()
        
        result = assess_quality_from_bytes(
            file_bytes,
            file.filename,
            config={
                'clarity_threshold': 0.75,
                'alignment_weight': 0.25,
                'clarity_weight': 0.40,
                'readability_weight': 0.35,
                'ai_penalty_weight': 0.10
            }
        )
        
        return JSONResponse(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------
# HEALTH CHECK
# -----------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}


# -----------------------------------------------------------
# STARTUP MESSAGE
# -----------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("=" * 80)
    print("🏥 Health Insurance AI Agent Backend Started")
    print("=" * 80)
    print("\nEndpoints:")
    print("  POST /process          - Upload and process insurance documents")
    print("  POST /check-quality    - Check quality of a single document")
    print("  GET  /download/{req_id}/{filename} - Download generated PDFs")
    print("  POST /cleanup/{req_id} - Clean up uploaded/generated files")
    print("  GET  /health           - Health check")
    print("\nFeatures:")
    print("  ✓ OCR text extraction")
    print("  ✓ Document quality assessment (mandatory)")
    print("  ✓ Document classification")
    print("  ✓ Bill extraction")
    print("  ✓ Coverage calculation")
    print("  ✓ Missing documents detection")
    print("  ✓ Report generation")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)