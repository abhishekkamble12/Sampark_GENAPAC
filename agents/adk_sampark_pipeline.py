"""
agents/adk_sampark_pipeline.py — Root Google ADK pipeline for Sampark AI Platform.

Replaces agents/graph.py (LangGraph StateGraph) with Google ADK composition:
- SequentialAgent for linear pipeline flow
- ParallelAgent for concurrent analytics + prediction
- LlmAgent for each specialized node (intake, validation, analytics, etc.)
- Vertex AI RAG Engine as a native tool for grounded generation

Architecture:
    RootAgent (SequentialAgent)
    ├── intake_agent          → session.state["issue"]
    ├── validation_agent      → session.state["validation"]
    ├── data_intelligence     → session.state["context"] (via ParallelAgent internally)
    ├── analytics_agent       → session.state["analytics"]
    ├── prediction_agent      → session.state["prediction"]
    ├── recommendation_agent  → session.state["recommendation"] (uses Vertex AI RAG)
    ├── workflow_agent        → session.state["workflow"]
    └── response_agent        → session.state["response"]
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

from backend.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared constants (moved from agents/state.py)
# ---------------------------------------------------------------------------

KNOWN_ISSUE_TYPES: frozenset[str] = frozenset(
    {"road", "sanitation", "water", "electricity", "flood", "traffic", "health", "other"}
)

PRIORITY_LEVELS: frozenset[str] = frozenset({"Critical", "High", "Medium", "Low"})

DEPARTMENT_MAP = {
    "road": "Public Works Department",
    "sanitation": "Sanitation & Waste Management",
    "water": "Water Supply Department",
    "electricity": "Electricity Board",
    "flood": "Disaster Management Cell",
    "traffic": "Traffic Police / Urban Mobility",
    "health": "Public Health Department",
    "other": "Admin Review",
}

# ---------------------------------------------------------------------------
# Tool functions (injected into agents)
# ---------------------------------------------------------------------------

# --- Intake Tools ---

async def classify_issue_type(raw_type: str) -> str:
    """Map an extracted issue type label to one of the 8 canonical categories.
    
    Args:
        raw_type: The raw issue type string from extraction.
    
    Returns:
        One of: road, sanitation, water, electricity, flood, traffic, health, other
    """
    normalised = raw_type.strip().lower()
    if normalised in KNOWN_ISSUE_TYPES:
        return normalised
    
    _SYNONYMS = {
        "road": ["pothole", "pavement", "street", "highway", "road damage", "road repair", "tarmac"],
        "sanitation": ["garbage", "waste", "trash", "sewage", "drainage", "sewer", "rubbish", "litter"],
        "water": ["pipe", "leak", "supply", "tap", "drinking water", "water shortage"],
        "electricity": ["power", "electric", "light", "outage", "blackout", "transformer", "wiring"],
        "flood": ["flooding", "waterlogging", "inundation", "overflowing"],
        "traffic": ["congestion", "signal", "jam", "accident", "parking"],
        "health": ["hospital", "clinic", "medical", "disease", "hygiene", "epidemic"],
    }
    for canonical, keywords in _SYNONYMS.items():
        if any(kw in normalised for kw in keywords):
            return canonical
    return "other"

# --- Validation Tools ---

async def check_duplicate_issue(lat: float, lng: float, issue_type: str) -> dict:
    """Check for duplicate open issues within 500m radius with the same type.
    
    Args:
        lat: Latitude of the issue location.
        lng: Longitude of the issue location.
        issue_type: Type of issue to check for duplicates.
    
    Returns:
        Dict with 'duplicate' (bool) and 'nearby_count' (int).
    """
    from tools.firestore_tool import FirestoreTool
    fs = FirestoreTool(None)
    try:
        nearby = await fs.geo_radius_query(
            collection="issues",
            lat=lat, lng=lng,
            radius_meters=500,
            filters={"type": issue_type, "status": "open"},
        )
        return {"duplicate": len(nearby) > 0, "nearby_count": len(nearby)}
    except Exception:
        return {"duplicate": False, "nearby_count": 0}

async def verify_location(address: str, lat: float, lng: float) -> dict:
    """Verify that a location lies within the municipal boundary using Maps API.
    
    Args:
        address: Human-readable address string.
        lat: Latitude coordinate.
        lng: Longitude coordinate.
    
    Returns:
        Dict with 'verified' (bool), 'geocoded_lat' (float), 'geocoded_lng' (float).
    """
    from tools.maps_tool import MapsTool
    maps = MapsTool(api_key=settings.GOOGLE_MAPS_API_KEY)
    try:
        geocoded = await maps.geocode(address or f"{lat},{lng}")
        if geocoded:
            return {
                "verified": True,
                "geocoded_lat": geocoded.get("lat"),
                "geocoded_lng": geocoded.get("lng"),
            }
        return {"verified": False}
    except Exception:
        return {"verified": False}

# --- Data Intelligence Tools ---

async def query_historical_issues(ward_id: str, issue_type: str, days: int = 90) -> list[dict]:
    """Query BigQuery for historical issue data for the given ward and type.
    
    Args:
        ward_id: Ward identifier.
        issue_type: Issue category.
        days: How many days back to query.
    
    Returns:
        List of historical issue records.
    """
    from tools.bigquery_tool import BigQueryTool
    bq = BigQueryTool(project_id=settings.GCP_PROJECT_ID, dataset=settings.BIGQUERY_DATASET)
    return await bq.query_historical_issues(ward_id, issue_type, days)

async def fetch_weather_data(lat: float, lng: float) -> dict:
    """Fetch current weather and 48-hour forecast for a location.
    
    Args:
        lat: Latitude.
        lng: Longitude.
    
    Returns:
        Weather data dict with current conditions and forecast.
    """
    from tools.weather_tool import WeatherTool
    weather = WeatherTool(api_key=settings.OPENWEATHER_API_KEY)
    return await weather.get_current_and_forecast(lat, lng)

async def fetch_traffic_data(lat: float, lng: float) -> dict:
    """Fetch traffic context and nearby facilities for a location.
    
    Args:
        lat: Latitude.
        lng: Longitude.
    
    Returns:
        Traffic context dict with density and nearby facilities.
    """
    from tools.maps_tool import MapsTool
    maps = MapsTool(api_key=settings.GOOGLE_MAPS_API_KEY)
    return await maps.get_traffic_context(lat, lng)

async def fetch_health_score(ward_id: str) -> float | None:
    """Fetch the latest Community Health Score for a ward.
    
    Args:
        ward_id: Ward identifier.
    
    Returns:
        Health score float or None.
    """
    from tools.bigquery_tool import BigQueryTool
    bq = BigQueryTool(project_id=settings.GCP_PROJECT_ID, dataset=settings.BIGQUERY_DATASET)
    return await bq.read_community_health_score(ward_id)

# --- Analytics Tools ---

async def compute_trends(historical_issues: list[dict]) -> dict:
    """Compute 7-day and 30-day complaint volume trends.
    
    Args:
        historical_issues: List of issue records with 'reported_at' dates.
    
    Returns:
        Dict with trend_7d, trend_30d, zero_baseline, insufficient_data flags.
    """
    if not historical_issues or len(historical_issues) < 5:
        return {"trend_7d": None, "trend_30d": None, "zero_baseline": False, "insufficient_data": True}
    
    now = datetime.now(timezone.utc)
    count_0_7 = sum(1 for r in historical_issues if (now - timedelta(days=7)) <= _parse_dt(r.get("reported_at")) <= now)
    count_7_14 = sum(1 for r in historical_issues if (now - timedelta(days=14)) <= _parse_dt(r.get("reported_at")) < (now - timedelta(days=7)))
    count_0_30 = sum(1 for r in historical_issues if (now - timedelta(days=30)) <= _parse_dt(r.get("reported_at")) <= now)
    count_30_60 = sum(1 for r in historical_issues if (now - timedelta(days=60)) <= _parse_dt(r.get("reported_at")) < (now - timedelta(days=30)))
    
    result = {"insufficient_data": False, "zero_baseline": False, "trend_7d": None, "trend_30d": None}
    if count_7_14 == 0 or count_30_60 == 0:
        result["zero_baseline"] = True
    else:
        result["trend_7d"] = ((count_0_7 - count_7_14) / count_7_14) * 100.0
        result["trend_30d"] = ((count_0_30 - count_30_60) / count_30_60) * 100.0
    return result

def _parse_dt(dt_val: Any) -> datetime:
    now = datetime.now(timezone.utc)
    if isinstance(dt_val, str):
        try:
            return datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
        except ValueError:
            return now
    elif isinstance(dt_val, datetime):
        return dt_val.replace(tzinfo=timezone.utc) if dt_val.tzinfo is None else dt_val
    return now

async def analyze_sentiment(descriptions: list[str]) -> dict:
    """Analyze sentiment of complaint descriptions using Natural Language API.
    
    Args:
        descriptions: List of complaint description strings.
    
    Returns:
        Dict with sentiment_score (-1 to 1) and magnitude.
    """
    if not descriptions:
        return {"sentiment_score": None, "magnitude": None}
    
    from google.cloud import language_v2
    client = language_v2.LanguageServiceClient()
    
    all_scores = []
    all_magnitudes = []
    for desc in descriptions[:20]:  # Limit to 20 descriptions
        try:
            document = language_v2.Document(content=desc, type_=language_v2.Document.Type.PLAIN_TEXT)
            response = client.analyze_sentiment(document=document)
            sentiment = response.document_sentiment
            all_scores.append(sentiment.score)
            all_magnitudes.append(sentiment.magnitude)
        except Exception:
            pass
    
    if all_scores:
        return {"sentiment_score": sum(all_scores) / len(all_scores), "magnitude": sum(all_magnitudes) / len(all_magnitudes)}
    return {"sentiment_score": None, "magnitude": None}

# --- Prediction Tools ---

async def compute_risk_scores(
    rainfall_48h: float,
    flood_count: int,
    pothole_count_30d: int,
    rainfall_7d: float,
    traffic_density: str,
    total_7d_volume: int,
    trend_7d: float | None,
) -> dict:
    """Compute flood risk, road risk, volume forecast, and explainability.
    
    Uses heuristic models (logistic regression for flood, gradient boosting for road).
    
    Args:
        rainfall_48h: Rainfall forecast for next 48h.
        flood_count: Historical flood incident count.
        pothole_count_30d: Road complaints in last 30 days.
        rainfall_7d: Rainfall in last 7 days.
        traffic_density: Traffic density (low/medium/high).
        total_7d_volume: Total complaint volume in last 7 days.
        trend_7d: 7-day volume trend percentage.
    
    Returns:
        Dict with flood_risk, road_risk, high_risk_alert, volume_forecast, explainability.
    """
    import math
    
    traffic_mult = {"high": 1.5, "medium": 1.0, "low": 0.5}.get(traffic_density, 1.0)
    
    # Flood risk (logistic regression heuristic)
    drainage_capacity, slope = 50.0, 5.0
    flood_logit = (0.2 * rainfall_48h) + (0.5 * flood_count) - (0.1 * drainage_capacity) + (0.2 * slope)
    flood_risk = 1.0 / (1.0 + math.exp(-max(-10, min(10, flood_logit / 5.0))))
    
    # Road risk (gradient boosting heuristic)
    road_score = (pothole_count_30d * 0.05) + (rainfall_7d * 0.02) + (5.0 * 0.05) + (traffic_mult * 0.1)
    road_risk = max(0.0, min(1.0, road_score))
    
    high_risk_alert = flood_risk > 0.75 or road_risk > 0.75
    
    # Volume forecast
    daily_base = total_7d_volume / 7.0 if total_7d_volume > 0 else 1.0
    daily_trend = ((trend_7d or 0.0) / 100.0) / 7.0
    now = datetime.now(timezone.utc)
    forecast = []
    for i in range(1, 8):
        projected_vol = max(0, int(daily_base * (1 + (daily_trend * i))))
        forecast.append({"date": (now + timedelta(days=i)).strftime("%Y-%m-%d"), "predicted_count": projected_vol})
    
    # Explainability
    factors = (
        {"rainfall_forecast_48h": abs(0.2 * rainfall_48h), "historical_flood_count": abs(0.5 * flood_count)}
        if flood_risk >= road_risk
        else {"pothole_count_30d": abs(pothole_count_30d * 0.05), "rainfall_7d": abs(rainfall_7d * 0.02), "traffic_density": abs(traffic_mult * 0.1)}
    )
    sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:3]
    total = sum(w for _, w in sorted_factors) or 1.0
    explainability = [{"factor": f, "weight_pct": round((w / total) * 100.0, 1)} for f, w in sorted_factors]
    
    return {
        "flood_risk": round(flood_risk, 4),
        "road_risk": round(road_risk, 4),
        "high_risk_alert": high_risk_alert,
        "volume_forecast": forecast,
        "explainability": explainability,
    }

# --- Workflow Tools ---

async def create_firestore_task(issue_id: str, department: str, priority: str, due_date: str) -> dict:
    """Create a task document in Firestore.
    
    Args:
        issue_id: The issue identifier.
        department: Assigned department name.
        priority: Priority level (Critical/High/Medium/Low).
        due_date: ISO 8601 due date string.
    
    Returns:
        Dict with task_id and success flag.
    """
    from tools.firestore_tool import FirestoreTool
    fs = FirestoreTool(None)
    task_id = f"task_{issue_id}"
    now = datetime.now(timezone.utc)
    task_doc = {
        "issue_id": issue_id,
        "assigned_department": department,
        "priority": priority,
        "due_date": due_date,
        "status": "open",
        "created_at": now.isoformat(),
    }
    try:
        await fs.set_document("tasks", task_id, task_doc)
        return {"task_id": task_id, "success": True}
    except Exception as e:
        logger.exception("Firestore task creation failed")
        return {"task_id": task_id, "success": False, "error": str(e)}

async def publish_pubsub_event(topic: str, payload: dict) -> bool:
    """Publish an event to Pub/Sub.
    
    Args:
        topic: Pub/Sub topic name.
        payload: Event payload dict.
    
    Returns:
        True on success, False on failure.
    """
    from google.cloud import pubsub_v1
    import json
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(settings.GCP_PROJECT_ID, topic)
        data = json.dumps(payload).encode("utf-8")
        publisher.publish(topic_path, data)
        return True
    except Exception:
        logger.exception(f"PubSub publish failed for topic {topic}")
        return False

# ---------------------------------------------------------------------------
# Agent Definitions
# ---------------------------------------------------------------------------

# --- Intake Agent ---
# Handles multi-modal input parsing: text, audio, image
# Uses Cloud Translation API for language detection + translation (not Gemini)
intake_agent = LlmAgent(
    name="intake_agent",
    model="gemini-2.5-flash",
    instruction="""You are an intake specialist for a municipal citizen reporting system.

