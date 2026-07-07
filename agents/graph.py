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

from typing import TYPE_CHECKING, Any

import logging
from langgraph.graph import END, START, StateGraph

logger = logging.getLogger(__name__)
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
    if state.get("issue") and state["issue"].get("type") not in KNOWN_ISSUE_TYPES:
        state["issue"]["type"] = "other"
        
    if state.get("intake_error"):
        return "error_response_node"
    if state["validation"]["status"] == "low_confidence":
        return "low_confidence_node"
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
try:
    import google.generativeai as genai
except ImportError:
    genai = None
try:
    from google.cloud import firestore_v1, pubsub_v1
except ImportError:
    firestore_v1 = None
    pubsub_v1 = None

from tools.speech_tool import SpeechTool
from tools.vision_tool import VisionTool
from tools.firestore_tool import FirestoreTool
from tools.maps_tool import MapsTool
from tools.weather_tool import WeatherTool
from tools.bigquery_tool import BigQueryTool
from tools.vertex_tool import VertexSearchTool
from rag.retriever import Retriever
from rag.generator import Generator

class MockGeminiModel:
    def generate_content(self, prompt: str) -> Any:
        prompt_str = str(prompt)
        class MockResponse:
            def __init__(self, text):
                self.text = text
        
        if "sentiment" in prompt_str:
            return MockResponse('{"sentiment_score": -0.8}')
        elif "Language identification" in prompt_str or "language" in prompt_str:
            return MockResponse('{"language": "en", "is_english": true, "translated_text": ""}')
        elif "extract" in prompt_str or "extracted information" in prompt_str:
            import re
            normal_type = "road"
            for t in ["road", "sanitation", "water", "electricity", "flood", "traffic", "health"]:
                if t in prompt_str.lower():
                    normal_type = t
                    break
            return MockResponse(f'{{"type": "{normal_type}", "location": "MG Road", "description": "pothole on MG Road"}}')
        elif "retrieved" in prompt_str or "Retrieved Policies" in prompt_str:
            # WOW MOMENT: Dynamically check if the user uploaded a custom policy!
            # The prompt contains "[Document: [doc_name], Page: [page]]"
            import re
            custom_doc_match = re.search(r"\[Document:\s*(.+?),\s*Page:", prompt_str)
            custom_text_match = re.search(r"\]\n(.*?)(?=\n\n\[Document:|$)", prompt_str, re.DOTALL)
            
            doc_name = custom_doc_match.group(1).strip() if custom_doc_match else "General Municipal Code"
            policy_text = custom_text_match.group(1).strip() if custom_text_match else ""
            
            # Extract clean page number if present
            page_match = re.search(r"Page:\s*(\d+)\]", prompt_str)
            page_num = page_match.group(1) if page_match else "1"
            
            impact = "Reduces response latency"
            
            if "Urban Flood" in doc_name:
                action = "Deploy storm water pumps to low-lying areas in lowland zone"
                rationale = "Lowland drainage overflow requires immediate storm pump deployment under Section 1.5 of the Urban Flood Response Guidelines."
                impact = "Reduces flood risk by 30%"
            elif "Water Leakage" in doc_name:
                action = "Shut off local main pipeline valve and dispatch repair crew"
                rationale = "Pipeline leakages must be isolated and resolved within 24 hours per Section 3.1 of the Water Leakage Emergency Protocol."
                impact = "Conserves 500L water per day"
            elif "Road Maintenance" in doc_name or "Road Repair" in doc_name:
                action = "Dispatch Public Works crew for pothole repair within 72 hours"
                rationale = "High-risk potholes near school zones must be prioritized and patched within 72 hours per Section 4.2 of the Road Maintenance Policy."
                impact = "Reduces road hazard risk by 45%"
            else:
                # Dynamic adaptation to ANY newly uploaded policy
                action = f"Execute action based on {doc_name}"
                rationale = f"Policy '{doc_name}' (Page {page_num}) specifically mandates this response: '{policy_text[:100]}...'"
                
                # If we detect specific keywords in the uploaded text, make the action smarter!
                if "drone" in policy_text.lower():
                    action = "Deploy inspection drones immediately"
                    impact = "Accelerates damage assessment by 80%"
                elif "contractor" in policy_text.lower():
                    action = "Escalate to external contractor for expedited resolution"
                    impact = "Leverages private sector efficiency"
                elif "penalty" in policy_text.lower():
                    action = "Issue penalty notice and dispatch inspection team"
                    impact = "Enforces compliance protocol"
            
            return MockResponse(f'{{"action": "{action}", "rationale": "{rationale}", "cited_policies": ["{doc_name}"], "estimated_impact": "{impact}"}}')
        return MockResponse('{}')


