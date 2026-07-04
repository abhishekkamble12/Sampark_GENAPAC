# Sampark AI Architecture & Production Readiness

Sampark AI is designed with a highly scalable, event-driven architecture utilizing Google Cloud's enterprise data and AI stack. 

> [!IMPORTANT]
> **Demo Disclaimer**: For hackathon reliability and speed, this live demo runs in **local deterministic mode**. It uses in-memory mock databases and seeded policy documents to guarantee a bulletproof presentation. However, the application uses the exact same interfaces that switch seamlessly to the Google Cloud services detailed below when `APP_MODE=production`.

## Clean Architecture Diagram

```mermaid
graph TD
    %% Citizen & Officer Interfaces
    Citizen[Citizen Mobile/Web App]
    Officer[Command Center Dashboard]
    
    %% API Gateway
    Gateway[FastAPI Gateway\n(CORS, JWT Auth, Rate Limiting)]
    
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
    
    %% Google Cloud Infrastructure
    subgraph GCP Production Infra
        CloudRun[Google Cloud Run\n(Scalable Compute)]
        Vertex[Vertex AI Search\n(RAG / Policy Retrieval)]
        Firestore[(Firestore)\n(Task & Session Persistence)]
        BigQuery[(BigQuery)\n(Geospatial Analytics)]
        PubSub[Cloud Pub/Sub\n(Event Dispatch)]
        SecretManager[Secret Manager\n(Credentials)]
    end
    
    %% Connections
    Citizen -- Submit Issue --> Gateway
    Officer -- SSE Stream / API --> Gateway
    Gateway -- Deployed on --> CloudRun
    Gateway -- Triggers --> LangGraph
    
    Agent4 -- Retrieves Policy --> Vertex
    Agent5 -- Dispatches Task --> PubSub
    
    LangGraph -- Read/Write State --> Firestore
    Gateway -- Fetch Analytics --> BigQuery
    CloudRun -- Secure Access --> SecretManager
```

## Production Path Breakdown

### 1. API Gateway (FastAPI)
Handles all incoming traffic from the React frontend. In production, this layer enforces CORS policies, validates JWT tokens for municipal officers, and applies rate limiting to prevent spam submissions from public endpoints.

### 2. Orchestration (LangGraph on Cloud Run)
The core AI reasoning pipeline is orchestrated via LangGraph, enabling multi-agent handoffs. The entire backend is containerized and deployed on **Google Cloud Run**, allowing the service to scale from zero to thousands of concurrent citizen requests seamlessly.

### 3. Persistence (Firestore)
**Firestore** is used as the primary operational database. It stores the live LangGraph state (enabling long-running human-in-the-loop workflows) and maintains the active queue of civic issues and task statuses.

### 4. Analytics & Geospatial Risk (BigQuery)
For the Command Center Dashboard, raw issue data is synced to **BigQuery**. This allows for complex, high-performance analytical queries (e.g., calculating the moving 7-day average of community health scores and aggregating geospatial risk by ward) without bogging down the operational database.

### 5. Grounded RAG (Vertex AI Search)
The Recommendation Agent relies on **Vertex AI Search** to retrieve relevant civic policies, SLAs, and standard operating procedures. This ensures that all AI-generated actions are strictly grounded in official municipal documentation.

### 6. Event Dispatch (Pub/Sub)
When the Workflow Agent finalizes a task, it dispatches an event to **Cloud Pub/Sub**. This allows decoupled downstream systems (e.g., third-party SMS gateways for citizen updates, or legacy DPW ticketing systems) to subscribe to civic events asynchronously.

### 7. Security (Secret Manager)
All LLM API keys, database credentials, and signing secrets are securely injected at runtime via **Google Secret Manager**.
