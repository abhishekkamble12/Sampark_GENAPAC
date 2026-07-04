"""
backend/main.py — FastAPI Application for Sampark AI Platform.

Uses Google ADK for pipeline orchestration (replaces LangGraph).
Integrates Firebase Authentication (replaces custom JWT/bcrypt).
Integrates Cloud Logging for observability.
"""

import asyncio
import time
import uuid
import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.middleware import LoggingMiddleware, AuthAndRateLimitMiddleware
from backend.config import settings

logger = logging.getLogger("sampark.gateway")

# ── Google ADK ─────────────────────────────────────────────────────────
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from agents.adk_sampark_pipeline import sampark_pipeline

# In-memory session service for local development.
# In production, swap to DatabaseSessionService or VertexAiSessionService.
session_service = InMemorySessionService()
runner = Runner(
    agent=sampark_pipeline,
    app_name="sampark-pipeline",
    session_service=session_service,
    auto_create_session=True,
)

# ── Firebase Admin (optional, falls back to demo mode) ─────────────────
firebase_initialized = False
try:
    import firebase_admin
    firebase_admin.initialize_app()
    firebase_initialized = True
    logger.info("Firebase initialized successfully")
except Exception:
    logger.warning("Firebase not available — using demo auth")

# ── Cloud Logging ──────────────────────────────────────────────────────
try:
    import google.cloud.logging
    cloud_logging_client = google.cloud.logging.Client()
    cloud_logging_client.setup_logging()
    logger.info("Cloud Logging initialized")
except Exception:
    logger.warning("Cloud Logging not available — using standard logging")

# ── FastAPI App ────────────────────────────────────────────────────────

app = FastAPI(title="Sampark AI Platform API Gateway (ADK)")

origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthAndRateLimitMiddleware)
app.add_middleware(LoggingMiddleware)


# ── Pydantic Schemas ───────────────────────────────────────────────────

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


# ── Health ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "framework": "google-adk", "version": "0.2.0"}


# ── Startup: Seed Demo Data ────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    if settings.APP_MODE != "production":
        from tools.firestore_tool import FirestoreTool
        logger.info("Seeding local demo data...")

        FirestoreTool._local_db["community_scores"] = {
            "w1": {"ward_id": "w1", "score": 85.0},
            "w2": {"ward_id": "w2", "score": 72.0},
            "w3": {"ward_id": "w3", "score": 90.0},
        }

        issues = {
            "iss_demo1": {
                "id": "iss_demo1", "type": "water",
                "location": {"lat": 18.5204, "lng": 73.8567, "address": "MG Road, Ward 1", "ward_id": "w1"},
                "description": "Water leakage on MG Road. Big waste of drinking water.",
                "media_refs": [], "original_language": "en", "severity": "High"
            },
            "iss_demo2": {
                "id": "iss_demo2", "type": "road",
                "location": {"lat": 18.5304, "lng": 73.8667, "address": "Sector 4 School, Ward 2", "ward_id": "w2"},
                "description": "Pothole near sector 4 school is causing traffic jams.",
                "media_refs": [], "original_language": "en", "severity": "Medium"
            },
            "iss_demo3": {
                "id": "iss_demo3", "type": "electricity",
                "location": {"lat": 18.5104, "lng": 73.8467, "address": "Park Lane, Ward 1", "ward_id": "w1"},
                "description": "Streetlight not working since last Tuesday.",
                "media_refs": [], "original_language": "en", "severity": "Low"
            },
            "iss_demo4": {
                "id": "iss_demo4", "type": "flood",
                "location": {"lat": 18.5404, "lng": 73.8767, "address": "Lowland Area, Ward 3", "ward_id": "w3"},
                "description": "Drainage overflow after yesterday's rain.",
                "media_refs": [], "original_language": "en", "severity": "Critical"
            }
        }
        FirestoreTool._local_db["issues"] = issues
        logger.info("Demo data seeded with %d issues", len(issues))


# ── Auth Endpoint (Firebase Auth) ──────────────────────────────────────

@app.post("/auth/login")
async def login(req: LoginRequest):
    """Demo login. In production, use Firebase Authentication."""
    if firebase_initialized:
        from firebase_admin import auth
        try:
            # In production, verify Firebase ID token sent from client
            user = auth.get_user_by_email(req.username)
            custom_token = auth.create_custom_token(user.uid)
            return {"access_token": custom_token.decode() if isinstance(custom_token, bytes) else custom_token}
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    # Demo mode: simple username/password check
    if req.username == settings.DEMO_ADMIN_USERNAME and req.password == settings.DEMO_ADMIN_PASSWORD:
        return {"access_token": "demo_admin_token", "user_id": "admin_1", "role": "government_officer", "ward_ids": ["*"]}
    if req.username == settings.DEMO_LEADER_USERNAME and req.password == settings.DEMO_LEADER_PASSWORD:
        return {"access_token": "demo_leader_token", "user_id": "leader_1", "role": "community_leader", "ward_ids": ["w1"]}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ── Report Issue (ADK Pipeline) ────────────────────────────────────────

