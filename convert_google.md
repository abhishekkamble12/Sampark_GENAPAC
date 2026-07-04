# 🔄 Sampark AI — Google ADK & Full Google Cloud Conversion Guide

> **Status:** Comprehensive Migration Plan  
> **Target Framework:** Google Agent Development Kit (ADK)  
> **Goal:** Replace LangGraph + custom RAG with Google ADK, Vertex AI RAG Engine, and maximize Google Cloud services

---

## 📋 Table of Contents

1. [Why Convert to Google ADK?](#1-why-convert-to-google-adk)
2. [Architecture Overview — Before & After](#2-architecture-overview--before--after)
3. [Phase 1: Replace LangGraph with Google ADK](#3-phase-1-replace-langgraph-with-google-adk)
4. [Phase 2: Replace Custom RAG with Vertex AI RAG Engine](#4-phase-2-replace-custom-rag-with-vertex-ai-rag-engine)
5. [Phase 3: Maximize Google Cloud Services](#5-phase-3-maximize-google-cloud-services)
6. [Phase 4: Deployment & Infrastructure Changes](#6-phase-4-deployment--infrastructure-changes)
7. [Phase 5: Testing & Validation Strategy](#7-phase-5-testing--validation-strategy)
8. [Dependency Changes](#8-dependency-changes)
9. [File-by-File Migration Checklist](#9-file-by-file-migration-checklist)
10. [Estimated Effort & Priority](#10-estimated-effort--priority)

---

## 1. Why Convert to Google ADK?

### 1.1 Hackathon Compliance

The hackathon explicitly requires: **"Your project must be built using the Agent Development Kit (ADK)."** Converting LangGraph → ADK is the single highest-impact change for judging criteria.

### 1.2 Strategic Benefits

| Aspect | Current (LangGraph) | Target (Google ADK) | Benefit |
|--------|-------------------|-------------------|---------|
| **Framework** | LangGraph (community) | Google ADK (official Google) | Hackathon alignment + Google support |
| **RAG** | Custom with pypdf + mock Vector Search | Vertex AI RAG Engine (managed) | No manual chunking/embedding code |
| **Models** | Manual Gemini calls | Native ADK + Gemini integration | Simpler code, built-in tool calling |
| **Deployment** | Custom Dockerfile | ADK → Vertex AI Agent Engine | One-command deploy, auto-scaling |
| **Observability** | None | Cloud Trace + Cloud Logging built-in | Free debugging & monitoring |
| **State Mgmt** | Custom checkpointing code | ADK session.state + output_key | Battle-tested, less code |

### 1.3 What Changes

- **Removed:** `langgraph`, `langchain` dependencies, custom `StateGraph`, manual checkpointing, custom RAG pipeline
- **Added:** `google-adk`, `google-genai` (unified SDK), Vertex AI RAG Engine, Google Cloud managed services
- **Kept:** Core agent logic (intake, validation, analytics, prediction, workflow), Google Cloud infra (Firestore, BigQuery, Pub/Sub, Cloud Run)

---

## 2. Architecture Overview — Before & After

### 2.1 Current Architecture (LangGraph)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Gateway                             │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ ainvoke(GraphState)
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                              │
│                                                                      │
│  START → intake_node → validation_node → supervisor_router           │
│                                              │                       │
│                                    ┌─────────┴──────────┐           │
│                                    ▼                    ▼           │
│                          data_intelligence    low_confidence_node    │
│                                    │                                 │
│                          ┌─────────┴──────────┐                      │
│                          ▼                    ▼                      │
│                   analytics_node      prediction_node                │
│                                    │                                 │
│                                    ▼                                 │
│                          recommendation_node (RAG)                   │
│                                    │                                 │
│                                    ▼                                 │
│                          workflow_node → response → END              │
└──────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Custom RAG Pipeline               Google Cloud Infra                │
│  ┌──────────────┐                  ┌──────────┐                     │
│  │ pypdf parser │                  │ Firestore│                     │
│  │ Manual chunk │                  │ BigQuery │                     │
│  │ Mock vectors │                  │ Pub/Sub  │                     │
│  └──────────────┘                  └──────────┘                     │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Target Architecture (Google ADK + Full GCP)

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FastAPI Gateway                                  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ ADK run_async()
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Google ADK Root Agent (SequentialAgent)                 │
│                                                                      │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ IntakeAgent │→│ValidationAgent│→│DataIntelAgent│→│AnalyticsAgent│ │
│  │ (LlmAgent)  │ │ (LlmAgent)   │ │ (LlmAgent)   │ │ (LlmAgent)   │ │
│  └─────────────┘ └──────────────┘ └──────────────┘ └──────┬───────┘ │
│                                                            │         │
│                                              ┌─────────────┴───────┐ │
│                                              │  ParallelAgent      │ │
│                                              │  ┌───────────────┐  │ │
│                                              │  │PredictionAgent│  │ │
│                                              │  └───────────────┘  │ │
│                                              └──────────┬──────────┘ │
│                                                         ▼           │
│  ┌──────────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ RecommendAgent   │→│ WorkflowAgent│→│ ResponseAgent → END     │ │
│  │ (uses RAG Tool)  │ │ (LlmAgent)   │ │ (LlmAgent)              │ │
│  └──────────────────┘ └──────────────┘ └──────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Vertex AI RAG Engine       Fully Managed Google Services               │
│  (Managed: chunking,        ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│   embedding, retrieval)     │ Firestore│ │ BigQuery │ │ Cloud Trace  │ │
│                             │ Pub/Sub  │ │Cloud Run │ │Cloud Monitor │ │
│                             │FCM +Twilio│ │Cloud Logs│ │Firebase Auth │ │
│                             └──────────┘ └──────────┘ └──────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 1: Replace LangGraph with Google ADK

### 3.1 Installation

```bash
# Remove old dependencies
pip uninstall langgraph langchain

# Install Google ADK + unified Gen AI SDK
pip install google-adk
pip install google-genai  # Unified SDK for Gemini (replaces google-generativeai)
```

### 3.2 ADK Agent Definitions — Migrating Each LangGraph Node

#### 3.2.1 Agent: IntakeAgent (Replaces `agents/intake_agent.py`)

**Why ADK is better:** ADK's `LlmAgent` natively handles tool calling loops. Instead of manually calling Gemini for language detection + extraction + classification, you define tools and let ADK orchestrate.

```python
# agents/adk_intake_agent.py
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

# Custom tools for the intake agent
async def detect_language(text: str) -> dict:
    """Detect language and translate to English if needed.
    Returns {'language': str, 'is_english': bool, 'translated_text': str}"""
    # Uses Gemini via ADK's built-in model access
    ...

async def extract_issue(text: str) -> dict:
    """Extract issue type, location, and description from citizen report.
    Returns {'type': str, 'location': str, 'description': str}"""
    ...

async def classify_type(raw_type: str) -> str:
    """Map raw issue type to canonical category.
    Returns one of: road, sanitation, water, electricity, flood, traffic, health, other"""
    ...

# Define the intake agent
intake_agent = LlmAgent(
    name="intake_agent",
    model="gemini-2.5-flash",
    instruction="""You are an intake specialist for a municipal citizen reporting system.
    
    1. Detect the input modality (text, audio: prefix, image: prefix)
    2. For audio: use speech_tool to transcribe
    3. For image: use vision_tool to caption
    4. Detect language and translate to English
    5. Extract structured issue info (type, location, description)
    6. Classify the issue type into canonical categories
    
    Output the result to 'issue' in session state.""",
    tools=[
        FunctionTool(func=detect_language),
        FunctionTool(func=extract_issue),
        FunctionTool(func=classify_type),
    ],
    output_key="issue",  # Auto-writes to session.state["issue"]
)
```

**Why this change:**

| Current (LangGraph) | Target (ADK) | Rationale |
|---------------------|-------------|-----------|
| Manual `asyncio.timeout` for SLA | Built-in agent timeout | Less boilerplate |
| Manual Gemini calls via `_run_gemini()` | ADK manages LLM calls | Less code, built-in retry |
| Manual JSON parsing | `response_schema` with Pydantic | Type-safe, validated output |
| Manual state dict mutation | `output_key` + `session.state` | Clear data flow |

#### 3.2.2 Agent: ValidationAgent (Replaces `agents/validation_agent.py`)

```python
# agents/adk_validation_agent.py
validation_agent = LlmAgent(
    name="validation_agent",
    model="gemini-2.5-flash",
    instruction="""You are a validation specialist for citizen issue reports.
    Given an issue from session state, you must:
    1. Check for duplicates using the duplicate_check tool
    2. Verify location validity using the location_verify tool
    3. Cross-reference with weather data
    4. Compute a confidence score (0.0-1.0)
    5. Set status to 'valid' if confidence >= 0.4, else 'low_confidence'
    
    Output the validation result to 'validation' in session state.""",
    tools=[
        FunctionTool(func=check_duplicate_issue),
        FunctionTool(func=verify_location),
        FunctionTool(func=corroborate_weather),
    ],
    output_key="validation",
)
```

#### 3.2.3 Agent: DataIntelligenceAgent (Replaces `agents/data_intelligence_agent.py`)

**Why this change improves concurrency:** ADK's `ParallelAgent` handles concurrent execution natively without `asyncio.gather` boilerplate.

```python
# agents/adk_data_intelligence_agent.py
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent

# Sub-agents for parallel data fetching
bigquery_agent = LlmAgent(
    name="bigquery_fetcher",
    model="gemini-2.5-flash",
    instruction="Query BigQuery for historical issue data for the current ward.",
    tools=[FunctionTool(func=query_bigquery_historical)],
    output_key="historical_issues",
)

weather_agent = LlmAgent(
    name="weather_fetcher",
    model="gemini-2.5-flash",
    instruction="Fetch current weather and forecast for the issue location.",
    tools=[FunctionTool(func=fetch_weather_data)],
    output_key="weather",
)

maps_agent = LlmAgent(
    name="maps_fetcher",
    model="gemini-2.5-flash",
    instruction="Fetch traffic context for the issue location.",
    tools=[FunctionTool(func=fetch_traffic_data)],
    output_key="traffic",
)

# Parallel execution (replaces asyncio.gather)
parallel_data_fetch = ParallelAgent(
    name="parallel_data_fetch",
    sub_agents=[bigquery_agent, weather_agent, maps_agent],
)
```

#### 3.2.4 Agent: AnalyticsAgent (Replaces `agents/analytics_agent.py`)

```python
# agents/adk_analytics_agent.py
analytics_agent = LlmAgent(
    name="analytics_agent",
    model="gemini-2.5-flash",
    instruction="""You are an analytics specialist. Given historical data and current issue context:
    1. Compute 7-day and 30-day trends
    2. Perform geospatial clustering
    3. Score sentiment using Gemini
    4. Detect outliers
    5. Check community health score
    
    Output analytics results to 'analytics' in session state.""",
    tools=[
        FunctionTool(func=compute_trends),
        FunctionTool(func=perform_clustering),
        FunctionTool(func=analyze_sentiment),
        FunctionTool(func=detect_outliers),
        FunctionTool(func=check_health_score),
    ],
    output_key="analytics",
)
```

#### 3.2.5 Agent: PredictionAgent (Replaces `agents/prediction_agent.py`)

```python
# agents/adk_prediction_agent.py
prediction_agent = LlmAgent(
    name="prediction_agent",
    model="gemini-2.5-flash",
    instruction="""You are a risk prediction specialist. Given analytics and weather data:
    1. Compute flood risk using logistic regression heuristic
    2. Compute road deterioration risk
    3. Forecast 7-day complaint volume
    4. Generate SHAP-like explainability
    5. Set high_risk_alert if any risk > 0.75
    
    Output prediction results to 'prediction' in session state.""",
    tools=[FunctionTool(func=compute_risk_scores)],
    output_key="prediction",
)
```

#### 3.2.6 Agent: RecommendationAgent (Replaces `agents/recommendation_agent.py`)

**Why this is transformed by ADK + RAG Engine:** The custom RAG pipeline is replaced by ADK's native `Tool.from_retrieval()` which integrates Vertex AI RAG Engine as a first-class tool.

```python
# agents/adk_recommendation_agent.py
from vertexai import rag
from vertexai.generative_models import Tool
from google.adk.agents import LlmAgent

# Configure RAG Engine as a Gemini tool
rag_retrieval_tool = Tool.from_retrieval(
    retrieval=rag.Retrieval(
        source=rag.VertexRagStore(
            rag_resources=[
                rag.RagResource(
                    rag_corpus="projects/{project_id}/locations/us-central1/ragCorpora/{corpus_id}"
                )
            ],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
        ),
    )
)

# The recommendation agent uses RAG Engine as a built-in tool
recommendation_agent = LlmAgent(
    name="recommendation_agent",
    model="gemini-2.5-flash",
    instruction="""You are a policy recommendation specialist.
    1. Retrieve relevant policy documents using the RAG tool
    2. Generate a grounded recommendation with citations
    3. Apply priority matrix based on flood risk, road risk, and traffic density
    4. Add confidence caveat if validation was low confidence
    5. Add disclaimer if no policies were found
    
    Output recommendation to 'recommendation' in session state.""",
    tools=[rag_retrieval_tool],  # Vertex AI RAG Engine as native tool
    output_key="recommendation",
)
```

#### 3.2.7 Agent: WorkflowAgent (Replaces `agents/workflow_agent.py`)

```python
# agents/adk_workflow_agent.py
workflow_agent = LlmAgent(
    name="workflow_agent",
    model="gemini-2.5-flash",
    instruction="""You are a workflow dispatch specialist.
    1. Look up the assigned department based on issue type
    2. Calculate SLA due date based on priority
    3. Create a task document in Firestore
    4. Publish a task-created event to Pub/Sub
    
    Output workflow result to 'workflow' in session state.""",
    tools=[
        FunctionTool(func=lookup_department),
        FunctionTool(func=create_firestore_task),
        FunctionTool(func=publish_pubsub_event),
    ],
    output_key="workflow",
)
```

### 3.3 Root Agent Assembly (Replaces `agents/graph.py`)

**Why this is better:** Instead of manually wiring `StateGraph` nodes with `add_node()` + `add_edge()` + `add_conditional_edges()`, ADK uses declarative `SequentialAgent` and `ParallelAgent` composition.

```python
# agents/adk_sampark_pipeline.py
from google.adk.agents import SequentialAgent, ParallelAgent, LlmAgent

# ── Build the pipeline with ADK workflow agents ──

# Parallel execution for data gathering (replaces Send API fan-out)
data_parallel = ParallelAgent(
    name="data_parallel",
    sub_agents=[analytics_agent, prediction_agent],
)

# Funnel agent to merge parallel results
funnel_agent = LlmAgent(
    name="funnel_agent",
    model="gemini-2.5-flash",
    instruction="Review the prediction and analytics results and prepare a unified summary for the recommendation stage.",
    output_key="funnel_summary",
)

# Main pipeline as SequentialAgent (replaces StateGraph)
sampark_pipeline = SequentialAgent(
    name="sampark_pipeline",
    sub_agents=[
        intake_agent,
        validation_agent,
        data_intelligence_agent,
        data_parallel,          # Parallel execution (like Send API)
        funnel_agent,           # Merge parallel results
        recommendation_agent,   # Uses Vertex AI RAG Engine
        workflow_agent,
        response_agent,         # Format final response
    ],
)
```

### 3.4 State Management — ADK `session.state` (Replaces `GraphState` TypedDict)

**Why this change:**

| Current (LangGraph) | Target (ADK) | Rationale |
|---------------------|-------------|-----------|
| `GraphState` TypedDict with 16+ fields | `session.state` dictionary + `output_key` | ADK manages state lifecycle |
| Manual `state["field"] = value` in each node | `output_key="field"` in agent config | Declarative, less code |
| `execution` metadata field | ADK built-in execution tracking | No manual metadata |
| `rag_chunks` field in state | RAG Engine manages chunks internally | Cleaner state shape |
| Checkpointing code (200+ lines) | ADK built-in checkpointing | Zero custom code |

```python
# Example: Invoking the pipeline with ADK
from google.adk import Runner

runner = Runner(agent=sampark_pipeline)

# Initial state is passed via session.state
initial_state = {
    "query": "Large pothole on MG Road near the school",
    "user": {
        "user_id": "user_123",
        "role": "citizen",
        "ward_ids": ["w1"],
        "preferred_channel": "app",
    },
    "issue": {
        "id": "iss_abc123",
        "type": "other",
        "location": {"lat": 18.52, "lng": 73.85, "ward_id": "w1"},
        "description": "Large pothole on MG Road near the school",
    },
}

result = await runner.run_async(
    session_id="session_abc123",
    initial_state=initial_state,
)
```

### 3.5 Error Handling & Retry (Replaces `agents/retry.py`)

**Why:** ADK has built-in retry and error handling — no need for custom `with_retry()` wrapper.

```python
# Built into ADK - no custom code needed
recommendation_agent = LlmAgent(
    name="recommendation_agent",
    model="gemini-2.5-flash",
    max_retries=2,              # Replaces with_retry()
    retry_backoff_seconds=2.0,  # Replaces custom backoff
    ...
)
```

### 3.6 Checkpointing & Resume (Replaces `agents/checkpointing.py` + `agents/resume.py`)

**Why:** ADK has built-in session persistence and checkpointing — ~300 lines of custom code eliminated.

```python
# ADK automatically persists session state
# No need for FirestoreCheckpointSaver, create_checkpoint_wrapper, or try_resume()

# To resume:
result = await runner.run_async(
    session_id="session_abc123",  # Same session = auto-resume
    initial_state=initial_state,
)
```

### 3.7 Files to Delete

After migration, these files are **no longer needed**:

| File | Reason for Removal |
|------|-------------------|
| `agents/graph.py` | Replaced by `SequentialAgent` + `ParallelAgent` composition |
| `agents/state.py` | Replaced by ADK `session.state` + `output_key` |
| `agents/checkpointing.py` | Replaced by ADK built-in session persistence |
| `agents/retry.py` | Replaced by ADK `max_retries` parameter |
| `agents/resume.py` | Replaced by ADK session resume |
| `langgraph/Dockerfile` | No longer needed (see new deployment) |

---

## 4. Phase 2: Replace Custom RAG with Vertex AI RAG Engine

### 4.1 Current RAG vs. Vertex AI RAG Engine

| Capability | Current (Custom) | Vertex AI RAG Engine | Benefit |
|------------|-----------------|---------------------|---------|
| **PDF Parsing** | `pypdf` (manual) | Automatic (Document AI) | Better accuracy |
| **Chunking** | Manual 512-token with 64-overlap | Configurable via `TransformationConfig` | Managed, tunable |
| **Embeddings** | Mock `[0.1]*768` or `textembedding-gecko@003` | Managed `text-embedding-005` | No code to maintain |
| **Vector Storage** | Mock in local dict | Managed Vector Search | Production-ready |
| **ANN Search** | Mock with score filtering | Managed ScaNN algorithm | 10x faster |
| **Metadata Storage** | Manual Firestore writes | Automatic corpus management | Less code |
| **Query Retrieval** | Custom `Retriever` class | `rag.Retrieval` as Gemini Tool | One-liner |

### 4.2 Setting Up Vertex AI RAG Engine

```bash
# Install required packages
pip install --upgrade google-cloud-aiplatform
pip install google-genai
```

#### 4.2.1 Create RAG Corpus & Import Documents

```python
# scripts/setup_rag_corpus.py
from vertexai import rag
import vertexai

PROJECT_ID = "sampark-gcp-project"
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)

# 1. Create RAG Corpus with embedding config
embedding_model_config = rag.RagEmbeddingModelConfig(
    vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
        publisher_model="publishers/google/models/text-embedding-005"
    )
)

rag_corpus = rag.create_corpus(
    display_name="sampark_municipal_policies",
    description="Municipal policy documents for grounding citizen issue recommendations",
    backend_config=rag.RagVectorDbConfig(
        rag_embedding_model_config=embedding_model_config
    ),
)

print(f"Created corpus: {rag_corpus.name}")
# Output: projects/{project}/locations/us-central1/ragCorpora/{corpus_id}
```

#### 4.2.2 Import Documents from Cloud Storage

```python
# 2. Import PDF documents from Cloud Storage
paths = ["gs://sampark-policy-documents/*.pdf"]

rag.import_files(
    rag_corpus.name,
    paths,
    transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(
            chunk_size=512,        # Same as current
            chunk_overlap=64,      # Same as current
        ),
    ),
)
```

#### 4.2.3 One-Line Retrieval (Replaces `rag/retriever.py` + `rag/generator.py`)

```python
# In the recommendation agent - this replaces 150+ lines of custom code
from vertexai.generative_models import Tool

rag_retrieval_tool = Tool.from_retrieval(
    retrieval=rag.Retrieval(
        source=rag.VertexRagStore(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=rag_corpus.name,
                )
            ],
            rag_retrieval_config=rag.RagRetrievalConfig(
                top_k=5,                   # Same as current
                filter=rag.Filter(
                    vector_distance_threshold=0.75  # Same threshold
                ),
            ),
        ),
    )
)

# Gemini + RAG Engine auto-handles:
# 1. Query embedding using text-embedding-005
# 2. ANN search on Vector Search
# 3. Score filtering (> 0.75)
# 4. Return top-5 chunks with metadata
```

### 4.3 Files to Delete After Migration

| File | Reason for Removal |
|------|-------------------|
| `rag/ingestor.py` | Replaced by `rag.import_files()` |
| `rag/retriever.py` | Replaced by `Tool.from_retrieval()` |
| `rag/generator.py` | Replaced by Gemini + RAG Engine |
| `rag/__init__.py` | No longer needed |
| `rag/tests/test_rag_pipeline.py` | Tests need rewriting for RAG Engine |
| `rag/tests/test_rag_pipeline_pbt.py` | Tests need rewriting for RAG Engine |
| `tools/vertex_tool.py` | Replaced by Vertex AI SDK managed calls |

### 4.4 Admin Endpoint Updates (`backend/main.py`)

The admin endpoints for RAG document management need to be updated:

```python
# OLD: Used custom Ingestor class
@app.post("/admin/knowledge-base")
async def upload_document(file: UploadFile = File(...)):
    ingestor = Ingestor(vertex_tool, fs_tool)
    success = await ingestor.ingest_pdf(doc_name, file_bytes)

# NEW: Use Vertex AI RAG Engine
@app.post("/admin/knowledge-base")
async def upload_document(file: UploadFile = File(...)):
    # Upload to Cloud Storage first
    bucket = storage_client.bucket("sampark-policy-documents")
    blob = bucket.blob(doc_name)
    blob.upload_from_string(file_bytes)
    
    # Import into RAG Engine
    rag.import_files(
        rag_corpus.name,
        [f"gs://sampark-policy-documents/{doc_name}"],
        transformation_config=rag.TransformationConfig(...),
    )
```

---

## 5. Phase 3: Maximize Google Cloud Services

### 5.1 Service Replacement Matrix

| Current Implementation | Google Cloud Service | Why This Service |
|------------------------|--------------------|-------------------|
| Custom issue type classification | **Natural Language API** | Pre-trained entity extraction, no LLM call needed |
| Manual speech-to-text | **Cloud Speech-to-Text v2** | 125+ languages, automatic punctuation |
| Manual image captioning | **Cloud Vision API** | OCR, object detection, landmark recognition |
| Manual language detection + translation | **Cloud Translation API** | 100+ languages, Glossary support for municipal terms |
| Custom notification dispatch | **Firebase Cloud Messaging** | Cross-platform push + topic-based broadcast |
| Manual session tracking | **Cloud Monitoring + Trace** | Distributed tracing, latency analysis |
| Manual log management | **Cloud Logging** | Structured logging, log-based metrics |
| Manual cron jobs | **Cloud Scheduler** | Managed cron, HTTP targets |
| Async event handling | **Cloud Tasks + Eventarc** | Guaranteed delivery, retry, deduplication |

### 5.2 Detailed Service Integrations

#### 5.2.1 Cloud Vision API (Replaces `tools/vision_tool.py`)

**Why:** Google's Vision API has pre-trained models that outperform the current Gemini-based captioning. It can detect potholes, garbage dumps, water logging from images — directly relevant to the use case.

```python
from google.cloud import vision

async def analyze_issue_image(image_bytes: bytes) -> dict:
    """Analyze citizen-submitted image using Vision API."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    
    # Multi-feature analysis in one API call
    results = await client.annotate_image({
        "image": image,
        "features": [
            {"type": "LABEL_DETECTION"},      # Detect objects (pothole, garbage)
            {"type": "OBJECT_LOCALIZATION"},   # Bounding boxes
            {"type": "TEXT_DETECTION"},        # OCR for road signs
            {"type": "LANDMARK_DETECTION"},    # Recognizable landmarks
            {"type": "IMAGE_PROPERTIES"},      # Color analysis for water/flood
        ],
    })
    
    return {
        "labels": [label.description for label in results.label_annotations],
        "objects": [obj.name for obj in results.localized_object_annotations],
        "text": results.text_annotations[0].description if results.text_annotations else "",
        "landmarks": [lm.description for lm in results.landmark_annotations],
    }
```

**Impact:** Eliminates `tools/vision_tool.py` and the Gemini-based captioning. Adds object detection (potholes, garbage piles) that directly classifies issue types.

#### 5.2.2 Cloud Speech-to-Text v2 (Replaces `tools/speech_tool.py`)

**Why:** Speech-to-Text v2 supports 125+ languages, automatic punctuation, and is optimized for phone-quality audio (govt helpline calls).

```python
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

async def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio using Speech-to-Text v2."""
    client = SpeechClient()
    
    config = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        model="latest_long",  # Optimized for long-form audio
        language_codes=["en-US", "hi-IN", "ta-IN", "te-IN"],  # Auto-detect
        features=cloud_speech.RecognitionFeatures(
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
        ),
    )
    
    request = cloud_speech.RecognizeRequest(
        recognizer=f"projects/{project_id}/locations/global/recognizers/_",
        config=config,
        content=audio_bytes,
    )
    
    response = await client.recognize(request=request)
    return " ".join(
        word.word for result in response.results for word in result.alternatives[0].words
    )
```

**Impact:** Eliminates `tools/speech_tool.py`. Better accuracy, especially for Indian languages (Hindi, Tamil, Telugu).

#### 5.2.3 Cloud Translation API (Replaces part of `agents/intake_agent.py`)

**Why:** Dedicated service for language detection + translation removes the need for a Gemini call for this simple task. 100+ languages supported.

```python
from google.cloud import translate

async def detect_and_translate(text: str) -> dict:
    """Detect language and translate to English if needed."""
    client = translate.TranslationServiceClient()
    parent = f"projects/{project_id}/locations/global"
    
    # First detect language
    detection = await client.detect_language(
        request={"parent": parent, "content": text}
    )
    detected_lang = detection.languages[0].language_code
    
    # Translate if not English
    if detected_lang != "en":
        translation = await client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "source_language_code": detected_lang,
                "target_language_code": "en",
            }
        )
        translated_text = translation.translations[0].translated_text
    else:
        translated_text = ""
    
    return {
        "language": detected_lang,
        "is_english": detected_lang == "en",
        "translated_text": translated_text,
    }
```

**Impact:** Reduces Gemini API cost. The 200-line language detection + translation logic in `intake_agent.py` becomes a 30-line service call.

#### 5.2.4 Natural Language API (Replaces Gemini-based sentiment + classification)

**Why:** Natural Language API handles entity extraction, sentiment analysis, and content classification with pre-trained models — no LLM prompt engineering needed.

```python
from google.cloud import language_v2

async def analyze_complaint_text(text: str) -> dict:
    """Analyze citizen complaint using Natural Language API."""
    client = language_v2.LanguageServiceClient()
    document = language_v2.Document(content=text, type_=language_v2.Document.Type.PLAIN_TEXT)
    
    # Multi-analysis
    [sentiment, entities, categories] = await client.annotate_text({
        "document": document,
        "features": {
            "extract_sentiment": True,
            "extract_entities": True,
            "classify_text": True,
        },
    })
    
    return {
        "sentiment_score": sentiment.document_sentiment.score,  # -1 to 1
        "sentiment_magnitude": sentiment.document_sentiment.magnitude,
        "entities": [
            {"name": e.name, "type": e.type_.name, "salience": e.salience}
            for e in entities
        ],
        "categories": [
            {"name": c.name, "confidence": c.confidence}
            for c in categories.categories
        ],
    }
```

**Impact:** Replaces the 50-line Gemini sentiment prompt in `agents/analytics_agent.py` with a single API call. More reliable than prompt-engineered sentiment.

#### 5.2.5 Firebase Cloud Messaging (Replaces part of `tools/notification_tool.py`)

**Why:** FCM is Google's cross-platform push notification service. It's free for unlimited messages and supports topic-based subscriptions, which is perfect for ward-level broadcasts.

```python
from firebase_admin import messaging

async def send_push_notification(user_token: str, title: str, body: str) -> bool:
    """Send push notification via Firebase Cloud Messaging."""
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=user_token,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="issue_updates",
            ),
        ),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                icon="/icon.png",
                badge="/badge.png",
            ),
        ),
    )
    
    try:
        response = await messaging.send_async(message)
        return True
    except Exception:
        return False  # Fall back to email/SMS
```

**Impact:** Eliminates manual Firebase HTTP calls. Adds web push + Android + iOS support for free.

#### 5.2.6 Cloud Monitoring + Trace + Logging (Replaces nothing — adds observability)

**Why:** The current system has zero observability. Adding Google Cloud's operations suite requires minimal code.

```python
# backend/middleware.py — Enhanced with Cloud Trace
from google.cloud.logging import CloudLoggingHandler
from google.cloud.trace_v1 import TraceServiceClient

import google.cloud.logging

# Auto-instrument Cloud Logging
logging_client = google.cloud.logging.Client()
logging_client.setup_logging()  # All Python logging goes to Cloud Logging

# Structured logging for better querying
logger = logging.getLogger("sampark")
logger.info("Pipeline started", extra={
    "session_id": session_id,
    "issue_type": issue_type,
    "ward_id": ward_id,
    "latency_ms": elapsed_ms,
})
```

**Impact:** Zero custom monitoring code needed. Cloud Logging + Trace auto-capture request latency, error rates, and logs. Viewable in Google Cloud Console.

#### 5.2.7 Firebase Authentication (Replaces custom JWT auth)

**Why:** Firebase Auth handles sign-up, sign-in, multi-factor auth, and OAuth providers (Google, Facebook, etc.) with built-in security.

```python
# backend/main.py — Firebase Auth middleware (replaces bcrypt + JWT)
import firebase_admin
from firebase_admin import auth

# Initialize Firebase
firebase_admin.initialize_app()

async def verify_firebase_token(token: str) -> dict:
    """Verify Firebase ID token and extract user claims."""
    try:
        decoded = auth.verify_id_token(token)
        return {
            "user_id": decoded["uid"],
            "role": decoded.get("role", "citizen"),
            "ward_ids": decoded.get("ward_ids", []),
        }
    except Exception:
        return None
```

**Impact:** Eliminates 100+ lines of JWT auth code. Supports multi-provider auth, MFA, and secure token refresh out of the box.

---

## 6. Phase 4: Deployment & Infrastructure Changes

### 6.1 Current Deployment

```
FastAPI Gateway (Cloud Run api-gateway)
    ├── LangGraph Engine (Cloud Run langgraph-engine)
    └── Notification Worker (Cloud Run notification-worker)
```

### 6.2 Target Deployment

```
FastAPI Gateway (Cloud Run api-gateway)
    └── ADK Agent Engine (Vertex AI Agent Engine)
         ├── Integrated Cloud Trace
         ├── Integrated Cloud Logging
         └── Integrated Model Monitoring
```

### 6.3 Dockerfile Changes

The `langgraph/` directory and its Dockerfile are **deleted**. Instead:

```dockerfile
# Dockerfile (root) — Single container for ADK + FastAPI
FROM python:3.12-slim

WORKDIR /app

# Install Python deps
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install .

# Copy application code
COPY agents/ ./agents/
COPY backend/ ./backend/
COPY tools/ ./tools/

# No separate langgraph container needed
# ADK runs within the same process as FastAPI

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 6.4 Cloud Run Configuration Changes

```hcl
# infra/cloud_run.tf — Simplified (no separate langgraph-engine)

# Only one service needed
resource "google_cloud_run_service" "api_gateway" {
  name     = "sampark-api-gateway"
  location = "us-central1"
  
  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/sampark-api-gateway"
        
        # ADK requires more memory for token processing
        resources {
          limits = {
            memory = "2Gi"
            cpu    = "2"
          }
        }
      }
    }
  }
}
```

### 6.5 Terraform Changes

```hcl
# infra/cloud_run.tf — REMOVED:
# - google_service_account.langgraph_engine (no longer needed)
# - google_project_iam_member.langgraph_* (consolidated into api-gateway SA)
# - google_cloud_run_service.langgraph_engine (deleted)

# infra/secrets.tf — REMOVED:
# - All langgraph-engine secrets (consolidated)

# ADDED: Vertex AI RAG Engine IAM
resource "google_project_iam_member" "api_gateway_rag_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}
```

---

## 7. Phase 5: Testing & Validation Strategy

### 7.1 Unit Tests — ADK Style

ADK provides built-in testing utilities:

```python
# tests/test_adk_intake_agent.py
from google.adk.testing import AgentTestRunner

async def test_intake_agent_basic_text():
    runner = AgentTestRunner(agent=intake_agent)
    
    result = await runner.run(
        initial_state={"query": "Pothole on MG Road"}
    )
    
    assert result.state["issue"]["type"] in KNOWN_ISSUE_TYPES
    assert "location" in result.state["issue"]
```

### 7.2 RAG Engine Tests

```python
# tests/test_rag_engine.py
from vertexai import rag

async def test_rag_corpus_query():
    response = rag.query(
        corpus_name=rag_corpus.name,
        query="pothole repair policy",
        similarity_top_k=5,
    )
    
    assert len(response.chunks) > 0
    assert all(chunk.score > 0.75 for chunk in response.chunks)
```

### 7.3 Integration Tests

```python
# tests/test_e2e_adk.py
async def test_full_pipeline():
    runner = AgentTestRunner(agent=sampark_pipeline)
    
    result = await runner.run(
        initial_state={
            "query": "Water logging in Sector 4 near the school",
            "user": {"user_id": "u1", "role": "citizen"},
        }
    )
    
    assert result.state["workflow"]["assigned_department"] is not None
    assert result.state["recommendation"]["cited_policies"] is not None
```

---

## 8. Dependency Changes

### 8.1 `pyproject.toml` Changes

```toml
[project]
dependencies = [
    # ── REMOVED ──
    # "langgraph",           → Replaced by google-adk
    # "langchain",           → Not used, deleted
    
    # ── KEPT ──
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic-settings",
    "google-cloud-firestore",
    "google-cloud-bigquery",
    "google-cloud-pubsub",
    "google-cloud-storage",
    "httpx",
    "python-multipart",
    
    # ── ADDED ──
    "google-adk",                    # Agent orchestration framework
    "google-genai",                  # Unified Gemini SDK (replaces google-generativeai)
    "google-cloud-aiplatform",       # Vertex AI RAG Engine + Vector Search
    "google-cloud-speech",           # Cloud Speech-to-Text v2
    "google-cloud-vision",           # Cloud Vision API
    "google-cloud-translate",        # Cloud Translation API
    "google-cloud-language",         # Natural Language API
    "google-cloud-logging",          # Cloud Logging
    "google-cloud-trace",            # Cloud Trace
    "firebase-admin",                # Firebase Authentication + FCM
    
    # ── REMOVED ──
    # "pyjwt",                       → Replaced by Firebase Auth
    # "bcrypt",                      → Replaced by Firebase Auth
    # "pypdf",                       → Replaced by Vertex AI RAG Engine
    # "google-generativeai",         → Replaced by google-genai
]
```

### 8.2 Python Version

```toml
requires-python = ">=3.12"  # Keep (ADK requires 3.10+)
```

---

## 9. File-by-File Migration Checklist

### Files to CREATE

| New File | Purpose | Replaces |
|----------|---------|----------|
| `agents/adk_sampark_pipeline.py` | Root ADK pipeline assembly | `agents/graph.py` |
| `agents/adk_intake_agent.py` | Intake as ADK `LlmAgent` | `agents/intake_agent.py` (update) |
| `agents/adk_validation_agent.py` | Validation as ADK `LlmAgent` | `agents/validation_agent.py` (update) |
| `agents/adk_data_intelligence.py` | Data fetching with `ParallelAgent` | `agents/data_intelligence_agent.py` (update) |
| `agents/adk_analytics_agent.py` | Analytics as ADK `LlmAgent` | `agents/analytics_agent.py` (update) |
| `agents/adk_prediction_agent.py` | Prediction as ADK `LlmAgent` | `agents/prediction_agent.py` (update) |
| `agents/adk_recommendation_agent.py` | RAG via `Tool.from_retrieval()` | `agents/recommendation_agent.py` + `rag/` |
| `agents/adk_workflow_agent.py` | Workflow as ADK `LlmAgent` | `agents/workflow_agent.py` (update) |
| `scripts/setup_rag_corpus.py` | One-time RAG corpus setup | N/A |
| `scripts/seed_policy_documents.py` | Seed sample policies | N/A |

### Files to UPDATE

| File | Update Description |
|------|-------------------|
| `backend/main.py` | Use ADK `Runner` instead of `graph.ainvoke()`, add Firebase Auth |
| `pyproject.toml` | Replace dependencies as listed in §8.1 |
| `infra/cloud_run.tf` | Remove langgraph-engine, update IAM |
| `infra/secrets.tf` | Remove langgraph-engine secrets |
| `infra/variables.tf` | Remove langgraph-engine variables |
| `.github/workflows/ci-cd.yml` | Remove langgraph-engine build/deploy steps |
| `tools/vision_tool.py` | Replace with Cloud Vision API calls |
| `tools/speech_tool.py` | Replace with Cloud Speech-to-Text v2 |
| `tools/notification_tool.py` | Add Firebase Cloud Messaging integration |

### Files to DELETE

| File | Reason |
|------|--------|
| `agents/graph.py` | Replaced by ADK pipeline |
| `agents/state.py` | Replaced by ADK session.state |
| `agents/checkpointing.py` | Replaced by ADK built-in |
| `agents/retry.py` | Replaced by ADK max_retries |
| `agents/resume.py` | Replaced by ADK session resume |
| `rag/ingestor.py` | Replaced by Vertex AI RAG Engine |
| `rag/retriever.py` | Replaced by Tool.from_retrieval() |
| `rag/generator.py` | Replaced by Gemini + RAG Engine |
| `rag/__init__.py` | No longer needed |
| `rag/tests/test_rag_pipeline.py` | Rewrite for RAG Engine |
| `rag/tests/test_rag_pipeline_pbt.py` | Rewrite for RAG Engine |
| `tools/vertex_tool.py` | Replaced by Vertex AI SDK |
| `langgraph/Dockerfile` | No longer needed |

---

## 10. Estimated Effort & Priority

### Phased Implementation Plan

| Phase | Scope | Effort | Priority | Impact |
|-------|-------|--------|----------|--------|
| **P1** | Install google-adk, create ADK agents for all 7 nodes | 4-5 days | 🔴 Critical | Core migration |
| **P2** | Set up Vertex AI RAG Engine, connect to recommendation agent | 1-2 days | 🔴 Critical | RAG replacement |
| **P3** | Update FastAPI to use ADK Runner, wire Firebase Auth | 1 day | 🟡 High | API integration |
| **P4** | Replace tools with Google Cloud managed services (Vision, Speech, Translate, NL) | 2 days | 🟡 High | Maximize GCP |
| **P5** | Add Cloud Monitoring + Trace + Logging | 0.5 day | 🟢 Medium | Observability |
| **P6** | Update deployment (Docker, Terraform, CI/CD) | 1 day | 🟢 Medium | Infrastructure |
| **P7** | Rewrite tests for ADK + RAG Engine | 1-2 days | 🟢 Medium | Quality |
| **P8** | Delete old files and clean up | 0.5 day | 🟢 Medium | Hygiene |

### Quick Wins (Day 1)

1. **Install packages** — `pip install google-adk google-genai google-cloud-aiplatform`
2. **Create ADK agents** — Migrate 1-2 simplest agents (intake, workflow) to prove the pattern
3. **Set up RAG corpus** — Run `scripts/setup_rag_corpus.py` once
4. **Wire FastAPI** — Replace `graph.ainvoke()` with `runner.run_async()`

### ROI Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Framework code** | ~500 lines (graph, state, checkpointing, retry, resume) | ~0 lines (built into ADK) | 100% less |
| **RAG code** | ~300 lines (ingestor, retriever, generator, vertex_tool) | ~10 lines (Tool.from_retrieval()) | 97% less |
| **Tool code** | ~400 lines (manual API calls) | ~100 lines (managed SDK calls) | 75% less |
| **Observability** | Zero | Full (Trace + Logging + Monitoring) | Infinite |
| **Auth code** | ~100 lines (bcrypt + JWT) | ~10 lines (Firebase Auth) | 90% less |
| **Total code reduction** | Baseline | ~1,200 fewer lines | ~40% less |

---

> **Next Steps:** This document serves as the migration blueprint. Each section corresponds to a discrete, testable phase. Start with Phase 1 (ADK agents) as the foundation, then layer on RAG Engine, managed services, and infrastructure changes.
