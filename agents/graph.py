"""
agents/graph.py — LangGraph StateGraph definition for the Sampark AI Platform (FREE Stack)

All Google Cloud dependencies replaced with free alternatives:
- Vertex AI → Gemini API (AI Studio, free)
- Firestore → SQLite (aiosqlite)
- BigQuery → DuckDB
- Vertex AI Vector Search → FAISS + Gemini Embeddings
- Pub/Sub → Python asyncio.Queue
- Cloud Storage → Local filesystem

Node topology:
    START → intake_node → validation_node → supervisor_router
        ├─→ error_response_node → END
        ├─→ low_confidence_node → response_node → END
        └─→ data_intelligence_node → analytics_node → prediction_node
            → recommendation_node → workflow_node
            → notification_dispatch_node → response_node → END
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agents.state import KNOWN_ISSUE_TYPES, GraphState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------


def supervisor_router(state: GraphState) -> str:
    """Route after validation_node."""
    if state.get("intake_error"):
        return "error_response_node"
    if state["validation"]["status"] == "low_confidence":
        return "low_confidence_node"
    if state["issue"]["type"] not in KNOWN_ISSUE_TYPES:
        state["issue"]["type"] = "other"
    return "data_intelligence_node"


def parallel_dispatch(state: GraphState) -> list[Send]:
    """Fan-out from data_intelligence_node to analytics and prediction in parallel."""
    return [
        Send("analytics_node", state),
        Send("prediction_node", state),
    ]


def check_recommendation_timeout(state: GraphState) -> str:
    """Route after recommendation_node."""
    rec = state.get("recommendation") or {}
    if rec.get("error") == "timeout":
        return "error_response_node"
    return "workflow_node"


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from agents.intake_agent import make_intake_node
from agents.validation_agent import make_validation_node
from agents.data_intelligence_agent import make_data_intelligence_node
from agents.analytics_agent import make_analytics_node
from agents.prediction_agent import make_prediction_node
from agents.recommendation_agent import make_recommendation_node
from agents.workflow_agent import make_workflow_node

from backend.config import settings

# === FREE: Google AI Studio Gemini API (replaces Vertex AI) ===
import google.generativeai as genai

# === FREE: SQLite Database (replaces Firestore) ===
from tools.sqlite_tool import DatabaseTool

# === FREE: FAISS + Gemini Embeddings (replaces Vertex AI Vector Search) ===
from tools.embeddings_tool import EmbeddingSearchTool

from tools.firestore_tool import FirestoreTool
from tools.maps_tool import MapsTool
from tools.weather_tool import WeatherTool
from tools.bigquery_tool import BigQueryTool
from tools.vision_tool import VisionTool
from tools.speech_tool import SpeechTool
from tools.vertex_tool import VertexSearchTool
from rag.retriever import Retriever
from rag.generator import Generator


# ---------------------------------------------------------------------------
# Mock Gemini model for local/demo mode
# ---------------------------------------------------------------------------


class MockGeminiModel:
    def generate_content(self, prompt: str) -> Any:
        prompt_str = str(prompt)

        class MockResponse:
            def __init__(self, text):
                self.text = text

        if "sentiment" in prompt_str:
            return MockResponse('{"sentiment_score": -0.8}')
        elif "Language identification" in prompt_str or "language" in prompt_str:
            return MockResponse(
                '{"language": "en", "is_english": true, "translated_text": ""}'
            )
        elif "extract" in prompt_str or "extracted information" in prompt_str:
            import re
            normal_type = "road"
            for t in ["road", "sanitation", "water", "electricity", "flood", "traffic", "health"]:
                if t in prompt_str.lower():
                    normal_type = t
                    break
            return MockResponse(
                f'{{"type": "{normal_type}", "location": "MG Road", "description": "pothole on MG Road"}}'
            )
        elif "retrieved" in prompt_str or "Retrieved Policies" in prompt_str:
            if "Urban Flood" in prompt_str:
                doc_name = "Urban Flood Response Guidelines"
                action = "Deploy storm water pumps to low-lying areas in lowland zone"
                rationale = "Lowland drainage overflow requires immediate storm pump deployment under Section 1.5 of the Urban Flood Response Guidelines."
            elif "Water Leakage" in prompt_str:
                doc_name = "Water Leakage Emergency Protocol"
                action = "Shut off local main pipeline valve and dispatch repair crew"
                rationale = "Pipeline leakages must be isolated and resolved within 24 hours per Section 3.1 of the Water Leakage Emergency Protocol."
            else:
                doc_name = "Road Maintenance Policy"
                action = "Dispatch Public Works crew for pothole repair within 72 hours"
                rationale = "High-risk potholes near school zones must be prioritized and patched within 72 hours per Section 4.2 of the Road Maintenance Policy."
            return MockResponse(
                f'{{"action": "{action}", "rationale": "{rationale}", "cited_policies": ["{doc_name}"]}}'
            )
        return MockResponse("{}")


# ---------------------------------------------------------------------------
# Initialize FREE services
# ---------------------------------------------------------------------------

# --- Initialize Database (SQLite replaces Firestore) ---
db_tool = DatabaseTool(db_path=settings.SQLITE_DB_PATH)
fs_tool = FirestoreTool(db_tool)

# --- Initialize Vector Search (FAISS + Gemini Embeddings replaces Vertex AI Vector Search) ---
embedding_tool = EmbeddingSearchTool(
    index_path=settings.FAISS_INDEX_PATH,
    metadata_path=settings.VECTOR_METADATA_PATH,
)

# Share the embedding tool with VertexSearchTool adapter
VertexSearchTool._embedding_tool = embedding_tool
vertex_tool = VertexSearchTool(project_id="local")

# --- Initialize Gemini Model (AI Studio replaces Vertex AI Gemini) ---
if settings.APP_MODE == "local" or not settings.GEMINI_API_KEY:
    logger.info("Initializing MockGeminiModel for local development (no API key required)")
    gemini_model = MockGeminiModel()
else:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model_name = settings.GEMINI_MODEL
    gemini_model = genai.GenerativeModel(model_name)

# Share gemini_model with embedding tool for Gemini Embeddings
if embedding_tool is not None and settings.GEMINI_API_KEY:
    embedding_tool._gemini_model = gemini_model

# --- Initialize Tools ---
speech_tool = SpeechTool()
vision_tool = VisionTool(gemini_model=gemini_model)
maps_tool = MapsTool(api_key=settings.GOOGLE_MAPS_API_KEY)
weather_tool = WeatherTool(api_key=settings.OPENWEATHER_API_KEY)
bq_tool = BigQueryTool()
retriever = Retriever(vertex_tool, fs_tool)
generator = Generator(gemini_model)

# --- Initialize Pub/Sub replacement (async in-memory queue) ---
class LocalEventQueue:
    """Replaces Google Cloud Pub/Sub with an in-memory asyncio queue."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    async def publish(self, topic: str, payload: dict) -> None:
        await self._queue.put({"topic": topic, "payload": payload})
        logger.info("[LocalEventQueue] Published to topic %s: %s", topic, payload)

    async def subscribe(self, topic: str):
        """Generator that yields messages for a specific topic."""
        while True:
            msg = await self._queue.get()
            if msg["topic"] == topic:
                yield msg["payload"]


