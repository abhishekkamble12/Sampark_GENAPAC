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

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Sampark AI Platform API Gateway")

# Enable CORS for frontend dynamically from configuration
origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    session_id: Optional[str] = None

# 13.9 Health Route
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Hash demo passwords securely using config values
ADMIN_HASH = bcrypt.hashpw(settings.DEMO_ADMIN_PASSWORD.encode(), bcrypt.gensalt())
LEADER_HASH = bcrypt.hashpw(settings.DEMO_LEADER_PASSWORD.encode(), bcrypt.gensalt())

@app.on_event("startup")
async def startup_event():
    if settings.APP_MODE == "production" and settings.JWT_SECRET == "mock_secret_key":
        logger.error("CRITICAL: Default JWT_SECRET detected in production APP_MODE!")
        raise RuntimeError("Startup blocked: Set a secure JWT_SECRET in production.")

    if settings.APP_MODE != "production":
        from tools.firestore_tool import FirestoreTool
        logger.info("Seeding local demo data...")
        
        # Seed community scores
        FirestoreTool._local_db["community_scores"] = {
            "w1": {"ward_id": "w1", "score": 85.0},
            "w2": {"ward_id": "w2", "score": 72.0},
            "w3": {"ward_id": "w3", "score": 90.0},
        }
        
        # Seed issues
        issues = {
            "iss_demo1": {
                "id": "iss_demo1",
                "type": "water",
                "location": {"lat": 18.5204, "lng": 73.8567, "address": "MG Road, Ward 1", "ward_id": "w1"},
                "description": "Water leakage on MG Road. Big waste of drinking water.",
                "media_refs": [],
                "original_language": "en",
                "severity": "High"
            },
            "iss_demo2": {
                "id": "iss_demo2",
                "type": "road",
                "location": {"lat": 18.5304, "lng": 73.8667, "address": "Sector 4 School, Ward 2", "ward_id": "w2"},
                "description": "Pothole near sector 4 school is causing traffic jams.",
                "media_refs": [],
                "original_language": "en",
                "severity": "Medium"
            },
            "iss_demo3": {
                "id": "iss_demo3",
                "type": "electricity",
                "location": {"lat": 18.5104, "lng": 73.8467, "address": "Park Lane, Ward 1", "ward_id": "w1"},
                "description": "Streetlight not working since last Tuesday.",
                "media_refs": [],
                "original_language": "en",
                "severity": "Low"
            },
            "iss_demo4": {
                "id": "iss_demo4",
                "type": "flood",
                "location": {"lat": 18.5404, "lng": 73.8767, "address": "Lowland Area, Ward 3", "ward_id": "w3"},
                "description": "Drainage overflow after yesterday's rain.",
                "media_refs": [],
                "original_language": "en",
                "severity": "Critical"
            }
        }
        FirestoreTool._local_db["issues"] = issues
        
        # Seed tasks
        tasks = {
            "task_iss_demo1": {
                "issue_id": "iss_demo1",
                "assigned_department": "Water Supply Department",
                "priority": "High",
                "due_date": "2026-07-06T12:00:00Z",
                "status": "open",
                "created_at": "2026-07-03T12:00:00Z"
            },
            "task_iss_demo2": {
                "issue_id": "iss_demo2",
                "assigned_department": "Public Works Department",
                "priority": "Medium",
                "due_date": "2026-07-10T12:00:00Z",
                "status": "open",
                "created_at": "2026-07-03T12:00:00Z"
            },
            "task_iss_demo3": {
                "issue_id": "iss_demo3",
                "assigned_department": "Electricity Board",
                "priority": "Low",
                "due_date": "2026-07-10T12:00:00Z",
                "status": "resolved",
                "created_at": "2026-07-03T12:00:00Z"
            },
            "task_iss_demo4": {
                "issue_id": "iss_demo4",
                "assigned_department": "Disaster Management Cell",
                "priority": "Critical",
                "due_date": "2026-07-04T12:00:00Z",
                "status": "open",
                "created_at": "2026-07-03T12:00:00Z"
            }
        }
        FirestoreTool._local_db["tasks"] = tasks


        # Seed knowledge base policies
        FirestoreTool._local_db["knowledge_base"] = {
            "road_repair_act_0": {
                "doc_name": "Road Repair Act",
                "chunk_index": 0,
                "page_number": 1,
                "section": "Section 1.0",
                "text": "Potholes on major roads like MG Road must be repaired by the Public Works Department within 48 hours to prevent traffic hazards."
            },
            "road_maintenance_policy_0": {
                "doc_name": "Road Maintenance Policy",
                "chunk_index": 0,
                "page_number": 1,
                "section": "Section 4.2",
                "text": "High-risk potholes near school zones and heavy traffic intersections must be prioritized and repaired by the Public Works Department within 48 to 72 hours."
            },
            "urban_flood_guidelines_0": {
                "doc_name": "Urban Flood Response Guidelines",
                "chunk_index": 0,
                "page_number": 2,
                "section": "Section 1.5",
                "text": "Drainage overflows and lowland flood incidents must be escalated immediately to the Disaster Management Cell for storm pump deployment."
            },
            "water_leakage_protocol_0": {
                "doc_name": "Water Leakage Emergency Protocol",
                "chunk_index": 0,
                "page_number": 1,
                "section": "Section 3.1",
                "text": "Main pipeline bursts or active water leaks on roadways should be shut off and repaired by the Water Supply Department within 24 hours of notification."
            }
        }



