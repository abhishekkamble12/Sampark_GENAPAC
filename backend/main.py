"""
backend/main.py — FastAPI Application for Sampark AI Platform (FREE Stack)

All Google Cloud dependencies replaced with free alternatives:
- Firestore → SQLite
- BigQuery → DuckDB  
- Cloud Run → uvicorn directly
- Secret Manager → .env file
- Cloud Pub/Sub → in-memory asyncio.Queue
"""

import asyncio
import time
import jwt
from typing import Optional, List
from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

from backend.middleware import LoggingMiddleware, AuthAndRateLimitMiddleware
from backend.config import settings
import bcrypt
import logging

logger = logging.getLogger("sampark.gateway")

app = FastAPI(title="Sampark AI Platform API Gateway")

# Enable CORS for frontend
origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Middlewares
app.add_middleware(AuthAndRateLimitMiddleware)
app.add_middleware(LoggingMiddleware)

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


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
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Global database reference (initialized on startup)
# ---------------------------------------------------------------------------

_db = None  # DatabaseTool instance
_bq = None  # BigQueryTool (DuckDB) instance


async def get_db():
    """Get the database instance."""
    global _db
    if _db is None:
        from tools.sqlite_tool import DatabaseTool
        _db = DatabaseTool(db_path=settings.SQLITE_DB_PATH)
        await _db.initialize()
    return _db


async def get_bq():
    """Get the analytics (DuckDB) instance."""
    global _bq
    if _bq is None:
        from tools.bigquery_tool import BigQueryTool
        _bq = BigQueryTool()
    return _bq


# Hash demo passwords
ADMIN_HASH = bcrypt.hashpw(settings.DEMO_ADMIN_PASSWORD.encode(), bcrypt.gensalt())
LEADER_HASH = bcrypt.hashpw(settings.DEMO_LEADER_PASSWORD.encode(), bcrypt.gensalt())


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Startup event - seed demo data
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event():
    """Initialize databases and seed demo data."""
    db = await get_db()
    await _seed_demo_data(db)

    logger.info("Sampark AI Platform started (FREE stack - all local, no GCP required)")