Process the citizen's report from session.state['query'] and session.state['user']:

1. **Detect modality**: Check if query starts with 'audio:' (audio), 'image:' (image), or plain text.
2. **For audio**: The audio bytes follow the 'audio:' prefix. The system transcribes it automatically.
3. **For image**: The image bytes follow the 'image:' prefix. The system captions it automatically.
4. **Language detection & translation**: Use the translation API tool if the text isn't in English.
5. **Extract structured info**: Determine the issue type, location, and description from the text.
6. **Classify the type**: Use the classify_type tool to map to canonical categories.
7. **Build issue object**: Create a structured IssueObject with id, type, location, description, etc.

Output the structured issue to session.state['issue'] as a JSON object with fields:
id, type, location (dict with lat, lng, address, ward_id), description, media_refs, original_language, severity.

If the input is unprocessable, set session.state['intake_error'] to the error reason.
""",
    tools=[FunctionTool(func=classify_issue_type)],
    output_key="issue",
)

# --- Validation Agent ---
# Scores issue credibility using Firestore duplicate check, Maps verification
validation_agent = LlmAgent(
    name="validation_agent",
    model="gemini-2.5-flash",
    instruction="""You are a validation specialist for citizen issue reports.

Given the issue in session.state['issue'], you must:

1. **Check for duplicates**: Use the check_duplicate_issue tool to find nearby open issues.
2. **Verify location**: Use the verify_location tool to check the address is valid.
3. **Check media evidence**: See if the issue has media_refs.
4. **Compute confidence score**: Score from 0.0-1.0 based on:
   - Duplicate found: +0.3
   - Location verified: +0.3
   - Weather corroboration: +0.2 (if rain data supports flood/road/sanitation)
   - Has media evidence: +0.2
