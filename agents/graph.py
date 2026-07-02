"""
agents/graph.py — LangGraph StateGraph definition for the Sampark AI Platform.

Node topology
-------------
::

    START
      │
      ▼
    intake_node
      │
      ├─[intake_error]──► error_response_node ──► END
      │
      ▼
    validation_node
      │
      ▼
    supervisor_router  ──[low_confidence]──► low_confidence_node ──► response_node ──► END
      │
      ▼
    data_intelligence_node ──────┐
                                  │  (parallel fan-out via Send API)
    analytics_node ◄─────────────┤
    prediction_node ◄────────────┘
      │
      ▼  (fan-in merge)
    recommendation_node
      │
      ├─[timeout]──► error_response_node ──► END
      │
      ▼
    workflow_node
      │
      ▼
    notification_dispatch_node
      │
      ▼
    response_node
      │
      ▼
    END

Routing functions
-----------------
* ``supervisor_router`` — dispatches after ``validation_node``; routes to
  ``error_response_node``, ``low_confidence_node``, or the main path starting
  at ``data_intelligence_node``.
* ``check_recommendation_timeout`` — dispatches after ``recommendation_node``;
  routes to ``error_response_node`` on timeout, otherwise ``workflow_node``.

Stub nodes
----------
All node functions are defined as inline stubs that return the state unchanged.
They will be replaced by real implementations in subsequent tasks (4–12).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agents.state import KNOWN_ISSUE_TYPES, GraphState

# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------


def supervisor_router(state: GraphState) -> str:
    """Route after validation_node.

    Returns
    -------
    str
        One of ``"error_response_node"``, ``"low_confidence_node"``, or
        ``"data_intelligence_node"``.
    """
    if state.get("intake_error"):
        return "error_response_node"
    if state["validation"]["status"] == "low_confidence":
        return "low_confidence_node"
    if state["issue"]["type"] not in KNOWN_ISSUE_TYPES:
        state["issue"]["type"] = "other"
    return "data_intelligence_node"


def parallel_dispatch(state: GraphState) -> list[Send]:
    """Fan-out from data_intelligence_node to analytics and prediction in parallel.

    Uses the LangGraph Send API so both nodes receive a copy of the current
    state and execute concurrently rather than sequentially.

    Returns
    -------
    list[Send]
        A pair of Send objects targeting ``analytics_node`` and
        ``prediction_node``.
    """
    return [
        Send("analytics_node", state),
        Send("prediction_node", state),
    ]


def check_recommendation_timeout(state: GraphState) -> str:
    """Route after recommendation_node.

    Returns
    -------
    str
        ``"error_response_node"`` if the recommendation timed out, else
        ``"workflow_node"``.
    """
    rec = state.get("recommendation") or {}
    if rec.get("error") == "timeout":
        return "error_response_node"
    return "workflow_node"


from agents.intake_agent import make_intake_node
from agents.validation_agent import make_validation_node
from agents.data_intelligence_agent import make_data_intelligence_node
from agents.analytics_agent import make_analytics_node
from agents.prediction_agent import make_prediction_node
from agents.recommendation_agent import make_recommendation_node
from agents.workflow_agent import make_workflow_node

from backend.config import settings
import google.generativeai as genai
from google.cloud import firestore_v1, pubsub_v1

from tools.speech_tool import SpeechTool
from tools.vision_tool import VisionTool
from tools.firestore_tool import FirestoreTool
from tools.maps_tool import MapsTool
from tools.weather_tool import WeatherTool
from tools.bigquery_tool import BigQueryTool
from tools.vertex_tool import VertexSearchTool
from rag.retriever import Retriever
from rag.generator import Generator

speech_tool = SpeechTool(project_id=settings.GCP_PROJECT_ID)
vision_tool = VisionTool(project_id=settings.GCP_PROJECT_ID)
genai.configure(api_key=settings.GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-pro-latest")

if settings.APP_MODE == "production":
    firestore_client = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID)
    pubsub_client = pubsub_v1.PublisherClient()
else:
    firestore_client = None
    pubsub_client = None

fs_tool = FirestoreTool(firestore_client)
maps_tool = MapsTool(api_key=settings.GOOGLE_MAPS_API_KEY)
weather_tool = WeatherTool(api_key=settings.OPENWEATHER_API_KEY)
bq_tool = BigQueryTool(project_id=settings.GCP_PROJECT_ID, dataset=settings.BIGQUERY_DATASET)
vertex_tool = VertexSearchTool(project_id=settings.GCP_PROJECT_ID)

retriever = Retriever(vertex_tool, fs_tool)
generator = Generator(gemini_model)

intake_node = make_intake_node(speech_tool, vision_tool, gemini_model)
validation_node = make_validation_node(fs_tool, maps_tool, weather_tool)
data_intelligence_node = make_data_intelligence_node(bq_tool, weather_tool, maps_tool)
analytics_node = make_analytics_node(gemini_model, bq_tool)
prediction_node = make_prediction_node()
recommendation_node = make_recommendation_node(retriever, generator)
workflow_node = make_workflow_node(fs_tool, pubsub_client)


def notification_dispatch_node(state: GraphState) -> GraphState:  # pragma: no cover – stub
    """Stub: Notification Agent (see task 12)."""
    return state


def response_node(state: GraphState) -> GraphState:  # pragma: no cover – stub
    """Stub: Response formatter — assembles final citizen-facing message."""
    return state


def error_response_node(state: GraphState) -> GraphState:  # pragma: no cover – stub
    """Stub: Error response formatter — returns a graceful error message."""
    return state


def low_confidence_node(state: GraphState) -> GraphState:  # pragma: no cover – stub
    """Stub: Low-confidence path handler — requests more information."""
    return state


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

# START → intake_node
builder.add_edge(START, "intake_node")

# intake_node → (conditional) supervisor_router handles intake_error branch,
# but intake feeds into validation first; the intake_error branch is handled
# by supervisor_router after validation is reached.
# Per the topology: intake_node → validation_node (normal path), with the
# error branch being caught by supervisor_router (which inspects intake_error).
builder.add_edge("intake_node", "validation_node")

# validation_node → supervisor_router (conditional dispatch)
builder.add_conditional_edges(
    "validation_node",
    supervisor_router,
    {
        "error_response_node": "error_response_node",
        "low_confidence_node": "low_confidence_node",
        "data_intelligence_node": "data_intelligence_node",
    },
)

# Low-confidence path: low_confidence_node → response_node → END
builder.add_edge("low_confidence_node", "response_node")

# Main path: data_intelligence_node fans out to analytics and prediction
# simultaneously using the Send API (parallel fan-out — task 2.3)
builder.add_conditional_edges(
    "data_intelligence_node",
    parallel_dispatch,
    ["analytics_node", "prediction_node"],
)

# Fan-in: both analytics and prediction feed into recommendation_node
builder.add_edge("analytics_node", "recommendation_node")
builder.add_edge("prediction_node", "recommendation_node")

# recommendation_node → (conditional) check for timeout
builder.add_conditional_edges(
    "recommendation_node",
    check_recommendation_timeout,
    {
        "error_response_node": "error_response_node",
        "workflow_node": "workflow_node",
    },
)

# Main happy path continues
builder.add_edge("workflow_node", "notification_dispatch_node")
builder.add_edge("notification_dispatch_node", "response_node")

# Terminal edges
builder.add_edge("response_node", END)
builder.add_edge("error_response_node", END)

# ---------------------------------------------------------------------------
# Compiled graph (module-level singleton)
# ---------------------------------------------------------------------------

graph = builder.compile()
"""Compiled LangGraph graph for the Sampark AI pipeline.

Import this object in the LangGraph engine entry-point to invoke the pipeline::

    from agents.graph import graph

    result = await graph.ainvoke(initial_state)
"""
