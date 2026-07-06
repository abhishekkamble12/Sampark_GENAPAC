# Sampark AI Architecture — FREE Stack (No GCP Billing Required)

Sampark AI is a multi-agent, RAG-grounded Decision Intelligence Platform powered entirely by **free Google technologies** and open-source software. No Google Cloud billing account is needed.

---

## Architecture Overview

```mermaid
graph TD
    %% Citizen & Officer Interfaces
    Citizen[Citizen Web App]
    Officer[Command Center Dashboard]
    
    %% API Gateway
    Gateway[FastAPI Gateway]
    
    %% Core Orchestration
    subgraph AI Reasoning Engine
        LangGraph[LangGraph Orchestrator]
        Agent1(Intake Agent)
        Agent2(Validation Agent)
        Agent3(Prediction Agent)
        Agent4(Recommendation Agent)
        Agent5(Workflow Agent)
        
        LangGraph --> Agent1
        LangGraph --> Agent2
        LangGraph --> Agent3
        LangGraph --> Agent4
        LangGraph --> Agent5
    end
    
    %% Free Stack Infrastructure
    subgraph FREE Stack
        Gemini[Gemini API<br/>(Google AI Studio)]
        FAISS[(FAISS<br/>Vector Search)]
        SQLite[(SQLite<br/>Database)]
        DuckDB[(DuckDB<br/>Analytics)]
        Queue[Async Queue<br/>(In-memory)]
    end
    
    %% Connections
    Citizen -- Submit Issue --> Gateway
    Officer -- Dashboard --> Gateway
    Gateway -- Triggers --> LangGraph
    
    Agent4 -- RAG Search --> FAISS
    LangGraph -- Read/Write --> SQLite
    Gateway -- Analytics --> DuckDB
    Agent5 -- Events --> Queue
```

## Key Differences from GCP Architecture

| Original (Paid GCP) | FREE Replacement | Why |
| :--- | :--- | :--- |
| **Vertex AI Gemini** | **Gemini API (AI Studio)** | Free API key, no billing |
| **Vertex AI Vector Search** | **FAISS** | Open source, runs locally |
| **Firestore** | **SQLite** | Zero-config, embedded DB |
| **BigQuery** | **DuckDB** | In-process analytics, free |
| **Cloud Pub/Sub** | **Python asyncio.Queue** | No infrastructure needed |
| **Cloud Run** | **uvicorn / Render** | Direct Python deployment |
| **Secret Manager** | **.env file** | Simple, effective |

---

## How It Works

### 1. API Gateway (FastAPI)
Handles all HTTP traffic from the React frontend. Authenticates users via JWT, applies rate limiting, and routes requests to the LangGraph pipeline.

### 2. Orchestration (LangGraph)
Multi-agent pipeline with shared GraphState. Each agent enriches the state with its specific output:
- **Intake Agent** → classifies issue, extracts location
- **Validation Agent** → checks duplicates, computes confidence
- **Data Intelligence Agent** → gathers context
- **Analytics Agent** → trend detection, sentiment analysis
- **Prediction Agent** → risk forecasting
- **Recommendation Agent** → RAG-grounded policy recommendations
- **Workflow Agent** → department assignment, task creation

### 3. Persistence (SQLite)
Local database storing all operational data: issues, tasks, sessions, community scores, knowledge base chunks. Zero configuration needed.

### 4. Analytics (DuckDB)
In-process analytical database for dashboard queries: community health scores, ward risk heatmaps, trend analysis.

### 5. Vector Search (FAISS + Gemini Embeddings)
Policy documents are embedded using the free Gemini Embeddings API and stored in a local FAISS index for semantic search.

### 6. Event Dispatch (Python Queue)
In-memory async queue replaces Cloud Pub/Sub for decoupled notification dispatching.

---

## Deployment

### Unified Docker Container (Recommended)

The entire platform is packaged into a single multi-stage Docker image:

```text
┌──────────────────────────────────────────────────────┐
│                  Docker Container                      │
│                                                        │
│  Port 8080 ─── nginx ─── React SPA (built via Vite)    │
│  Port 8000 ─── uvicorn ── FastAPI Backend              │
│                  │                                      │
│                  ├── LangGraph Agent Pipeline           │
│                  ├── SQLite (operational DB)            │
│                  ├── DuckDB (analytics)                 │
│                  └── FAISS (vector search)              │
└──────────────────────────────────────────────────────┘
```

```bash
docker build -t sampark-ai .
docker run -p 8080:8080 -p 8000:8000 sampark-ai
```

### CI/CD Pipeline

On push to `main` or `version3`, `.github/workflows/docker.yml`:
1. Runs `pytest` test suite
2. Builds the unified Docker image (with GitHub Actions cache)
3. Pushes to Docker Hub with tags: `latest`, branch name, commit SHA
4. Runs a smoke test (health endpoint check)
5. (Optional) Triggers Render deployment via webhook

### Legacy Deployments

| Platform | Component | Method |
| :--- | :--- | :--- |
| **Render** | Backend | `uvicorn backend.main:app --host 0.0.0.0 --port 10000` |
| **Railway** | Backend | Same as Render |
| **Vercel** | Frontend | Build: `npm run build`, Output: `dist` |
| **HuggingFace Spaces** | Full app | Docker-based deployment |