5. **Set status**: 'valid' if confidence >= 0.4, otherwise 'low_confidence'.

Output to session.state['validation'] as JSON:
{duplicate, confidence_score, status, location_verified, failure_reason}
""",
    tools=[
        FunctionTool(func=check_duplicate_issue),
        FunctionTool(func=verify_location),
    ],
    output_key="validation",
)

# --- Data Intelligence Agent ---
# Gathers context from BigQuery, Weather, and Maps
data_intelligence_agent = LlmAgent(
    name="data_intelligence_agent",
    model="gemini-2.5-flash",
    instruction="""You are a data intelligence specialist.

Given the issue in session.state['issue'], gather context data:

1. **Historical issues**: Use query_historical_issues tool for the ward and issue type.
2. **Weather data**: Use fetch_weather_data tool for the issue location.
3. **Traffic data**: Use fetch_traffic_data tool for the issue location.
4. **Health score**: Use fetch_health_score tool for the ward.

Output to session.state['context'] as JSON:
{historical_issues, weather, traffic, health_score}

Handle failures gracefully — if a source fails, set it to null.
""",
    tools=[
        FunctionTool(func=query_historical_issues),
        FunctionTool(func=fetch_weather_data),
        FunctionTool(func=fetch_traffic_data),
        FunctionTool(func=fetch_health_score),
    ],
    output_key="context",
)

# --- Analytics Agent ---
# Computes trends, clustering, sentiment (using Natural Language API)
analytics_agent = LlmAgent(
    name="analytics_agent",
    model="gemini-2.5-flash",
    instruction="""You are an analytics specialist.