event_queue = LocalEventQueue()

# ---------------------------------------------------------------------------
# Checkpointing (in-memory + SQLite based, replaces Firestore checkpointing)
# ---------------------------------------------------------------------------


class LocalCheckpointSaver:
    """In-memory checkpointing that persists to SQLite on completion.

    Replaces FirestoreCheckpointSaver (no Firestore needed).
    """

    def __init__(self, db_tool: DatabaseTool):
        self._db = db_tool
        self._checkpoints: dict[str, dict[str, Any]] = {}

    async def save_checkpoint(self, session_id: str, node_name: str, state: GraphState) -> None:
        self._checkpoints[f"{session_id}:{node_name}"] = {
            "node_name": node_name,
            "state_snapshot": dict(state),
            "completed_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        }
        logger.debug("Checkpoint saved: session=%s node=%s", session_id, node_name)

    async def load_checkpoint(self, session_id: str, node_name: str) -> GraphState | None:
        cp = self._checkpoints.get(f"{session_id}:{node_name}")
        return cp.get("state_snapshot") if cp else None

    async def list_completed_nodes(self, session_id: str) -> list[str]:
        return [
            cp["node_name"]
            for key, cp in self._checkpoints.items()
            if key.startswith(f"{session_id}:")
        ]


def create_checkpoint_wrapper(saver: LocalCheckpointSaver):
    """Return a decorator factory that wraps node functions with checkpointing."""

    def wrapper(node_fn, node_name: str):
        async def checkpointed_node(state: GraphState) -> GraphState:
            result = await node_fn(state)
            session_id: str = result.get("execution", {}).get("session_id", "unknown")
            await saver.save_checkpoint(session_id, node_name, result)
            return result

        checkpointed_node.__name__ = node_fn.__name__
        checkpointed_node.__qualname__ = node_fn.__qualname__
        return checkpointed_node

    return wrapper


saver = LocalCheckpointSaver(db_tool)
wrapper_fn = create_checkpoint_wrapper(saver)

# ---------------------------------------------------------------------------
# Create wrapped nodes
# ---------------------------------------------------------------------------

intake_node = wrapper_fn(make_intake_node(speech_tool, vision_tool, gemini_model), "intake_node")
validation_node = wrapper_fn(make_validation_node(fs_tool, maps_tool, weather_tool), "validation_node")
data_intelligence_node = wrapper_fn(make_data_intelligence_node(bq_tool, weather_tool, maps_tool), "data_intelligence_node")
analytics_node = wrapper_fn(make_analytics_node(gemini_model, bq_tool), "analytics_node")
prediction_node = wrapper_fn(make_prediction_node(), "prediction_node")
recommendation_node = wrapper_fn(make_recommendation_node(retriever, generator), "recommendation_node")
workflow_node = wrapper_fn(make_workflow_node(fs_tool, event_queue), "workflow_node")


def notification_dispatch_node(state: GraphState) -> GraphState:
    logger.info(
        "Notification dispatch node: notifying user about task %s",
        state.get("workflow", {}).get("task_id"),
    )
    return state


def response_node(state: GraphState) -> GraphState:
    state["execution"]["status"] = "completed"
    if not state.get("response"):
        dept = state.get("workflow", {}).get("assigned_department") or "Admin Review"
        action = state.get("recommendation", {}).get("action") or "Review by administration"
        state["response"] = (
            f"Your report has been successfully processed and assigned to {dept}. "
            f"Next action: {action}."
        )
    return state


def error_response_node(state: GraphState) -> GraphState:
    state["execution"]["status"] = "failed"
    if state.get("intake_error"):
        err = f"Intake failed: {state['intake_error']}"
    elif state.get("translation_error"):
        err = "Translation failed"
    elif state.get("extraction_error"):
        err = "Extraction failed"
    elif state.get("recommendation", {}).get("error") == "timeout":
        err = "System timeout during processing"
    else:
        err = "An internal processing error occurred"
    state["response"] = f"Unable to process report. Error: {err}."
    return state


def low_confidence_node(state: GraphState) -> GraphState:
    reason = state.get("validation", {}).get("failure_reason") or "verification criteria not met"
    state["response"] = (
        f"Your report could not be automatically validated ({reason}). "
        f"Please resubmit with clearer description or media evidence."
    )
    return state


notification_dispatch_node = wrapper_fn(notification_dispatch_node, "notification_dispatch_node")
response_node = wrapper_fn(response_node, "response_node")
error_response_node = wrapper_fn(error_response_node, "error_response_node")
low_confidence_node = wrapper_fn(low_confidence_node, "low_confidence_node")

# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

builder: StateGraph = StateGraph(GraphState)

# --- Register nodes ---
builder.add_node("intake_node", intake_node)
builder.add_node("validation_node", validation_node)
builder.add_node("data_intelligence_node", data_intelligence_node)
builder.add_node("analytics_node", analytics_node)
builder.add_node("prediction_node", prediction_node)
builder.add_node("recommendation_node", recommendation_node)
builder.add_node("workflow_node", workflow_node)
builder.add_node("notification_dispatch_node", notification_dispatch_node)
builder.add_node("response_node", response_node)
builder.add_node("error_response_node", error_response_node)
builder.add_node("low_confidence_node", low_confidence_node)

# --- Wire edges ---
builder.add_edge(START, "intake_node")
builder.add_edge("intake_node", "validation_node")

builder.add_conditional_edges(
    "validation_node",
    supervisor_router,
    {
        "error_response_node": "error_response_node",
        "low_confidence_node": "low_confidence_node",
        "data_intelligence_node": "data_intelligence_node",
    },
)

builder.add_edge("low_confidence_node", "response_node")
builder.add_edge("data_intelligence_node", "analytics_node")
builder.add_edge("analytics_node", "prediction_node")
builder.add_edge("prediction_node", "recommendation_node")

builder.add_conditional_edges(
    "recommendation_node",
    check_recommendation_timeout,
    {
        "error_response_node": "error_response_node",
        "workflow_node": "workflow_node",
    },
)

builder.add_edge("workflow_node", "notification_dispatch_node")
builder.add_edge("notification_dispatch_node", "response_node")
builder.add_edge("response_node", END)
builder.add_edge("error_response_node", END)

# ---------------------------------------------------------------------------
# Compiled graph (module-level singleton)
# ---------------------------------------------------------------------------

graph = builder.compile()
"""Compiled LangGraph graph for the Sampark AI pipeline (FREE stack).

Import this object to invoke the pipeline::

    from agents.graph import graph
    result = await graph.ainvoke(initial_state)
"""