speech_tool = SpeechTool(project_id=settings.GCP_PROJECT_ID)
vision_tool = VisionTool(project_id=settings.GCP_PROJECT_ID)

if settings.APP_MODE == "local" or not settings.GEMINI_API_KEY:
    logger.info("Initializing MockGeminiModel for local development...")
    gemini_model = MockGeminiModel()
else:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-pro-latest")

class MockPubSubClient:
    async def publish(self, topic: str, payload: dict) -> None:
        logger.info("[MockPubSub] Published to topic %s: %s", topic, payload)

if settings.APP_MODE == "production":
    firestore_client = firestore_v1.AsyncClient(project=settings.GCP_PROJECT_ID)
    pubsub_client = pubsub_v1.PublisherClient()
else:
    firestore_client = None
    pubsub_client = MockPubSubClient()

fs_tool = FirestoreTool(firestore_client)
maps_tool = MapsTool(api_key=settings.GOOGLE_MAPS_API_KEY)
weather_tool = WeatherTool(api_key=settings.OPENWEATHER_API_KEY)
bq_tool = BigQueryTool(project_id=settings.GCP_PROJECT_ID, dataset=settings.BIGQUERY_DATASET)
vertex_tool = VertexSearchTool(project_id=settings.GCP_PROJECT_ID)

retriever = Retriever(vertex_tool, fs_tool)
generator = Generator(gemini_model)

from agents.checkpointing import FirestoreCheckpointSaver, create_checkpoint_wrapper
saver = FirestoreCheckpointSaver(firestore_client)
wrapper = create_checkpoint_wrapper(saver)

intake_node = wrapper(make_intake_node(speech_tool, vision_tool, gemini_model), "intake_node")
validation_node = wrapper(make_validation_node(fs_tool, maps_tool, weather_tool), "validation_node")
data_intelligence_node = wrapper(make_data_intelligence_node(bq_tool, weather_tool, maps_tool), "data_intelligence_node")
analytics_node = wrapper(make_analytics_node(gemini_model, bq_tool), "analytics_node")
prediction_node = wrapper(make_prediction_node(), "prediction_node")
recommendation_node = wrapper(make_recommendation_node(retriever, generator), "recommendation_node")
workflow_node = wrapper(make_workflow_node(fs_tool, pubsub_client), "workflow_node")


def notification_dispatch_node(state: GraphState) -> GraphState:
    """Implement notification dispatch logic in the graph."""
    logger.info(
        "Notification dispatch node: notifying user about task %s",
        state.get("workflow", {}).get("task_id")
    )
    return state


def response_node(state: GraphState) -> GraphState:
    """Format final response message for citizen."""
    state["execution"]["status"] = "completed"
    if not state.get("response"):
        dept = state.get("workflow", {}).get("assigned_department") or "Admin Review"
        action = state.get("recommendation", {}).get("action") or "Review by administration"
        state["response"] = f"Your report has been successfully processed and assigned to {dept}. Next action: {action}."
    return state


def error_response_node(state: GraphState) -> GraphState:
    """Format error response message for citizen."""
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
    """Handle low confidence validation by requesting more details."""
    reason = state.get("validation", {}).get("failure_reason") or "verification criteria not met"
    state["response"] = f"Your report could not be automatically validated ({reason}). Please resubmit with clearer description or media evidence."
    return state


notification_dispatch_node = wrapper(notification_dispatch_node, "notification_dispatch_node")
response_node = wrapper(response_node, "response_node")
error_response_node = wrapper(error_response_node, "error_response_node")
low_confidence_node = wrapper(low_confidence_node, "low_confidence_node")


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

# Main path: data_intelligence_node feeds sequentially into analytics and prediction (avoiding parallel merge conflicts)
builder.add_edge("data_intelligence_node", "analytics_node")
builder.add_edge("analytics_node", "prediction_node")
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
