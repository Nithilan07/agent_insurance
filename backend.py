# backend.py
import os, uuid, shutil, json, asyncio
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect

from utils.models import init_db, save_claim, update_claim, get_all_claims, get_claim
from agents.ocr_agent import extract_text
from agents.orchestrator import process_documents

# Directories
BASE_UPLOAD = "uploaded_files"
BASE_OUTPUT = "generated_outputs"
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
    await wsmanager.broadcast_all({"claimId": claimId, "status": "ocr"})
    await wsmanager.broadcast_claim(claimId, {"stage": "ocr", "message": "Extracting text..."})

    # OCR
    texts = {}
    for path in filepaths:
        ocr = extract_text(path)
        texts[os.path.basename(path)] = ocr.get("text", "")

    update_claim(claimId, stage="agent1")
    await wsmanager.broadcast_all({"claimId": claimId, "status": "agent1"})
    await wsmanager.broadcast_claim(claimId, {"stage": "agent1", "message": "Analyzing documents..."})

    # Orchestrator
    result = process_documents(texts, generate_pdfs=True, output_dir=output_dir)

    # Final update
    update_claim(claimId, stage="done", status="completed", resultJson=json.dumps(result))
    await wsmanager.broadcast_all({"claimId": claimId, "status": "completed"})
    await wsmanager.broadcast_claim(claimId, {"stage": "done", "message": "Completed", "result": result})


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
    if not r:
        raise HTTPException(404, "Not found")

    return {
        "id": r[0],
        "name": r[1],
        "insuranceId": r[2],
        "policyName": r[3],
        "status": r[4],
        "currentStage": r[5],
        "createdAt": r[6],
        "result": json.loads(r[7]) if r[7] else None
    }


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