# 13.8 Auth Route
@app.post("/auth/login")
async def login(req: LoginRequest):
    # Authenticating with bcrypt
    if req.username == settings.DEMO_ADMIN_USERNAME and bcrypt.checkpw(req.password.encode(), ADMIN_HASH):
        payload = {
            "user_id": "admin_1",
            "role": "government_officer",
            "ward_ids": ["*"],
            "exp": time.time() + 3600
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return {"access_token": token}
    
    if req.username == settings.DEMO_LEADER_USERNAME and bcrypt.checkpw(req.password.encode(), LEADER_HASH):
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
    
    session_id = req.session_id or f"session_{uuid.uuid4().hex[:8]}"
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
    
    # 3. Save to Firestore / Local Persistence
    try:
        from tools.firestore_tool import FirestoreTool
        if settings.APP_MODE == "production":
            from google.cloud import firestore
            db = firestore.AsyncClient(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
            fs = FirestoreTool(db)
        else:
            fs = FirestoreTool(None)
            
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
        logger.warning(f"Persistence failed: {e}")
        
    workflow_info = final_state.get("workflow") or {}
    validation_info = final_state.get("validation") or {}
    rec_info = final_state.get("recommendation") or {}

    # Build structured AI Trace panel details
    issue_data = final_state.get("issue") or {}
    prediction_data = final_state.get("prediction") or {}
    context_data = final_state.get("context") or {}

    traffic_density = context_data.get("traffic", {}).get("traffic_density", "medium") if isinstance(context_data.get("traffic"), dict) else "medium"
    explainability_list = prediction_data.get("explainability") or []
    explainability_str = ", ".join([f"{item['factor']}: {item['weight_pct']:.0f}%" for item in explainability_list]) if explainability_list else "Heuristic model analysis"

    policy_details = []
    for chunk in final_state.get("rag_chunks") or []:
        policy_details.append({
            "name": chunk.get("doc_name", "Municipal Policy"),
            "citation": f"Section {chunk.get('section', 'N/A')}, Page {chunk.get('page_number', '1')}",
            "why_applies": chunk.get("text", "")
        })

    if not policy_details and rec_info.get("cited_policies"):
        for policy in rec_info.get("cited_policies") or []:
            policy_details.append({
                "name": policy,
                "citation": "Municipal Code",
                "why_applies": "Referenced in administrative resolution guidelines."
            })

    ai_trace = {
        "intake": {
            "extracted_type": issue_data.get("type", "other"),
            "extracted_location": (issue_data.get("location") or {}).get("address") or "unknown",
            "language_detected": issue_data.get("original_language") or "en",
            "summary": issue_data.get("description", "")
        },
        "validation": {
            "duplicate_found": "yes" if validation_info.get("duplicate") else "no",
            "location_verified": "yes" if validation_info.get("location_verified") else "no",
            "weather_corroboration": "yes" if validation_info.get("weather_corroborated") else "no",
            "media_evidence": "yes" if validation_info.get("has_media") else "no",
            "confidence_score": f"{int((validation_info.get('confidence_score') or 0.0) * 100)}%"
        },
        "prediction": {
            "flood_risk": f"{int((prediction_data.get('flood_risk') or 0.0) * 100)}%" if prediction_data.get("flood_risk") is not None else "0%",
            "road_risk": f"{int((prediction_data.get('road_risk') or 0.0) * 100)}%" if prediction_data.get("road_risk") is not None else "0%",
            "traffic_risk": traffic_density,
            "risk_explanation": explainability_str
        },
        "recommendation": {
            "action": rec_info.get("action") or "Review by administration",
            "priority": rec_info.get("priority") or "Low",
            "sla": "24 hours" if rec_info.get("priority") == "Critical" else ("72 hours" if rec_info.get("priority") == "High" else "7 days"),
            "policy_citation": ", ".join(rec_info.get("cited_policies") or []) or "No specific policy",
            "rationale": rec_info.get("rationale") or "Standard administrative handling",
            "policy_details": policy_details
        },
        "workflow": {
            "assigned_department": workflow_info.get("assigned_department") or "Admin Review",
            "task_id": workflow_info.get("task_id") or "N/A",
            "due_date": workflow_info.get("due_date") or "N/A",
            "status": "open" if workflow_info.get("task_id") else "pending"
        }
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
        "ai_trace": ai_trace
    }


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
    Open stream, forward actual agent progress events by polling checkpoints.
    """
    async def event_generator():
        from tools.firestore_tool import FirestoreTool
        sent_nodes = set()
        start_time = time.time()
        
        while time.time() - start_time < 90:
            if await request.is_disconnected():
                break
                
            try:
                if settings.APP_MODE == "production":
                    from google.cloud import firestore
                    db = firestore.AsyncClient(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
                    docs = db.collection("sessions").document(session_id).collection("checkpoints").stream()
                    completed = [doc.id async for doc in docs]
                else:
                    session = FirestoreTool._local_db.get("sessions", {}).get(session_id, {})
                    completed = list(session.get("checkpoints", {}).keys())
            except Exception:
                completed = []
                
            for node in completed:
                if node not in sent_nodes:
                    sent_nodes.add(node)
                    yield f"data: Node {node} completed\n\n"
                    
            status = "running"
            try:
                if settings.APP_MODE == "production":
                    from google.cloud import firestore
                    db = firestore.AsyncClient(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
                    doc = await db.collection("sessions").document(session_id).get()
                    if doc.exists:
                        status = doc.to_dict().get("status", "running")
                else:
                    session = FirestoreTool._local_db.get("sessions", {}).get(session_id, {})
                    status = session.get("status", "running")
            except Exception:
                pass
                
            if status in ("completed", "failed") or "response_node" in completed or "error_response_node" in completed:
                yield "data: Done\n\n"
                break
                
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# 15.4 Admin RBAC Dependency
def require_admin(request: Request):
    if "*" not in request.state.ward_ids:
        raise HTTPException(status_code=403, detail="Admin access required")

# 15.1 Validate/Upload Endpoint
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
            from tools.vertex_tool import VertexSearchTool
            from tools.firestore_tool import FirestoreTool
            
            if settings.APP_MODE == "production":
                from google.cloud import firestore_v1
                firestore_client = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID)
            else:
                firestore_client = None
                
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
    
    if settings.APP_MODE != "production":
        # Local listing
        docs = FirestoreTool._local_db.get("knowledge_base", {})
        results = []
        for doc_id, d in docs.items():
            if d.get("chunk_index") == 0:
                results.append({
                    "document_id": d.get("doc_name"),
                    "name": d.get("doc_name"),
                    "status": "active"
                })
        return results
        
    try:
        from google.cloud import firestore_v1
        firestore_client = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID)
        fs_tool = FirestoreTool(firestore_client)
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
    
    if settings.APP_MODE == "production":
        from google.cloud import firestore_v1
        firestore_client = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID)
    else:
        firestore_client = None
        
    vertex_tool = VertexSearchTool(project_id=settings.GCP_PROJECT_ID)
    fs_tool = FirestoreTool(firestore_client)
    ingestor = Ingestor(vertex_tool, fs_tool)
    
    success = await ingestor.delete_document_cascade(document_id)
    if not success:
        raise HTTPException(status_code=500, detail="Delete cascade failed")

@app.get("/analytics/dashboard")
async def get_dashboard(request: Request):
    user_ward_ids = request.state.ward_ids
    
    latest_health_score = 78.5
    health_score_change = "+2.5"
    open_critical = 12
    heatmap = [
        {"ward_id": "w1", "risk": 0.8, "dominant_risk": "road"},
        {"ward_id": "w2", "risk": 0.7, "dominant_risk": "sanitation"},
        {"ward_id": "w3", "risk": 0.6, "dominant_risk": "flood"}
    ]
    top_critical_issues = [
        {"task_id": "TSK-001", "department": "Public Works", "priority": "high", "sla_due": "2026-07-06T12:00:00Z", "status": "open"},
        {"task_id": "TSK-002", "department": "Health", "priority": "critical", "sla_due": "2026-07-05T09:00:00Z", "status": "assigned"},
        {"task_id": "TSK-003", "department": "Water", "priority": "high", "sla_due": "2026-07-07T14:30:00Z", "status": "open"}
    ]
    ai_insights = [
        "Ward 1 road complaints increased 35% this week",
        "Flood risk elevated in Ward 3 due to recent rainfall",
        "Public Works workload may breach SLA in 48 hours"
    ]
    
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
    else:
        # Dynamic Local Calculations
        from tools.firestore_tool import FirestoreTool
        
        # 1. Health scores
        scores = []
        for w, data in FirestoreTool._local_db.get("community_scores", {}).items():
            if "*" in user_ward_ids or w in user_ward_ids:
                scores.append(data["score"])
        latest_health_score = sum(scores) / len(scores) if scores else 82.5
        
        # 2. Count open critical tasks
        open_critical = 0
        tasks_dict = FirestoreTool._local_db.get("tasks", {})
        for task_id, t in tasks_dict.items():
            issue_id = t.get("issue_id")
            issue = FirestoreTool._local_db.get("issues", {}).get(issue_id, {})
            ward_id = issue.get("location", {}).get("ward_id")
            
            if "*" not in user_ward_ids and ward_id not in user_ward_ids:
                continue
                
            if t.get("status") == "open" and t.get("priority") in ("High", "Critical"):
                open_critical += 1
                
        # 3. Heatmap
        ward_issue_counts = {}
        issues_dict = FirestoreTool._local_db.get("issues", {})
        for iss_id, issue in issues_dict.items():
            ward_id = issue.get("location", {}).get("ward_id")
            if ward_id:
                ward_issue_counts[ward_id] = ward_issue_counts.get(ward_id, 0) + 1
                
        heatmap = []
        for w in ["w1", "w2", "w3"]:
            if "*" in user_ward_ids or w in user_ward_ids:
                count = ward_issue_counts.get(w, 0)
                risk = min(count * 0.25, 1.0)
                if risk == 0:
                    risk = 0.1 if w == "w2" else (0.4 if w == "w1" else 0.2)
                heatmap.append({"ward_id": w, "risk": risk})
                
        # 4. Top critical issues
        for iss_id, issue in issues_dict.items():
            ward_id = issue.get("location", {}).get("ward_id")
            if "*" not in user_ward_ids and ward_id not in user_ward_ids:
                continue
                
            task_id = f"task_{iss_id}"
            task = tasks_dict.get(task_id) or {}
            
            if task.get("status") == "open" and task.get("priority") in ("High", "Critical"):
                top_critical_issues.append({
                    "id": iss_id,
                    "desc": issue.get("description", ""),
                    "ward_id": ward_id or "unknown",
                    "priority": task.get("priority"),
                    "department": task.get("assigned_department", "Admin Review")
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
            {"day": "Sun", "count": len(top_critical_issues)}
        ],
        "top_critical_issues": top_critical_issues,
        "ai_insights": ai_insights
    }

# 16.4 Dashboard Real-Time Stream
@app.get("/analytics/dashboard/stream")
async def dashboard_stream(request: Request):
    """
    Firestore `onSnapshot` mock for SSE push of task status updates.
    """
    user_ward_ids = None
    if settings.APP_MODE == "production":
        token = request.query_params.get("token")
        if not token:
            token = request.cookies.get("token")
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            raise HTTPException(status_code=401, detail="Authentication token required")

        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user_ward_ids = payload.get("ward_ids", [])
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    else:
        user_ward_ids = getattr(request.state, "ward_ids", None)
        if not user_ward_ids:
            user_ward_ids = ["*"]

    
    async def task_generator():
        import json
        from tools.firestore_tool import FirestoreTool
        sent_tasks = {}
        start_time = time.time()
        
        while time.time() - start_time < 300:
            if await request.is_disconnected():
                break
                
            try:
                if settings.APP_MODE == "production":
                    from google.cloud import firestore_v1
                    db = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID)
                    docs = db.collection("tasks").stream()
                    tasks = []
                    async for doc in docs:
                        d = doc.to_dict()
                        d["task_id"] = doc.id
                        issue_doc = await db.collection("issues").document(d.get("issue_id")).get()
                        d["ward_id"] = issue_doc.to_dict().get("location", {}).get("ward_id") if issue_doc.exists else "unknown"
                        tasks.append(d)
                else:
                    tasks_dict = FirestoreTool._local_db.get("tasks", {})
                    tasks = []
                    for task_id, t in tasks_dict.items():
                        item = dict(t)
                        item["task_id"] = task_id
                        issue_id = t.get("issue_id")
                        issue = FirestoreTool._local_db.get("issues", {}).get(issue_id, {})
                        item["ward_id"] = issue.get("location", {}).get("ward_id", "unknown")
                        tasks.append(item)
            except Exception:
                tasks = []
                
            for task in tasks:
                task_id = task.get("task_id")
                status = task.get("status")
                ward_id = task.get("ward_id")
                
                if "*" not in user_ward_ids and ward_id not in user_ward_ids:
                    continue
                    
                if sent_tasks.get(task_id) != status:
                    sent_tasks[task_id] = status
                    yield f"data: {json.dumps(task)}\n\n"
                    
            await asyncio.sleep(2.0)

    return StreamingResponse(task_generator(), media_type="text/event-stream")
