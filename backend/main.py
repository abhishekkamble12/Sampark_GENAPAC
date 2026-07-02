"""
backend/main.py — FastAPI Application for Sampark AI Platform.

Exposes endpoints with Pydantic validation and SSE streaming capabilities.
"""

import asyncio
import time
import jwt
from typing import Optional, List
from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.middleware import LoggingMiddleware, AuthAndRateLimitMiddleware, JWT_SECRET, JWT_ALGORITHM

app = FastAPI(title="Sampark AI Platform API Gateway")

# 13.1 Add Middlewares (order matters: outermost first)
app.add_middleware(AuthAndRateLimitMiddleware)
app.add_middleware(LoggingMiddleware)

# 13.4 Pydantic Schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class Location(BaseModel):
    lat: float
    lng: float
    ward_id: str

class IssueRequest(BaseModel):
    description: str = Field(..., min_length=10)
    image_url: Optional[str] = None
    location: Location

# 13.9 Health Route
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# 13.8 Auth Route
@app.post("/auth/login")
async def login(req: LoginRequest):
    # Mocking Firebase Auth
    if req.username == "admin" and req.password == "password":
        payload = {
            "user_id": "admin_1",
            "role": "government_officer",
            "ward_ids": ["*"],
            "exp": time.time() + 3600
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {"access_token": token}
    
    if req.username == "leader_w1":
        payload = {
            "user_id": "leader_1",
            "role": "community_leader",
            "ward_ids": ["w1"],
            "exp": time.time() + 3600
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {"access_token": token}
        
    return {"error": "invalid credentials"}

# Example authenticated endpoint
@app.post("/issues")
async def report_issue(req: IssueRequest, request: Request):
    user_id = request.state.user_id
    return {"status": "received", "user": user_id, "issue": req.dict()}

@app.get("/analytics/ward/{ward_id}/health-score")
async def get_ward_health_score(ward_id: str, request: Request):
    # 14.7 Mock 90-day history array
    if ward_id.lower() == "unknown":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Ward not found")
        
    import random
    history = [
        {"date": f"2026-07-{str((day % 30) + 1).zfill(2)}", "score": max(0.0, 85 - (day * 0.2) + random.uniform(-2, 2))}
        for day in range(90)
    ]
    return {"ward_id": ward_id, "history": history}

# 13.5 SSE Streaming
@app.get("/chat/stream/{session_id}")
async def chat_stream(session_id: str, request: Request):
    """
    Open stream, forward agent progress events.
    """
    async def event_generator():
        events = [
            "Initializing agents...",
            "Routing to Public Works...",
            "Analyzing images...",
            "Done."
        ]
        try:
            for event in events:
                # Disconnect check
                if await request.is_disconnected():
                    break
                yield f"data: {event}\n\n"
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# 15.4 Admin RBAC Dependency
def require_admin(request: Request):
    if "*" not in request.state.ward_ids:
        raise HTTPException(status_code=403, detail="Admin access required")

# 15.1 Upload Endpoint
@app.post("/admin/knowledge-base", dependencies=[Depends(require_admin)])
async def upload_document(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # 15.1 Validate <= 50MB (Mock check by reading length if possible, or just accept)
    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit")
        
    doc_name = file.filename or "unknown.pdf"
    
    try:
        async with asyncio.timeout(5.0):
            # Mock ingestor trigger
            from rag.ingestor import Ingestor
            # Mocks for vertex and firestore
            mock_vertex = type("V", (), {"get_embeddings": lambda t: [[0.1]*768]*len(t), "upsert_vectors": lambda v: None})()
            mock_fs = type("F", (), {"save_document_chunks": lambda n, m: None})()
            ingestor = Ingestor(mock_vertex, mock_fs)
            
            success = await ingestor.ingest_pdf(doc_name, file_bytes)
            if not success:
                raise HTTPException(status_code=500, detail="Ingestion failed")
                
            return {"document_id": doc_name, "status": "ingested"}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Ingestion timeout")

# 15.3 List Endpoint
@app.get("/admin/knowledge-base", dependencies=[Depends(require_admin)])
async def list_documents():
    return [
        {"document_id": "policy_2026.pdf", "name": "Policy 2026", "status": "active", "chunk_count": 42, "ingested_at": "2026-07-01T00:00:00Z"}
    ]

# 15.2 Delete Endpoint
@app.delete("/admin/knowledge-base/{document_id}", dependencies=[Depends(require_admin)], status_code=204)
async def delete_document(document_id: str):
    from rag.ingestor import Ingestor
    mock_vertex = type("V", (), {"delete_vectors": lambda ids: None})()
    mock_fs = type("F", (), {"get_document_chunks": lambda n: [], "delete_document_metadata": lambda n: None})()
    ingestor = Ingestor(mock_vertex, mock_fs)
    
    success = await ingestor.delete_document_cascade(document_id)
    if not success:
        raise HTTPException(status_code=500, detail="Delete cascade failed")

# 16.3 Dashboard Endpoint
@app.get("/analytics/dashboard")
async def get_dashboard(request: Request):
    user_ward_ids = request.state.ward_ids
    
    # Mock data to simulate 16.1 / 16.2 SQL View aggregation
    latest_health_score = 82.5
    open_critical = 12
    heatmap = [{"ward_id": "w1", "risk": 0.8}, {"ward_id": "w2", "risk": 0.3}]
    
    # 16.5 Ward Filtering
    if "*" not in user_ward_ids:
        heatmap = [h for h in heatmap if h["ward_id"] in user_ward_ids]
        # Adjust mock scalars to simulate ward-specific view
        if user_ward_ids == ["w1"]:
            latest_health_score = 75.0
            open_critical = 5
            
    return {
        "health_score": latest_health_score,
        "heatmap": heatmap,
        "trend_7d": [78.0, 79.5, 80.0, 79.0, 81.0, 82.0, latest_health_score],
        "top_critical_issues": [
            {"id": "issue_1", "desc": "Massive pothole on Main St", "ward_id": "w1"}
        ][:open_critical] # Just a structural mock
    }

# 16.4 Dashboard Real-Time Stream
@app.get("/analytics/dashboard/stream")
async def dashboard_stream(request: Request):
    """
    Firestore `onSnapshot` mock for SSE push of task status updates.
    """
    user_ward_ids = request.state.ward_ids
    
    async def task_generator():
        mock_tasks = [
            {"task_id": "t1", "ward_id": "w1", "status": "in_progress"},
            {"task_id": "t2", "ward_id": "w2", "status": "resolved"},
            {"task_id": "t3", "ward_id": "w1", "status": "resolved"}
        ]
        
        try:
            for task in mock_tasks:
                if await request.is_disconnected():
                    break
                
                # 16.5 Enforce ward-scope filtering on stream
                if "*" not in user_ward_ids and task["ward_id"] not in user_ward_ids:
                    continue
                    
                yield f"data: {json.dumps(task)}\n\n"
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    import json
    return StreamingResponse(task_generator(), media_type="text/event-stream")
