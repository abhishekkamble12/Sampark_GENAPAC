# Implementation Plan

## Overview

Implementation of the Sampark AI Decision Intelligence Platform — a multi-agent, RAG-grounded system built on LangGraph and Google Cloud. Tasks are ordered to respect dependencies: infrastructure first, then core state/graph, tool layer, agents (intake → validation → data intelligence → analytics → prediction → RAG → recommendation → workflow → notification), API gateway, health score service, knowledge base API, dashboard, frontend, and end-to-end tests.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1"] },
    { "wave": 2, "tasks": ["2"] },
    { "wave": 3, "tasks": ["3"] },
    { "wave": 4, "tasks": ["4"] },
    { "wave": 5, "tasks": ["5"] },
    { "wave": 6, "tasks": ["6"] },
    { "wave": 7, "tasks": ["7", "8", "9"] },
    { "wave": 8, "tasks": ["10"] },
    { "wave": 9, "tasks": ["11"] },
    { "wave": 10, "tasks": ["12"] },
    { "wave": 11, "tasks": ["13"] },
    { "wave": 12, "tasks": ["14", "15", "16"] },
    { "wave": 13, "tasks": ["17"] },
    { "wave": 14, "tasks": ["18"] }
  ]
}
```

## Tasks

- [x] 1. Project Scaffold and Cloud Infrastructure Setup
  Set up the monorepo structure, Docker containers, and Google Cloud project configuration.
  - [x] 1.1 Initialize monorepo with `backend/`, `frontend/`, `infra/`, `agents/`, `tools/`, `rag/` directories and root `pyproject.toml`
  - [x] 1.2 Create `backend/Dockerfile` and `langgraph/Dockerfile` with Python 3.12 base images
  - [x] 1.3 Create `frontend/Dockerfile` with Node 20 + React build
  - [x] 1.4 Write `infra/cloud_run.tf` Terraform configs for api-gateway, langgraph-engine, notification-worker services
  - [x] 1.5 Write `infra/pubsub.tf` creating topics: `task-created`, `task-escalated`, `health-score-updated`
  - [x] 1.6 Write `infra/bigquery.tf` creating dataset `sampark_analytics` with `issues`, `community_scores`, `predictions` tables
  - [x] 1.7 Configure GitHub Actions CI/CD workflow: test → build → push to Artifact Registry → deploy to Cloud Run
  - [x] 1.8 Configure Google Secret Manager entries for all third-party API keys

- [x] 2. GraphState and LangGraph Core
  Implement the shared state schema and LangGraph graph skeleton.
  - [x] 2.1 Implement `agents/state.py` with all `TypedDict` classes: `IssueObject`, `ValidationResult`, `AnalyticsResult`, `PredictionResult`, `RecommendationResult`, `WorkflowResult`, `ExecutionMeta`, `GraphState`
  - [x] 2.2 Implement `agents/graph.py` with `StateGraph` definition, all node registrations, and `supervisor_router` conditional edge
  - [x] 2.3 Implement parallel fan-out using `langgraph.types.Send` for `analytics_node` and `prediction_node`
  - [x] 2.4 Implement Firestore checkpoint saver: persist `GraphState` snapshot after each node completes under `sessions/{session_id}/checkpoints/{node_name}`
  - [x] 2.5 Implement resume-from-checkpoint logic: on new execution with existing `session_id`, skip nodes with existing checkpoints
  - [x] 2.6 Implement node retry wrapper: catch unhandled exceptions, wait 2s, retry up to 2 times, then set `execution.status = "failed"`
  - [x] 2.7 Write unit tests for `supervisor_router` covering all branching cases
  - [x] 2.8 Write property-based test: for any valid `GraphState`, `supervisor_router` always returns a known node name

- [x] 3. Tool Layer Implementation
  Implement all reusable tool wrappers used by agents.
  - [x] 3.1 Implement `tools/bigquery_tool.py`: `query_historical_issues(ward_id, issue_type, days)` and `write_predictions(prediction_record)`
  - [x] 3.2 Implement `tools/firestore_tool.py`: geo-radius query, document CRUD, `onSnapshot` listener interface
  - [x] 3.3 Implement `tools/maps_tool.py`: `geocode(location_str)`, `get_traffic_context(lat, lng)`, boundary validation
  - [x] 3.4 Implement `tools/weather_tool.py`: `get_current_and_forecast(lat, lng)` returning current + 48h forecast
  - [x] 3.5 Implement `tools/vision_tool.py`: `caption_image(image_bytes)` using Vertex AI Vision API
  - [x] 3.6 Implement `tools/speech_tool.py`: `transcribe(audio_bytes)` using Vertex AI Speech-to-Text
  - [x] 3.7 Implement `tools/notification_tool.py`: `send_fcm(token, message)`, `send_email(to, subject, body)`, `send_sms(phone, message)`, `send_whatsapp(phone, message)`
  - [x] 3.8 Write unit tests for each tool with mocked Google Cloud SDK responses

- [x] 4. Intake Agent
  Implement multi-modal issue intake with language detection, transcription, and classification.
  - [x] 4.1 Implement `agents/intake_agent.py` with `intake_node(state: GraphState) -> GraphState`
  - [x] 4.2 Implement modality detection (text / audio / image) from `state["query"]` and media metadata
  - [x] 4.3 Integrate `SpeechTool.transcribe()` for audio input; set `intake_error = "audio_unprocessable"` on failure
  - [x] 4.4 Integrate `VisionTool.caption_image()` for image input; set `intake_error = "image_unclassifiable"` on failure; store Cloud Storage URI
  - [x] 4.5 Implement Gemini prompt for language detection + translation; set `translation_error` flag on unsupported language
  - [x] 4.6 Implement Gemini entity extraction prompt to produce `{type, location, description}`; set `extraction_error` if location is absent
  - [x] 4.7 Implement issue type classifier mapping extracted type to the 8 canonical categories; default to `"other"` if unrecognised
  - [x] 4.8 Validate SLA: text ≤5s, audio ≤15s (enforce with `asyncio.timeout`)
  - [x] 4.9 Write unit tests for each input modality path including all error flag cases
  - [x] 4.10 Write property-based test: for any text input, `issue.type` always belongs to the 8 canonical categories

- [ ] 5. Validation Agent
  Implement credibility scoring, duplicate detection, and location verification.
  - [ ] 5.1 Implement `agents/validation_agent.py` with `validation_node(state: GraphState) -> GraphState`
  - [~] 5.2 Implement Firestore geo-radius query for duplicate detection within 500m with same `issue.type`; set `validation.duplicate`
  - [~] 5.3 Implement Maps Tool geocoding call to verify address within configured boundary; set `validation.location_verified`
  - [~] 5.4 Implement Weather Tool call for corroborating evidence
  - [~] 5.5 Implement `confidence_score` computation using the 4-component scoring formula (complaints +0.3, maps +0.3, weather +0.2, media +0.2)
  - [~] 5.6 Set `validation.status` to `"low_confidence"` if score < 0.4, else `"valid"`
  - [~] 5.7 Enforce 8-second total SLA using `asyncio.timeout`
  - [~] 5.8 Write unit tests covering: duplicate found, location invalid, low confidence, valid paths
  - [~] 5.9 Write property-based test: `confidence_score` always ∈ [0.0, 1.0] for any combination of boolean evidence flags

- [ ] 6. Data Intelligence Agent
  Implement concurrent multi-source data retrieval with per-source timeout handling.
  - [~] 6.1 Implement `agents/data_intelligence_agent.py` with `data_intelligence_node(state: GraphState) -> GraphState`
  - [~] 6.2 Implement `asyncio.gather` with `return_exceptions=True` for concurrent BigQuery, Weather, Maps calls
  - [~] 6.3 Apply 5-second `asyncio.timeout` per source; on timeout set that source's context field to `null` and log failure
  - [~] 6.4 Apply 10-second total SLA; write consolidated context to GraphState regardless of partial failures
  - [~] 6.5 Write unit tests: all sources succeed, one source times out, all sources fail
  - [~] 6.6 Write property-based test: context object always has all expected keys (values may be null) regardless of which sources fail

- [ ] 7. Analytics Agent
  Implement trend detection, geospatial clustering, sentiment analysis, and outlier detection.
  - [~] 7.1 Implement `agents/analytics_agent.py` with `analytics_node(state: GraphState) -> GraphState`
  - [~] 7.2 Implement insufficient-data guard: if historical records < 5, set `insufficient_data = true` and skip trend/cluster
  - [~] 7.3 Implement 7-day and 30-day complaint volume trend computation; handle zero-baseline case with `null` + `zero_baseline` flag
  - [~] 7.4 Implement DBSCAN-based geospatial clustering; flag wards > 1.5 std dev above citywide mean
  - [~] 7.5 Implement Gemini-based sentiment scoring over last-30-day ward reports → float [-1.0, 1.0]
  - [~] 7.6 Implement outlier detection: combined z-score of `confidence_score` + complaint frequency; flag if > 2.0 std dev
  - [~] 7.7 Read Community Health Score from BigQuery `community_scores` where `computed_at` within 25h; set `health_score_unavailable` flag if absent
  - [~] 7.8 Enforce 12-second SLA
  - [~] 7.9 Write unit tests for each computation branch including insufficient-data path
  - [~] 7.10 Write property-based test: `sentiment_score` always ∈ [-1.0, 1.0]; trend values are null or finite floats

- [ ] 8. Prediction Agent
  Implement risk forecasting models with explainability.
  - [~] 8.1 Implement `agents/prediction_agent.py` with `prediction_node(state: GraphState) -> GraphState`
  - [~] 8.2 Guard: if analytics or weather context is null, set `prediction.error = "insufficient_context"` and return early
  - [~] 8.3 Implement flood risk logistic regression model using {rainfall_forecast_48h, drainage_capacity, historical_flood_count, slope}
  - [~] 8.4 Implement road deterioration gradient boosting model using {pothole_count_30d, rainfall_7d, road_age, traffic_density}
  - [~] 8.5 Implement ARIMA(7,1,1) 7-day volume forecast per ward per category
  - [~] 8.6 Set `high_risk_alert = true` if flood_risk > 0.75 OR road_risk > 0.75
  - [~] 8.7 Attach SHAP-based explainability object: top 3 features with weights summing to 100%
  - [~] 8.8 Enforce 15-second SLA
  - [~] 8.9 Write unit tests: normal prediction, insufficient context guard, high-risk alert threshold
  - [~] 8.10 Write property-based test: `flood_risk` and `road_risk` always ∈ [0.0, 1.0]; explainability weights always sum to 100

- [ ] 9. RAG Pipeline
  Implement document ingestion, embedding, retrieval, and Gemini-grounded generation.
  - [~] 9.1 Implement `rag/ingestor.py`: PDF parsing with `pypdf`, 512-token chunks with 64-token overlap, metadata extraction (doc_name, section_heading, page_number, chunk_index, token_count)
  - [~] 9.2 Implement deterministic chunk serialisation: same PDF always produces identical chunk boundaries and metadata
  - [~] 9.3 Integrate Vertex AI `text-embedding-004` for 768-dim chunk embeddings
  - [~] 9.4 Implement Vertex AI Vector Search upsert for ingested chunks
  - [~] 9.5 Store chunk metadata in Firestore `kb_documents/{document_id}/chunks[]`
  - [~] 9.6 Handle PDF parse failure: skip document, write error entry to ingestion log, continue remaining documents
  - [~] 9.7 Implement `rag/retriever.py`: embed query, ANN search top-5 neighbours with score > 0.75, fetch metadata from Firestore
  - [~] 9.8 Return empty list + `no_policy_context = true` if zero results from Vector Search
  - [~] 9.9 Implement `rag/generator.py`: construct Gemini 1.5 Pro prompt with retrieved chunks as citations; enforce recommendation includes ≥1 document citation
  - [~] 9.10 Handle Gemini generation failure/timeout: return error to Recommendation Agent without partial output
  - [~] 9.11 Write unit tests for chunking, retrieval, and generation paths including empty-results case
  - [~] 9.12 Write property-based test: for any valid PDF, retrieving with a verbatim sentence always returns ≥1 chunk from that document

- [ ] 10. Recommendation Agent
  Implement priority-matrix-based recommendation generation with policy citations.
  - [~] 10.1 Implement `agents/recommendation_agent.py` with `recommendation_node(state: GraphState) -> GraphState`
  - [~] 10.2 Invoke RAG pipeline to retrieve top-5 policy chunks for `{issue.type} + analytics_summary`
  - [~] 10.3 Implement priority decision matrix: Critical (both risks > 0.75 + density > 5000), High (one risk > 0.75 + density), Medium/Low via analytics
  - [~] 10.4 Set `confidence_caveat = true` if `validation.status == "low_confidence"` and priority ∈ {High, Critical}
  - [~] 10.5 Set `disclaimer` field if `no_policy_context == true`
  - [~] 10.6 Produce recommendation object with all required fields: `action`, `priority`, `rationale`, `cited_policies`, `estimated_impact`
  - [~] 10.7 Enforce 20-second SLA; Supervisor sets `recommendation.error = "timeout"` on breach
  - [~] 10.8 Write unit tests covering all priority matrix branches and caveat/disclaimer conditions
  - [~] 10.9 Write property-based test: `priority` always ∈ {Critical, High, Medium, Low}; `cited_policies` always a list (may be empty only when `no_policy_context` is set)

- [ ] 11. Workflow Agent
  Implement department routing, task creation, SLA due-dates, and escalation.
  - [~] 11.1 Implement `agents/workflow_agent.py` with `workflow_node(state: GraphState) -> GraphState`
  - [~] 11.2 Implement department routing table lookup; fallback to `"Admin Review"` and set `routing_fallback` flag for unknown types
  - [~] 11.3 Create Firestore task record with `issue_id`, `assigned_department`, `priority`, `due_date`, `status: "open"` within 3s
  - [~] 11.4 Implement due-date SLA: Critical=24h, High=72h, Medium/Low=7d from `datetime.utcnow()`
  - [~] 11.5 Publish Pub/Sub event to `task-created` topic after successful task creation
  - [~] 11.6 Implement Firestore retry: 1 retry after 2s; on double failure set `workflow_error` and skip Pub/Sub
  - [~] 11.7 Log Pub/Sub publish failures with `task_id` and `issue_id` for manual replay
  - [~] 11.8 Implement escalation Cloud Function: query overdue open tasks, increment priority, publish `task-escalated`; re-publish every 24h for Critical tasks
  - [~] 11.9 Write unit tests for routing table, due-date computation, Firestore retry, Pub/Sub failure logging
  - [~] 11.10 Write property-based test: `due_date` is always in the future at creation time for any valid `priority`

- [ ] 12. Notification Agent
  Implement multi-channel notification delivery with fallback chain.
  - [~] 12.1 Implement `agents/notification_agent.py` as Pub/Sub subscriber consuming `task-created` and `task-escalated` topics
  - [~] 12.2 Implement Firestore `onSnapshot` listener for `tasks` collection `status` field changes
  - [~] 12.3 Implement channel selection: read `preferred_channel` from user Firestore profile; default to email
  - [~] 12.4 Implement notification dispatch for all lifecycle events: Issue Received, Engineer Assigned, Resolved, Escalated
  - [~] 12.5 Implement fallback chain: FCM/WhatsApp → retry once (30s) → Email; Email → retry once (30s) → SMS
  - [~] 12.6 Notify assigned Government Officer on escalation; fallback to Admin Review distribution address if no officer assigned
  - [~] 12.7 Log all notification attempts to Firestore `notifications` collection with channel, status, attempt_count, failure_reason
  - [~] 12.8 Enforce 60-second dispatch SLA from trigger event
  - [~] 12.9 Write unit tests for each lifecycle event and each fallback channel path
  - [~] 12.10 Write property-based test: for any notification event, at least one delivery attempt is always logged to Firestore

- [ ] 13. FastAPI Gateway
  Implement the API Gateway with JWT auth, rate limiting, schema validation, SSE streaming, and request logging.
  - [~] 13.1 Implement `backend/main.py` FastAPI app with all routes from the API design (Section 5.1)
  - [~] 13.2 Implement JWT middleware: validate RS256 signature, `exp`, and `user_id`; return HTTP 401 on any failure
  - [~] 13.3 Implement Redis (Memorystore) sliding-window rate limiter: 60 requests per 60s per `user_id`; return HTTP 429 + `Retry-After`
  - [~] 13.4 Implement Pydantic request schemas for all POST endpoints; return HTTP 422 with field-level violations on failure
  - [~] 13.5 Implement `GET /chat/stream/{session_id}` SSE endpoint: open stream, forward agent progress events, close on pipeline completion or client disconnect
  - [~] 13.6 Implement RBAC middleware: enforce ward_ids scope for community_leader and government_officer roles; return HTTP 403 on out-of-scope requests
  - [~] 13.7 Implement request logging middleware writing all requests to Cloud Logging with timestamp, user_id, endpoint, method, status_code, latency_ms
  - [~] 13.8 Implement `/auth/login` endpoint producing JWTs via Firebase Authentication
  - [~] 13.9 Implement `/health` endpoint returning service status
  - [~] 13.10 Write unit tests for all JWT rejection cases, rate limiting, and RBAC enforcement
  - [~] 13.11 Write property-based test: any request with a missing or malformed JWT always returns HTTP 401

- [ ] 14. Community Health Score Service
  Implement the scheduled score computation and health score API endpoint.
  - [~] 14.1 Implement `functions/health_score.py` Cloud Function with `compute_health_score(sub_scores)` using weight rebalancing for missing sub-scores
  - [~] 14.2 Implement BigQuery sub-score derivation: count resolved vs. open issues per category per ward over 90 days, min-max normalize to 0–100
  - [~] 14.3 Implement transition detection: flag ward as `at_risk = true` when score crosses below 60; remove flag when score crosses 60 or above
  - [~] 14.4 Publish Pub/Sub `health-score-updated` event on at-risk transitions
  - [~] 14.5 Implement BigQuery write with last-known-score fallback on write failure
  - [~] 14.6 Configure Cloud Scheduler to trigger daily at 00:00 UTC
  - [~] 14.7 Implement `GET /analytics/ward/{ward_id}/health-score` endpoint returning 90-day history; HTTP 404 if ward not found
  - [~] 14.8 Write unit tests for weight rebalancing, transition detection, and at-risk flagging
  - [~] 14.9 Write property-based test: `compute_health_score` always returns a value ∈ [0.0, 100.0]; available weights always sum to 1.0

- [ ] 15. Knowledge Base Admin API
  Implement document upload, deletion, and listing for the RAG knowledge base.
  - [~] 15.1 Implement `POST /admin/knowledge-base` endpoint: validate PDF ≤50MB, store to Cloud Storage, trigger RAG ingestion, return `document_id` within 5s
  - [~] 15.2 Implement `DELETE /admin/knowledge-base/{document_id}` endpoint: remove Cloud Storage file, delete all Vector Search embeddings for the document, remove Firestore metadata
  - [~] 15.3 Implement `GET /admin/knowledge-base` endpoint: list all documents with `document_id`, `name`, `status`, `chunk_count`, `ingested_at`
  - [~] 15.4 Enforce Admin-only RBAC on all `/admin/knowledge-base` endpoints
  - [~] 15.5 Write unit tests for upload validation (size limit, non-PDF rejection), delete cascade, and listing
  - [~] 15.6 Write integration test: upload a PDF → verify chunks appear in Vector Search → delete → verify chunks removed

- [ ] 16. Dashboard and BigQuery View
  Implement the `sampark_dashboard_view` and dashboard API endpoint.
  - [~] 16.1 Create BigQuery SQL view `sampark_dashboard_view` joining `issues`, `community_scores`, `predictions`, `tasks` aggregated by `ward_id` and date
  - [~] 16.2 View must expose: `complaint_volume`, `avg_health_score`, `max_flood_risk`, `max_road_risk`, `resolution_rate`, `open_critical_count` without additional joins
  - [~] 16.3 Implement `GET /analytics/dashboard` endpoint: return latest health score, risk heatmap data, 7-day trend, top 5 Critical open issues for requesting user's ward scope
  - [~] 16.4 Implement Firestore `onSnapshot` → SSE push for real-time task status updates to dashboard clients within 5s
  - [~] 16.5 Enforce ward-scope filtering from JWT `ward_ids` claim on all dashboard data
  - [~] 16.6 Write query performance test: `sampark_dashboard_view` query completes in < 3s on 100,000-row dataset
  - [~] 16.7 Write unit tests for ward-scope filtering and SSE event emission

- [ ] 17. Frontend React Application
  Implement the citizen portal and government officer dashboard.
  - [~] 17.1 Scaffold React 18 app with React Router, TanStack Query, and Tailwind CSS
  - [~] 17.2 Implement login page with Firebase Authentication (email/password + Google OAuth)
  - [~] 17.3 Implement citizen issue submission form: text, audio upload, image upload with progress indicator
  - [~] 17.4 Implement real-time pipeline progress view using `GET /chat/stream/{session_id}` SSE connection
  - [~] 17.5 Implement Government Officer dashboard: health score card, risk heatmap (Google Maps JS API), 7-day complaint trend chart (Recharts), top-5 Critical issues panel
  - [~] 17.6 Implement real-time task status updates on dashboard using SSE connection to `/analytics/dashboard/stream`
  - [~] 17.7 Implement Admin knowledge base management page: upload, list, delete documents
  - [~] 17.8 Implement ward-scope access guard: redirect to 403 page if JWT ward_ids mismatch
  - [~] 17.9 Implement responsive layout with WCAG 2.1 AA accessibility compliance
  - [~] 17.10 Write component unit tests with React Testing Library for all major views

- [ ] 18. End-to-End Integration and Performance Testing
  Validate the complete pipeline, SLAs, and non-functional requirements.
  - [~] 18.1 Write end-to-end test: citizen submits text issue → validate → analytics → prediction → recommendation → task created → notification dispatched
  - [~] 18.2 Write end-to-end test: audio issue submission with mocked Speech-to-Text
  - [~] 18.3 Write end-to-end test: pipeline resume from checkpoint after simulated node failure
  - [~] 18.4 Write Locust load test: 100 concurrent users, verify p95 pipeline completion ≤ 60 seconds
  - [~] 18.5 Write latency test: dashboard initial load ≤ 3s for 100,000-record dataset
  - [~] 18.6 Write security test: verify all JWT rejection cases, rate limiting, and RBAC enforcement across all endpoints
  - [~] 18.7 Write RAG evaluation: for each ingested policy document, verify verbatim-sentence retrieval returns ≥1 correct chunk
  - [~] 18.8 Verify SSE pipeline progress events appear within 5 seconds of each node completing

## Notes

- All Python code targets Python 3.12. All Node/React code targets Node 20 / React 18.
- Google Cloud services: Cloud Run, Firestore, BigQuery, Pub/Sub, Vertex AI, Cloud Storage, Memorystore (Redis), Secret Manager, Cloud Logging, Cloud Scheduler.
- LangGraph version must support `StateGraph`, `Send` API, and Firestore checkpoint savers.
- All agent SLAs are enforced with `asyncio.timeout`; SLA breaches set error flags in GraphState rather than crashing.
- Property-based tests use the `hypothesis` library.
- Mocked external APIs (Vertex AI, Maps, Weather, Twilio, SendGrid) for all unit/integration tests; no real API calls in CI.