@app.post("/issues")
async def report_issue(req: IssueRequest, request: Request):
    """Submit a citizen issue report via the ADK pipeline.

    Replaces the old LangGraph graph.ainvoke() with ADK Runner.run_async().
    """
    user_id = getattr(request.state, "user_id", "anonymous")
    session_id = req.session_id or f"session_{uuid.uuid4().hex[:8]}"
    issue_id = f"iss_{uuid.uuid4().hex[:8]}"

    start_time = time.time()

    # Build initial state for ADK
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
    }

    # Run the ADK pipeline
    try:
        result = await runner.run_async(
            session_id=session_id,
            initial_state=initial_state,
        )
        final_state = result.state
    except Exception as e:
        logger.exception("ADK pipeline failed for session=%s", session_id)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info("Pipeline completed in %.0fms for session=%s", elapsed_ms, session_id)

    # Persist results to Firestore
    try:
        from tools.firestore_tool import FirestoreTool
        fs = FirestoreTool(None)
        issue_data = final_state.get("issue", {})
        await fs.set_document("issues", issue_id, issue_data)
        await fs.set_document("sessions", session_id, {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "issue_summary": issue_data.get("description"),
            "status": "processed",
        })
    except Exception as e:
        logger.warning("Persistence failed: %s", e)

    # Build response
    workflow_info = final_state.get("workflow") or {}
    validation_info = final_state.get("validation") or {}
    rec_info = final_state.get("recommendation") or {}

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
        "latency_ms": round(elapsed_ms, 0),
    }


# ── Health Score Endpoint ──────────────────────────────────────────────

@app.get("/analytics/ward/{ward_id}/health-score")
async def get_ward_health_score(ward_id: str, request: Request):
    from tools.bigquery_tool import BigQueryTool
    bq = BigQueryTool(project_id=settings.GCP_PROJECT_ID, dataset=settings.BIGQUERY_DATASET)
    score = await bq.read_community_health_score(ward_id)
    return {"ward_id": ward_id, "health_score": score or 82.5, "status": "stable"}


# ── SSE Streaming ──────────────────────────────────────────────────────

@app.get("/chat/stream/{session_id}")
async def chat_stream(session_id: str, request: Request):
    """Stream pipeline progress events by polling ADK session state."""
    async def event_generator():
        from tools.firestore_tool import FirestoreTool
        sent_state = set()
        start_time = time.time()

        while time.time() - start_time < 90:
            if await request.is_disconnected():
                break

            # Poll the ADK session state
            try:
                session = FirestoreTool._local_db.get("sessions", {}).get(session_id, {})
                checkpoints = list(session.get("checkpoints", {}).keys()) if session else []
            except Exception:
                checkpoints = []

            for key in checkpoints:
                if key not in sent_state:
                    sent_state.add(key)
                    yield f"data: Agent {key} completed\n\n"

            status = session.get("status", "running") if session else "running"
            if status in ("completed", "failed"):
                yield "data: Done\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Admin: Upload Document (Vertex AI RAG Engine) ─────────────────────

@app.post("/admin/knowledge-base", dependencies=[Depends(lambda r: None)])
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document for RAG ingestion via Vertex AI RAG Engine.

    Replaces the old custom Ingestor with managed Vertex AI RAG Engine.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit")

    doc_name = file.filename or "unknown.pdf"

    # Guard: RAG corpus must be configured
    if not settings.RAG_CORPUS_ID:
        raise HTTPException(
            status_code=400,
            detail="RAG corpus not configured. Run `python scripts/setup_rag_corpus.py` first",
        )

    try:
        async with asyncio.timeout(30.0):
            # Upload to Cloud Storage
            from google.cloud import storage
            storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
            bucket = storage_client.bucket("sampark-policy-documents")
            blob = bucket.blob(doc_name)
            blob.upload_from_string(file_bytes, content_type="application/pdf")

            # Import into Vertex AI RAG Engine
            from vertexai import rag
            import vertexai
            vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)

            rag_corpus_name = (
                f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_LOCATION}"
                f"/ragCorpora/{settings.RAG_CORPUS_ID}"
            )

            rag.import_files(
                rag_corpus_name,
                [f"gs://sampark-policy-documents/{doc_name}"],
                transformation_config=rag.TransformationConfig(
                    chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=64),
                ),
            )

            return {"document_id": doc_name, "status": "ingested", "method": "vertex-ai-rag-engine"}
    except (asyncio.TimeoutError, TimeoutError):
        raise HTTPException(status_code=504, detail="Ingestion timeout")


# ── Dashboard ──────────────────────────────────────────────────────────

@app.get("/analytics/dashboard")
async def get_dashboard(request: Request):
    user_ward_ids = getattr(request.state, "ward_ids", [])
    from tools.firestore_tool import FirestoreTool

    # Health scores
    scores = []
    for w, data in FirestoreTool._local_db.get("community_scores", {}).items():
        if "*" in user_ward_ids or w in user_ward_ids:
            scores.append(data["score"])
    latest_health_score = sum(scores) / len(scores) if scores else 82.5

    # Open critical tasks
    open_critical = 0
    top_issues = []
    for task_id, t in FirestoreTool._local_db.get("tasks", {}).items():
        issue_id = t.get("issue_id", "")
        issue = FirestoreTool._local_db.get("issues", {}).get(issue_id, {})
        ward_id = issue.get("location", {}).get("ward_id", "")
        if "*" not in user_ward_ids and ward_id not in user_ward_ids:
            continue
        if t.get("status") == "open" and t.get("priority") in ("High", "Critical"):
            open_critical += 1
            top_issues.append({
                "id": issue_id, "desc": issue.get("description", ""),
                "ward_id": ward_id, "priority": t.get("priority"),
            })

    return {
        "health_score": latest_health_score,
        "open_critical": open_critical,
        "top_critical_issues": top_issues[:5],
        "framework": "google-adk",
    }