Given session.state['context'] (which includes historical_issues and health_score)
and session.state['validation']:

1. **Compute trends**: Use compute_trends on the historical issues data.
2. **Analyze sentiment**: Use analyze_sentiment on recent complaint descriptions.
3. **Check health score**: Read from context.health_score.
4. **Detect outliers**: Flag if confidence + complaint frequency is abnormally high.
5. **Build cluster data**: Create geospatial cluster labels from locations.

Output to session.state['analytics'] as JSON:
{trend_7d, trend_30d, zero_baseline, sentiment_score, outlier_flag, insufficient_data, health_score_unavailable}
""",
    tools=[
        FunctionTool(func=compute_trends),
        FunctionTool(func=analyze_sentiment),
    ],
    output_key="analytics",
)

# --- Prediction Agent ---
# Risk forecasting using heuristic models
prediction_agent = LlmAgent(
    name="prediction_agent",
    model="gemini-2.5-flash",
    instruction="""You are a risk prediction specialist.

Given session.state['context'] (weather, traffic, historical_issues)
and session.state['analytics'] (trend_7d):

Extract these inputs and call compute_risk_scores:
- rainfall_48h: from context.weather.rainfall_forecast_48h
- flood_count: count of flood-type issues in historical_issues
- pothole_count_30d: count of road-type issues in last 30 days
- rainfall_7d: from weather data (default 10.0)
- traffic_density: from context.traffic.traffic_density
- total_7d_volume: count of all issues in last 7 days
- trend_7d: from analytics.trend_7d

