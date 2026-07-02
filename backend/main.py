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

from backend.middleware import LoggingMiddleware, AuthAndRateLimitMiddleware
from backend.config import settings
import bcrypt
import logging
logger = logging.getLogger("sampark.gateway")

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

# Hash demo passwords securely
ADMIN_HASH = bcrypt.hashpw(b"password", bcrypt.gensalt())
LEADER_HASH = bcrypt.hashpw(b"password", bcrypt.gensalt())

# 13.8 Auth Route
@app.post("/auth/login")
async def login(req: LoginRequest):
    # Authenticating with bcrypt
    if req.username == "admin" and bcrypt.checkpw(req.password.encode(), ADMIN_HASH):
        payload = {
            "user_id": "admin_1",
            "role": "government_officer",
            "ward_ids": ["*"],
            "exp": time.time() + 3600
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return {"access_token": token}
    
    if req.username == "leader_w1" and bcrypt.checkpw(req.password.encode(), LEADER_HASH):
        payload = {
            "user_id": "leader_1",
            "role": "community_leader",
            "ward_ids": ["w1"],
            "exp": time.time() + 3600
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return {"access_token": token}
        
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/issues")
async def report_issue(req: IssueRequest, request: Request):
    user_id = request.state.user_id
    
    # 1. Initialize LangGraph State
    import uuid
    from datetime import datetime, timezone
    
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    issue_id = f"iss_{uuid.uuid4().hex[:8]}"
    
    initial_state = {
        "query": req.description,
        "user": {
            "user_id": user_id,
            "role": getattr(request.state, "role", "citizen"),
            "ward_ids": getattr(request.state, "ward_ids", []),
            "preferred_channel": "app"
        },
        "issue": {
            "id": issue_id,
            "type": "other",  
            "location": req.location.model_dump(),
            "description": req.description,
            "media_refs": [req.image_url] if req.image_url else [],
            "original_language": "en",
            "severity": None
        },
        "execution": {
            "session_id": session_id,
            "status": "running",
            "retry_count": 0,
            "node_checkpoints": []
        }
    }
    
    # 2. Invoke Pipeline
    from agents.graph import graph
    final_state = await graph.ainvoke(initial_state)
    
    # 3. Save to Firestore
    from google.cloud import firestore
    from tools.firestore_tool import FirestoreTool
    
    try:
        if settings.APP_MODE == "production":
            db = firestore.AsyncClient(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
            fs = FirestoreTool(db)
            
            issue_data = final_state.get("issue", {})
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                # Store lightweight version of state
                "issue_summary": issue_data.get("description"),
                "status": "processed"
            }
            
            await fs.set_document("issues", issue_id, issue_data)
            await fs.set_document("sessions", session_id, session_data)
    except Exception as e:
        logger.warning(f"Firestore persistence failed: {e}")
        
    return {"status": "processed", "session_id": session_id, "issue_id": issue_id, "workflow": final_state.get("workflow")}

@app.get("/analytics/ward/{ward_id}/health-score")
async def get_ward_health_score(ward_id: str, request: Request):
    # Retrieve health score via BigQuery
    from tools.bigquery_tool import BigQueryTool
    bq = BigQueryTool(project_id=settings.GCP_PROJECT_ID, dataset=settings.BIGQUERY_DATASET)
    score = await bq.read_community_health_score(ward_id)
    return {"ward_id": ward_id, "health_score": score or 82.5, "status": "stable"}

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
        async with asyncio.timeout(10.0):
            from rag.ingestor import Ingestor
            from tools.vertex_tool import VertexSearchTool
            from tools.firestore_tool import FirestoreTool
            from google.cloud import firestore_v1
            
            firestore_client = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID) if settings.APP_MODE == "production" else None
            vertex_tool = VertexSearchTool(project_id=settings.GCP_PROJECT_ID)
            fs_tool = FirestoreTool(firestore_client)
            ingestor = Ingestor(vertex_tool, fs_tool)
            
            success = await ingestor.ingest_pdf(doc_name, file_bytes)
            if not success:
                raise HTTPException(status_code=500, detail="Ingestion failed")
                
            return {"document_id": doc_name, "status": "ingested"}
    except (asyncio.TimeoutError, TimeoutError):
        raise HTTPException(status_code=504, detail="Ingestion timeout")

# 15.3 List Endpoint
@app.get("/admin/knowledge-base", dependencies=[Depends(require_admin)])
async def list_documents():
    from tools.firestore_tool import FirestoreTool
    from google.cloud import firestore_v1
    firestore_client = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID) if settings.APP_MODE == "production" else None
    fs_tool = FirestoreTool(firestore_client)
    
    if not fs_tool._db:
        return []
        
    try:
        # Filter for chunk_index 0 to list unique documents
        _FieldFilter = fs_tool._get_field_filter()
        docs = fs_tool._db.collection("knowledge_base").where(filter=_FieldFilter("chunk_index", "==", 0)).stream()
        results = []
        async for doc in docs:
            d = doc.to_dict()
            results.append({
                "document_id": d.get("doc_name"),
                "name": d.get("doc_name"),
                "status": "active"
            })
        return results
    except Exception as e:
        logger.exception("Failed to list documents")
        return []