async def _seed_demo_data(db):
    """Seed demo data into SQLite."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    # Community scores
    scores = {
        "w1": {"ward_id": "w1", "score": 85.0, "status": "stable"},
        "w2": {"ward_id": "w2", "score": 72.0, "status": "stable"},
        "w3": {"ward_id": "w3", "score": 90.0, "status": "stable"},
    }
    for wid, data in scores.items():
        await db.set_document("community_scores", wid, data)

    # Issues
    issues = {
        "iss_demo1": {
            "id": "iss_demo1", "type": "water",
            "location": {"lat": 18.5204, "lng": 73.8567, "address": "MG Road, Ward 1", "ward_id": "w1"},
            "description": "Water leakage on MG Road. Big waste of drinking water.",
            "media_refs": [], "original_language": "en", "severity": "High",
        },
        "iss_demo2": {
            "id": "iss_demo2", "type": "road",
            "location": {"lat": 18.5304, "lng": 73.8667, "address": "Sector 4 School, Ward 2", "ward_id": "w2"},
            "description": "Pothole near sector 4 school is causing traffic jams.",
            "media_refs": [], "original_language": "en", "severity": "Medium",
        },
        "iss_demo3": {
            "id": "iss_demo3", "type": "electricity",
            "location": {"lat": 18.5104, "lng": 73.8467, "address": "Park Lane, Ward 1", "ward_id": "w1"},
            "description": "Streetlight not working since last Tuesday.",
            "media_refs": [], "original_language": "en", "severity": "Low",
        },
        "iss_demo4": {
            "id": "iss_demo4", "type": "flood",
            "location": {"lat": 18.5404, "lng": 73.8767, "address": "Lowland Area, Ward 3", "ward_id": "w3"},
            "description": "Drainage overflow after yesterday's rain.",
            "media_refs": [], "original_language": "en", "severity": "Critical",
        },
    }
    for iid, data in issues.items():
        await db.set_document("issues", iid, data)

    # Tasks
    tasks = {
        "task_iss_demo1": {
            "issue_id": "iss_demo1", "assigned_department": "Water Supply Department",
            "priority": "High", "due_date": "2026-07-06T12:00:00Z", "status": "open",
            "created_at": now,
        },
        "task_iss_demo2": {
            "issue_id": "iss_demo2", "assigned_department": "Public Works Department",
            "priority": "Medium", "due_date": "2026-07-10T12:00:00Z", "status": "open",
            "created_at": now,
        },
        "task_iss_demo3": {
            "issue_id": "iss_demo3", "assigned_department": "Electricity Board",
            "priority": "Low", "due_date": "2026-07-10T12:00:00Z", "status": "resolved",
            "created_at": now,
        },
        "task_iss_demo4": {
            "issue_id": "iss_demo4", "assigned_department": "Disaster Management Cell",
            "priority": "Critical", "due_date": "2026-07-04T12:00:00Z", "status": "open",
            "created_at": now,
        },
    }
    for tid, data in tasks.items():
        await db.set_document("tasks", tid, data)

    # Knowledge base
    kb_docs = {
        "road_repair_act_0": {
            "doc_name": "Road Repair Act", "chunk_index": 0, "page_number": 1,
            "section": "Section 1.0",
            "text": "Potholes on major roads like MG Road must be repaired by the Public Works Department within 48 hours to prevent traffic hazards.",
        },
        "road_maintenance_policy_0": {
            "doc_name": "Road Maintenance Policy", "chunk_index": 0, "page_number": 1,
            "section": "Section 4.2",
            "text": "High-risk potholes near school zones and heavy traffic intersections must be prioritized and repaired by the Public Works Department within 48 to 72 hours.",
        },
        "urban_flood_guidelines_0": {
            "doc_name": "Urban Flood Response Guidelines", "chunk_index": 0, "page_number": 2,
            "section": "Section 1.5",
            "text": "Drainage overflows and lowland flood incidents must be escalated immediately to the Disaster Management Cell for storm pump deployment.",
        },
        "water_leakage_protocol_0": {
            "doc_name": "Water Leakage Emergency Protocol", "chunk_index": 0, "page_number": 1,
            "section": "Section 3.1",
            "text": "Main pipeline bursts or active water leaks on roadways should be shut off and repaired by the Water Supply Department within 24 hours of notification.",
        },
    }
    for kid, data in kb_docs.items():
        await db.set_document("knowledge_base", kid, data)


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@app.post("/auth/login")
async def login(req: LoginRequest):
    if req.username == settings.DEMO_ADMIN_USERNAME and bcrypt.checkpw(
        req.password.encode(), ADMIN_HASH
    ):
        payload = {
            "user_id": "admin_1",
            "role": "government_officer",
            "ward_ids": ["*"],
            "exp": time.time() + 3600,
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return {"access_token": token}

    if req.username == settings.DEMO_LEADER_USERNAME and bcrypt.checkpw(
        req.password.encode(), LEADER_HASH
    ):
        payload = {
            "user_id": "leader_1",
            "role": "community_leader",
            "ward_ids": ["w1"],
            "exp": time.time() + 3600,
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return {"access_token": token}

    raise HTTPException(status_code=401, detail="Invalid credentials")


# ---------------------------------------------------------------------------
# Issue reporting
# ---------------------------------------------------------------------------


@app.post("/issues")
async def report_issue(req: IssueRequest, request: Request):
    user_id = request.state.user_id

    import uuid
    from datetime import datetime, timezone

    session_id = req.session_id or f"session_{uuid.uuid4().hex[:8]}"
    issue_id = f"iss_{uuid.uuid4().hex[:8]}"

    initial_state = {
        "query": req.description,
        "user": {
            "user_id": user_id,
            "role": getattr(request.state, "role", "citizen"),
            "ward_ids": getattr(request.state, "ward_ids", []),
            "preferred_channel": "app",
        },
        "issue": {
            "id": issue_id,
            "type": "other",
            "location": req.location.model_dump(),
            "description": req.description,
            "media_refs": [req.image_url] if req.image_url else [],
            "original_language": "en",
            "severity": None,
        },
        "execution": {
            "session_id": session_id,
            "status": "running",
            "retry_count": 0,
            "node_checkpoints": [],
        },
    }

    # Invoke LangGraph pipeline
    from agents.graph import graph
    final_state = await graph.ainvoke(initial_state)

    # Persist to SQLite
    try:
        db = await get_db()
        issue_data = final_state.get("issue", {})
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "issue_summary": issue_data.get("description"),
            "status": "processed",
        }
        await db.set_document("issues", issue_id, issue_data)
        await db.set_document("sessions", session_id, session_data)
    except Exception as e:
        logger.warning(f"Persistence failed: {e}")

    workflow_info = final_state.get("workflow") or {}
    validation_info = final_state.get("validation") or {}
    rec_info = final_state.get("recommendation") or {}
    issue_data = final_state.get("issue") or {}
    prediction_data = final_state.get("prediction") or {}
    context_data = final_state.get("context") or {}

    traffic_density = (
        context_data.get("traffic", {}).get("traffic_density", "medium")
        if isinstance(context_data.get("traffic"), dict)
        else "medium"
    )
    explainability_list = prediction_data.get("explainability") or []
    explainability_str = (
        ", ".join([f"{item['factor']}: {item['weight_pct']:.0f}%" for item in explainability_list])
        if explainability_list
        else "Heuristic model analysis"
    )

    policy_details = []
    for chunk in final_state.get("rag_chunks") or []:
        policy_details.append({
            "name": chunk.get("doc_name", "Municipal Policy"),
            "citation": f"Section {chunk.get('section', 'N/A')}, Page {chunk.get('page_number', '1')}",
            "why_applies": chunk.get("text", ""),
        })

    if not policy_details and rec_info.get("cited_policies"):
        for policy in rec_info.get("cited_policies") or []:
            policy_details.append({
                "name": policy,
                "citation": "Municipal Code",
                "why_applies": "Referenced in administrative resolution guidelines.",
            })

    ai_trace = {
        "intake": {
            "extracted_type": issue_data.get("type", "other"),
            "extracted_location": (issue_data.get("location") or {}).get("address") or "unknown",
            "language_detected": issue_data.get("original_language") or "en",
            "summary": issue_data.get("description", ""),
        },
        "validation": {
            "duplicate_found": "yes" if validation_info.get("duplicate") else "no",
            "location_verified": "yes" if validation_info.get("location_verified") else "no",
            "weather_corroboration": "yes" if validation_info.get("weather_corroborated") else "no",
            "media_evidence": "yes" if validation_info.get("has_media") else "no",
            "confidence_score": f"{int((validation_info.get('confidence_score') or 0.0) * 100)}%",
        },
        "prediction": {
            "flood_risk": f"{int((prediction_data.get('flood_risk') or 0.0) * 100)}%",
            "road_risk": f"{int((prediction_data.get('road_risk') or 0.0) * 100)}%",
            "traffic_risk": traffic_density,
            "risk_explanation": explainability_str,
        },
        "recommendation": {
            "action": rec_info.get("action") or "Review by administration",
            "priority": rec_info.get("priority") or "Low",
            "sla": "24 hours" if rec_info.get("priority") == "Critical"
            else ("72 hours" if rec_info.get("priority") == "High" else "7 days"),
            "policy_citation": ", ".join(rec_info.get("cited_policies") or []) or "No specific policy",
            "rationale": rec_info.get("rationale") or "Standard administrative handling",
            "policy_details": policy_details,
        },
        "workflow": {
            "assigned_department": workflow_info.get("assigned_department") or "Admin Review",
            "task_id": workflow_info.get("task_id") or "N/A",
            "due_date": workflow_info.get("due_date") or "N/A",
            "status": "open" if workflow_info.get("task_id") else "pending",
        },
    }

    return {
        "session_id": session_id,
        "issue_id": issue_id,
        "task_id": workflow_info.get("task_id") or f"task_{issue_id}",
        "message": final_state.get("response", ""),
        "issue_type": (final_state.get("issue") or {}).get("type") or "other",
        "department": workflow_info.get("assigned_department") or "Admin Review",
        "priority": rec_info.get("priority") or "Low",
        "confidence": validation_info.get("confidence_score") or 0.0,
        "next_action": rec_info.get("action") or "Admin Review",
        "ai_trace": ai_trace,
    }


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------


@app.get("/analytics/ward/{ward_id}/health-score")
async def get_ward_health_score(ward_id: str, request: Request):
    """Get health score for a ward using DuckDB analytics."""
    db = await get_db()
    score = await db.read_community_health_score(ward_id)
    return {"ward_id": ward_id, "health_score": score or 82.5, "status": "stable"}


@app.get("/analytics/dashboard")
async def get_dashboard(request: Request):
    """Get dashboard analytics using local SQLite data."""
    user_ward_ids = request.state.ward_ids
    db = await get_db()

    latest_health_score = 78.5
    health_score_change = "+2.5"
    heatmap = [
        {"ward_id": "w1", "risk": 0.8, "dominant_risk": "road"},
        {"ward_id": "w2", "risk": 0.7, "dominant_risk": "sanitation"},
        {"ward_id": "w3", "risk": 0.6, "dominant_risk": "flood"},
    ]
    top_critical_issues = []
    ai_insights = [
        "Ward 1 road complaints increased 35% this week",
        "Flood risk elevated in Ward 3 due to recent rainfall",
        "Public Works workload may breach SLA in 48 hours",
    ]

    # Local SQLite calculations
    scores = await db.list_documents("community_scores")
    score_values = []
    for s in scores:
        if "*" in user_ward_ids or s.get("ward_id") in user_ward_ids:
            score_values.append(s.get("score", 0))
    latest_health_score = sum(score_values) / len(score_values) if score_values else 82.5

    # Count open critical tasks
    all_tasks = await db.list_documents("tasks")
    open_critical = 0
    for t in all_tasks:
        issue = await db.get_document("issues", t.get("issue_id", ""))
        ward_id = issue.get("location", {}).get("ward_id") if issue else None
        if "*" not in user_ward_ids and ward_id not in user_ward_ids:
            continue
        if t.get("status") == "open" and t.get("priority") in ("High", "Critical"):
            open_critical += 1

    # Heatmap
    all_issues = await db.list_documents("issues")
    ward_issue_counts = {}
    for issue in all_issues:
        wid = issue.get("location", {}).get("ward_id")
        if wid:
            ward_issue_counts[wid] = ward_issue_counts.get(wid, 0) + 1

    heatmap = []
    for w in ["w1", "w2", "w3"]:
        if "*" in user_ward_ids or w in user_ward_ids:
            count = ward_issue_counts.get(w, 0)
            risk = min(count * 0.25, 1.0)
            if risk == 0:
                risk = 0.1 if w == "w2" else (0.4 if w == "w1" else 0.2)
            heatmap.append({"ward_id": w, "risk": risk})

    # Top critical issues
    for issue in all_issues:
        wid = issue.get("location", {}).get("ward_id")
        if "*" not in user_ward_ids and wid not in user_ward_ids:
            continue
        task_id = f"task_{issue.get('id')}"
        task = None
        for t in all_tasks:
            if t.get("issue_id") == issue.get("id"):
                task = t
                break
        if task and task.get("status") == "open" and task.get("priority") in ("High", "Critical"):
            top_critical_issues.append({
                "id": issue.get("id"),
                "desc": issue.get("description", ""),
                "ward_id": wid or "unknown",
                "priority": task.get("priority"),
                "department": task.get("assigned_department", "Admin Review"),
            })

    top_critical_issues.sort(key=lambda x: 0 if x["priority"] == "Critical" else 1)
    top_critical_issues = top_critical_issues[:5]

    return {
        "health_score": latest_health_score,
        "health_score_change": health_score_change,
        "heatmap": heatmap,
        "trend_7d": [
            {"day": "Mon", "count": 2},
            {"day": "Tue", "count": 4},
            {"day": "Wed", "count": 1},
            {"day": "Thu", "count": 5},
            {"day": "Fri", "count": 3},
            {"day": "Sat", "count": 2},
            {"day": "Sun", "count": len(top_critical_issues)},
        ],
        "top_critical_issues": top_critical_issues,
        "ai_insights": ai_insights,
    }


# ---------------------------------------------------------------------------
# SSE Streaming
# ---------------------------------------------------------------------------


@app.get("/chat/stream/{session_id}")
async def chat_stream(session_id: str, request: Request):
    """Stream agent progress events by polling SQLite checkpoints."""

    async def event_generator():
        db = await get_db()
        sent_nodes = set()
        start_time = time.time()

        while time.time() - start_time < 90:
            if await request.is_disconnected():
                break

            try:
                session = await db.get_document("sessions", session_id)
                completed = list(session.get("checkpoints", {}).keys()) if session else []
            except Exception:
                completed = []

            for node in completed:
                if node not in sent_nodes:
                    sent_nodes.add(node)
                    yield f"data: Node {node} completed\n\n"

            status = "running"
            try:
                session = await db.get_document("sessions", session_id)
                if session:
                    status = session.get("status", "running")
            except Exception:
                pass

            if status in ("completed", "failed") or "response_node" in completed or "error_response_node" in completed:
                yield "data: Done\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Admin RBAC
# ---------------------------------------------------------------------------


def require_admin(request: Request):
    if "*" not in request.state.ward_ids:
        raise HTTPException(status_code=403, detail="Admin access required")


# ---------------------------------------------------------------------------
# Knowledge Base Management
# ---------------------------------------------------------------------------


@app.post("/admin/knowledge-base", dependencies=[Depends(require_admin)])
async def upload_document(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit")

    doc_name = file.filename or "unknown.pdf"

    try:
        async with asyncio.timeout(10.0):
            from rag.ingestor import Ingestor
            from tools.firestore_tool import FirestoreTool
            from tools.vertex_tool import VertexSearchTool

            fs_tool = FirestoreTool(await get_db())
            vertex_tool = VertexSearchTool()
            ingestor = Ingestor(vertex_tool, fs_tool)

            success = await ingestor.ingest_pdf(doc_name, file_bytes)
            if not success:
                raise HTTPException(status_code=500, detail="Ingestion failed")

            return {"document_id": doc_name, "status": "ingested"}
    except (asyncio.TimeoutError, TimeoutError):
        raise HTTPException(status_code=504, detail="Ingestion timeout")


@app.get("/admin/knowledge-base", dependencies=[Depends(require_admin)])
async def list_documents():
    db = await get_db()
    docs = await db.list_documents("knowledge_base")
    seen = set()
    results = []
    for d in docs:
        name = d.get("doc_name")
        if name and name not in seen:
            seen.add(name)
            results.append({"document_id": name, "name": name, "status": "active"})
    return results


@app.delete(
    "/admin/knowledge-base/{document_id}",
    dependencies=[Depends(require_admin)],
    status_code=204,
)
async def delete_document(document_id: str):
    from rag.ingestor import Ingestor
    from tools.firestore_tool import FirestoreTool
    from tools.vertex_tool import VertexSearchTool

    fs_tool = FirestoreTool(await get_db())
    vertex_tool = VertexSearchTool()
    ingestor = Ingestor(vertex_tool, fs_tool)

    success = await ingestor.delete_document_cascade(document_id)
    if not success:
        raise HTTPException(status_code=500, detail="Delete cascade failed")


# ---------------------------------------------------------------------------
# Dashboard real-time stream
# ---------------------------------------------------------------------------


@app.get("/analytics/dashboard/stream")
async def dashboard_stream(request: Request):
    """SSE stream for task status updates using local data."""
    user_ward_ids = getattr(request.state, "ward_ids", ["*"])

    async def task_generator():
        import json
        db = await get_db()
        sent_tasks = {}
        start_time = time.time()

        while time.time() - start_time < 300:
            if await request.is_disconnected():
                break

            try:
                tasks = await db.list_documents("tasks")
                for task in tasks:
                    issue = await db.get_document("issues", task.get("issue_id", ""))
                    task["ward_id"] = (
                        issue.get("location", {}).get("ward_id", "unknown")
                        if issue
                        else "unknown"
                    )
            except Exception:
                tasks = []

            for task in tasks:
                task_id = task.get("id") or task.get("task_id")
                status = task.get("status")
                ward_id = task.get("ward_id")

                if "*" not in user_ward_ids and ward_id not in user_ward_ids:
                    continue
                if sent_tasks.get(task_id) != status:
                    sent_tasks[task_id] = status
                    task["task_id"] = task_id
                    yield f"data: {json.dumps(task)}\n\n"

            await asyncio.sleep(2.0)

    return StreamingResponse(task_generator(), media_type="text/event-stream")