Output to session.state['prediction'] as JSON:
{flood_risk, road_risk, high_risk_alert, volume_forecast, explainability}
""",
    tools=[FunctionTool(func=compute_risk_scores)],
    output_key="prediction",
)

# --- Recommendation Agent ---
# Uses Vertex AI RAG Engine for grounded policy recommendations
if settings.RAG_CORPUS_ID:
    from vertexai.generative_models import Tool
    from vertexai import rag
    _rag_tool = Tool.from_retrieval(
        retrieval=rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[
                    rag.RagResource(
                        rag_corpus=f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_LOCATION}/ragCorpora/{settings.RAG_CORPUS_ID}",
                    )
                ],
                rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
            ),
        )
    )
    _rag_tools = [_rag_tool]
    logger.info("Vertex AI RAG Engine tool wired with corpus: %s", settings.RAG_CORPUS_ID)
else:
    _rag_tools = []
    logger.warning("No RAG_CORPUS_ID configured — recommendation agent will run without policy retrieval")

recommendation_agent = LlmAgent(
    name="recommendation_agent",
    model="gemini-2.5-flash",
    instruction="""You are a policy recommendation specialist for municipal governance.

Given the current issue, analytics, prediction, and validation from session state:

1. Review the issue type and ward from session.state['issue'].
2. Consider analytics trends, prediction risks, and validation confidence.
3. Generate a structured recommendation with action, priority, rationale, and cited policies.
4. Apply priority matrix:
   - flood_risk > 0.75 AND road_risk > 0.75 AND traffic_density = 'high' → Critical
   - flood_risk > 0.75 OR road_risk > 0.75 OR traffic_density = 'high' → High
   - traffic_density = 'medium' → Medium
   - Otherwise → Low
