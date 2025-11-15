# backend.py
import os, uuid, shutil, json, asyncio
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from urllib.parse import quote

from utils.models import init_db, save_claim, update_claim, get_all_claims, get_claim
from agents.ocr_agent import extract_text
from agents.orchestrator import process_documents

# Directories
BASE_UPLOAD = "uploaded_files"
BASE_OUTPUT = "insurance-ui/generated_outputs"
os.makedirs(BASE_UPLOAD, exist_ok=True)
os.makedirs(BASE_OUTPUT, exist_ok=True)

init_db()

app = FastAPI(title="Insurance Claim Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
#   WEBSOCKET MANAGER
# ──────────────────────────────────────────────
class WSManager:
    def __init__(self):
        self.connections_all = []   # dashboard
        self.claim_connections = {} # detail views

    async def broadcast_all(self, message):
        dead = []
        for ws in self.connections_all:
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)
        for ws in dead:
            self.connections_all.remove(ws)

    async def broadcast_claim(self, claimId, message):
        if claimId not in self.claim_connections:
            return
        dead = []
        for ws in self.claim_connections[claimId]:
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)
        for ws in dead:
            self.claim_connections[claimId].remove(ws)

    async def connect_all(self, ws):
        await ws.accept()
        self.connections_all.append(ws)

    async def connect_claim(self, claimId, ws):
        await ws.accept()
        if claimId not in self.claim_connections:
            self.claim_connections[claimId] = []
        self.claim_connections[claimId].append(ws)

wsmanager = WSManager()


# ──────────────────────────────────────────────
#   BACKGROUND WORKER for Pipeline
# ──────────────────────────────────────────────
async def run_pipeline(claimId, filepaths, output_dir):

    update_claim(claimId, stage="ocr", status="processing")
    print(f"[{claimId}] 🔵 Stage: OCR — Updating claim to status=processing")
    await wsmanager.broadcast_all({"claimId": claimId, "status": "ocr"})
    await wsmanager.broadcast_claim(claimId, {"stage": "ocr", "message": "Extracting text..."})
    print(f"[{claimId}] 📡 WS -> OCR stage broadcast sent")


    # OCR
    print(f"[{claimId}] 📄 Starting OCR on {len(filepaths)} files")
    texts = {}
    for path in filepaths:
        print(f"[{claimId}] 🖼️ OCR Processing File: {path}")
        ocr = extract_text(path)
        extracted_text = ocr.get("text", "")
        print(f"[{claimId}] ✍️ OCR Extracted {len(extracted_text)} characters from {os.path.basename(path)}")
        texts[os.path.basename(path)] = extracted_text

    print(f"[{claimId}] ✅ OCR Completed for all files")


    update_claim(claimId, stage="agent1")
    print(f"[{claimId}] 🔵 Stage: Agent 1 — Document Analysis started")
    await wsmanager.broadcast_all({"claimId": claimId, "status": "agent1"})
    await wsmanager.broadcast_claim(claimId, {"stage": "agent1", "message": "Analyzing documents..."})
    print(f"[{claimId}] 📡 WS -> Agent1 stage broadcast sent")


    # Orchestrator
    print(f"[{claimId}] 🧠 Running orchestrator pipeline...")
    result = process_documents(texts, generate_pdfs=True, output_dir=output_dir)
    print(f"[{claimId}] 🧾 Orchestrator completed. Keys in result: {list(result.keys())}")


    # Final update
    print(f"[{claimId}] 🟢 Finalizing claim — storing result JSON into DB")
    update_claim(claimId, stage="done", status="completed", resultJson=json.dumps(result))

    print(f"[{claimId}] 📡 WS -> Completed stage broadcast sent to ALL")
    await wsmanager.broadcast_all({"claimId": claimId, "status": "completed"})

    print(f"[{claimId}] 📡 WS -> Completed stage broadcast sent to CLAIM channel")
    await wsmanager.broadcast_claim(claimId, {"stage": "done", "message": "Completed", "result": result})

    print(f"[{claimId}] 🎉 Pipeline completed SUCCESSFULLY")



# ──────────────────────────────────────────────
#                POST /claims
# ──────────────────────────────────────────────
@app.post("/claims")
async def create_claim(
    name: str = Form(...),
    insuranceId: str = Form(...),
    policyName: str = Form(...),
    files: List[UploadFile] = File(...)
):
    print("Received claim:", name, insuranceId, policyName, len(files), "files")
    claimId = str(uuid.uuid4())[:8]

    save_claim(claimId, name, insuranceId, policyName, status="pending")

    upload_dir = f"{BASE_UPLOAD}/{claimId}"
    output_dir = f"{BASE_OUTPUT}/{claimId}"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    filepaths = []
    for f in files:
        path = os.path.join(upload_dir, f.filename)
        with open(path, "wb") as buf:
            buf.write(await f.read())
        filepaths.append(path)

    # Run pipeline in background
    asyncio.create_task(run_pipeline(claimId, filepaths, output_dir))

    return {"claimId": claimId, "message": "Claim submitted"}

@app.get("/claims/{claimId}/pdf/{filename}")
def download_pdf(claimId: str, filename: str):
    pdf_path = f"{BASE_OUTPUT}/{claimId}/{filename}"

    if not os.path.exists(pdf_path):
        raise HTTPException(404, "PDF not found")

    return FileResponse(pdf_path, media_type="application/pdf")


# ──────────────────────────────────────────────
#              GET /claims (Dashboard List)
# ──────────────────────────────────────────────
@app.get("/claims")
def list_claims():
    rows = get_all_claims()
    return [
        {
            "id": r[0],
            "name": r[1],
            "insuranceId": r[2],
            "policyName": r[3],
            "status": r[4],
            "currentStage": r[5],
            "createdAt": r[6]
        }
        for r in rows
    ]


# ──────────────────────────────────────────────
#             GET /claims/{id} (Detail Page)
# ──────────────────────────────────────────────
@app.get("/claims/{id}")
def claim_details(id):
    r = get_claim(id)
    print("RAW DB RESULT:", r)
    if not r:
        raise HTTPException(404, "Not found")
    
    result_raw = json.loads(r[8]) if r[8] else None
    normalized = normalize_result(id, result_raw)
    
    return {
        "id": r[0],
        "name": r[1],
        "insuranceId": r[2],
        "policyName": r[3],
        "status": r[4],
        "currentStage": r[5],
        "createdAt": r[6],
        "result": normalized
    }

def normalize_result(claimId, result):
    if not result:
        return {}

    # Deep copy safe
    output = dict(result)

    # Convert generated_pdfs local paths → URLs
    if "generated_pdfs" in output:
        new_pdfs = {}
        for key, path in output["generated_pdfs"].items():
            filename = os.path.basename(path)
            new_pdfs[key] = f"http://localhost:8000/claims/{claimId}/pdf/{quote(filename)}"
        output["generated_pdfs"] = new_pdfs

    return output

# ──────────────────────────────────────────────
#       WEBSOCKETS: /ws/claims and /ws/claims/{id}
# ──────────────────────────────────────────────
@app.websocket("/ws/claims")
async def ws_claims(ws: WebSocket):
    await wsmanager.connect_all(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/claims/{claimId}")
async def ws_claim_id(ws: WebSocket, claimId: str):
    await wsmanager.connect_claim(claimId, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