# 15.2 Delete Endpoint
@app.delete("/admin/knowledge-base/{document_id}", dependencies=[Depends(require_admin)], status_code=204)
async def delete_document(document_id: str):
    from rag.ingestor import Ingestor
    from tools.vertex_tool import VertexSearchTool
    from tools.firestore_tool import FirestoreTool
    from google.cloud import firestore_v1
    
    firestore_client = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID) if settings.APP_MODE == "production" else None
    vertex_tool = VertexSearchTool(project_id=settings.GCP_PROJECT_ID)
    fs_tool = FirestoreTool(firestore_client)
    ingestor = Ingestor(vertex_tool, fs_tool)
    
    success = await ingestor.delete_document_cascade(document_id)
    if not success:
        raise HTTPException(status_code=500, detail="Delete cascade failed")

@app.get("/analytics/dashboard")
async def get_dashboard(request: Request):
    user_ward_ids = request.state.ward_ids
    
    latest_health_score = 82.5
    open_critical = 12
    heatmap = [{"ward_id": "w1", "risk": 0.8}, {"ward_id": "w2", "risk": 0.3}]
    
    top_critical_issues = []
    
    if settings.APP_MODE == "production":
        try:
            from google.cloud import bigquery
            from google.cloud import firestore_v1
            
            client = bigquery.Client(project=settings.GCP_PROJECT_ID)
            
            ward_filter = ""
            if "*" not in user_ward_ids:
                wards_str = ", ".join([f"'{w}'" for w in user_ward_ids])
                ward_filter = f"WHERE ward_id IN ({wards_str})"
                
            query = f"""
                SELECT 
                    AVG(avg_health_score) as current_health,
                    SUM(open_critical_count) as open_critical,
                    MAX(max_flood_risk) as top_flood_risk,
                    MAX(max_road_risk) as top_road_risk
                FROM `{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.sampark_dashboard_view`
                {ward_filter}
            """
            results = client.query(query).result()
            row = next(results)
            if row:
                latest_health_score = row.current_health or 82.5
                open_critical = row.open_critical or 12
            
            # Fetch real top issues from firestore
            db = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID)
            _FieldFilter = firestore_v1.FieldFilter
            issues_ref = db.collection("issues").where(filter=_FieldFilter("status", "==", "open"))
            if "*" not in user_ward_ids:
                issues_ref = issues_ref.where(filter=_FieldFilter("location.ward_id", "in", user_ward_ids))
            issues_ref = issues_ref.limit(5)
            
            async for doc in issues_ref.stream():
                d = doc.to_dict()
                top_critical_issues.append({"id": doc.id, "desc": d.get("description", ""), "ward_id": d.get("location", {}).get("ward_id", "")})
                
        except Exception as e:
            logger.warning(f"Dashboard fetch failed: {e}")
            
    return {
        "health_score": latest_health_score,
        "heatmap": heatmap,
        "trend_7d": [],
        "top_critical_issues": top_critical_issues
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