5. If validation status is 'low_confidence' AND priority is Critical/High, set confidence_caveat.

Use the RAG retrieval tool to find relevant municipal policy documents.
Cite the retrieved policy documents in your rationale.
If no policies are found, set disclaimer accordingly.

Output to session.state['recommendation'] as JSON:
{action, priority, rationale, cited_policies[], estimated_impact, disclaimer, confidence_caveat}
""",
    tools=_rag_tools,
    output_key="recommendation",
)

# --- Workflow Agent ---
# Routes issues to departments, creates tasks, publishes events
workflow_agent = LlmAgent(
    name="workflow_agent",
    model="gemini-2.5-flash",
    instruction="""You are a workflow dispatch specialist.

Given the issue, recommendation, and analytics from session state:

1. **Look up department**: Map issue type to department:
   - road → 'Public Works Department'
   - sanitation → 'Sanitation & Waste Management'
   - water → 'Water Supply Department'
   - electricity → 'Electricity Board'
   - flood → 'Disaster Management Cell'
   - traffic → 'Traffic Police / Urban Mobility'
   - health → 'Public Health Department'
   - other → 'Admin Review'

2. **Calculate SLA due date**:
   - Critical: 24 hours from now
   - High: 72 hours from now
   - Medium/Low: 7 days from now

3. **Create Firestore task**: Use create_firestore_task tool.
4. **Publish event**: Use publish_pubsub_event tool to 'task-created' topic.

Output to session.state['workflow'] as JSON:
{assigned_department, task_id, due_date, routing_fallback, workflow_error}
""",
    tools=[
        FunctionTool(func=create_firestore_task),
        FunctionTool(func=publish_pubsub_event),
    ],
    output_key="workflow",
)

# --- Response Agent ---
# Formats the final citizen-facing response
response_agent = LlmAgent(
    name="response_agent",
    model="gemini-2.5-flash",
    instruction="""You are a citizen-facing response formatter.

Given the complete pipeline results from session state, formulate a clear,
empathetic response to the citizen. Include:
- Confirmation that their report was received
- The assigned department
- The recommended action
- The expected timeline
- The task ID for tracking

If there was an error (intake_error, recommendation.error), apologize and explain
what went wrong.

Output the final response string to session.state['response'].
""",
    output_key="response",
)

# ---------------------------------------------------------------------------
# Root Pipeline Assembly
# ---------------------------------------------------------------------------

sampark_pipeline = SequentialAgent(
    name="sampark_pipeline",
    sub_agents=[
        intake_agent,
        validation_agent,
        data_intelligence_agent,
        analytics_agent,
        prediction_agent,
        recommendation_agent,
        workflow_agent,
        response_agent,
    ],
)

"""
Root Google ADK pipeline that processes citizen issue reports end-to-end.

Usage:
    from agents.adk_sampark_pipeline import sampark_pipeline
    from google.adk import Runner
    
    runner = Runner(agent=sampark_pipeline)
    result = await runner.run_async(
        session_id=session_id,
        initial_state={
            "query": "Pothole on MG Road near school",
            "user": {"user_id": "u1", "role": "citizen", "ward_ids": ["w1"]},
        }
    )
"""
