# 🛠 Google Tools & Services — Sampark AI Platform

> **Reference Guide:** Every Google Cloud service that can power, enhance, or differentiate the Sampark AI Decision Intelligence Platform.
>
> Each entry includes: **What it is** → **How to use in Sampark** → **Where to integrate**

---

## 📋 Quick-Reference Table

| # | Service | Category | Status | Priority |
|---|---|---|---|---|
| 1 | **Vertex AI Gemini API** | AI / ML | ✅ Used | 🔴 Critical |
| 2 | **Vertex AI Agent Builder (ADK)** | AI / ML | ❌ New | 🔴 Critical |
| 3 | **Vertex AI Vector Search** | AI / ML | ⚠️ Partial | 🔴 Critical |
| 4 | **Vertex AI Imagen** | AI / ML | ❌ New | 🟡 Medium |
| 5 | **Vertex AI Vision API** | AI / ML | ✅ Used | 🔴 Critical |
| 6 | **Vertex AI Speech-to-Text** | AI / ML | ✅ Used | 🔴 Critical |
| 7 | **Vertex AI Text-to-Speech** | AI / ML | ❌ New | 🟡 Medium |
| 8 | **Natural Language API** | AI / ML | ❌ New | 🟡 Medium |
| 9 | **Cloud Translation API** | AI / ML | ❌ New | 🟡 Medium |
| 10 | **Document AI** | AI / ML | ❌ New | 🟢 Nice |
| 11 | **Dialogflow CX** | AI / ML | ❌ New | 🟡 Medium |
| 12 | **BigQuery ML** | Data / Analytics | ❌ New | 🔴 Critical |
| 13 | **BigQuery** | Data / Analytics | ✅ Used | 🔴 Critical |
| 14 | **Pub/Sub** | Data / Messaging | ✅ Used | 🔴 Critical |
| 15 | **Dataflow** | Data / Processing | ❌ New | 🟡 Medium |
| 16 | **Cloud Composer** | Orchestration | ❌ New | 🟢 Nice |
| 17 | **Looker Studio** | BI / Dashboards | ❌ New | 🟡 Medium |
| 18 | **Firestore** | Database | ✅ Used | 🔴 Critical |
| 19 | **Memorystore (Redis)** | Caching | ❌ New | 🟡 Medium |
| 20 | **AlloyDB / Cloud SQL** | Database | ❌ New | 🟢 Nice |
| 21 | **Cloud Storage** | Storage | ✅ Used | 🔴 Critical |
| 22 | **Cloud Run** | Compute | ✅ Used | 🔴 Critical |
| 23 | **Cloud Functions 2nd Gen** | Serverless | ✅ Used | 🟡 Medium |
| 24 | **Cloud Scheduler** | Cron / Jobs | ✅ Used | 🟡 Medium |
| 25 | **Eventarc** | Event-Driven | ❌ New | 🟡 Medium |
| 26 | **Cloud Tasks** | Async Queues | ❌ New | 🟡 Medium |
| 27 | **Google Maps Platform** | Location | ✅ Used | 🔴 Critical |
| 28 | **Firebase Authentication** | Auth | ❌ New | 🔴 Critical |
| 29 | **Firebase Genkit** | AI Framework | ❌ New | 🔴 Critical |
| 30 | **Secret Manager** | Security | ✅ Used | 🔴 Critical |
| 31 | **Cloud KMS** | Security | ❌ New | 🟢 Nice |
| 32 | **Cloud Logging** | Observability | ✅ Used | 🟡 Medium |
| 33 | **Cloud Monitoring** | Observability | ⚠️ Partial | 🟡 Medium |
| 34 | **Cloud Build** | CI/CD | ✅ Used | 🟡 Medium |
| 35 | **Artifact Registry** | CI/CD | ✅ Used | 🟡 Medium |
| 36 | **Cloud Deploy** | CI/CD | ❌ New | 🟢 Nice |
| 37 | **Cloud Armor** | Security | ❌ New | 🟢 Nice |
| 38 | **Cloud Load Balancing** | Networking | ❌ New | 🟢 Nice |
| 39 | **Cloud CDN** | Networking | ❌ New | 🟢 Nice |
| 40 | **Security Command Center** | Security | ❌ New | 🟢 Nice |

**Legend:** ✅ Used / ⚠️ Partial / ❌ New | 🔴 Critical / 🟡 Medium / 🟢 Nice

---

## 🧠 Category 1: AI & Machine Learning

---

### 1. Vertex AI Gemini API

| Field | Detail |
|---|---|
| **Service** | `vertex-ai` — Gemini 1.5 Pro / 2.0 Flash / 2.0 Pro |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/vertex-ai](https://cloud.google.com/vertex-ai) |

**What it is:** Google's most capable multimodal AI model. Supports text, image, audio, video, and code understanding. 1M+ token context window, function calling, structured output, and system instructions.

**How to use in Sampark:**

| Agent / Component | What Gemini Does |
|---|---|
| **Intake Agent** | Entity extraction from citizen reports, language detection & translation |
| **Analytics Agent** | Sentiment scoring on complaint descriptions (returns -1.0 to 1.0) |
| **Recommendation Agent** | Grounded policy-backed recommendation generation via RAG |
| **Generator (RAG)** | Gemini 1.5 Pro prompt with retrieved policy chunks as citations |
| **Validation Agent** (optional) | Cross-verify extracted location vs. description |

**Where to integrate:**
- `agents/intake_agent.py` — `_run_gemini()` helper, `_LANG_DETECT_PROMPT`, `_EXTRACT_PROMPT`
- `agents/analytics_agent.py` — `_SENTIMENT_PROMPT` for scoring
- `rag/generator.py` — `_GENERATE_PROMPT` with policy chunk citations
- `agents/graph.py` — `genai.configure()` and `GenerativeModel("gemini-1.5-pro-latest")`

**🏆 Hackathon Tip:** Use Gemini 2.0 Flash for latency-sensitive agents (Intake, Validation) and Gemini 1.5 Pro for reasoning-heavy agents (Recommendation). Use `response_schema` / `response_mime_type="application/json"` to enforce structured JSON output instead of regex parsing.

---

### 2. Vertex AI Agent Builder (ADK)

| Field | Detail |
|---|---|
| **Service** | `vertex-ai-agent-builder` — Agent Development Kit (ADK) |
| **Status** | ❌ **New — High Impact** |
| **Docs** | [cloud.google.com/agent-development-kit](https://cloud.google.com/agent-development-kit) |

**What it is:** Google's open-source framework for building multi-agent AI systems. Provides tight integration with Gemini models, tool/function calling, state management, memory, and orchestration — an alternative/direct competitor to LangGraph for this hackathon.

**How to use in Sampark:**

| Component | ADK Role |
|---|---|
| **Supervisor Agent** | High-level orchestrator using ADK's `Agent` class routing |
| **Specialized Agents** | Each of the 8 agents as ADK sub-agents with tool bindings |
| **Memory & State** | ADK's built-in memory management replaces custom checkpointing |
| **Tool Calling** | ADK-native tool declarations replace the tool wrapper pattern |

**Where to integrate:**

> **Option A — Replace LangGraph with ADK:**
> ```
> agents/adk/
>   supervisor_agent.py    # Main orchestrator
>   intake_agent.py        # Sub-agent
>   validation_agent.py    # Sub-agent
>   recommendation_agent.py
>   ...
> ```
>
> **Option B — Hybrid: ADK wraps LangGraph:**
> ADK Agent calls the LangGraph pipeline as a single tool/action while ADK handles cross-session memory, user state, and multi-turn conversations.

**🏆 Hackathon Tip:** The hackathon is **specifically about ADK** ("Your project must be built using the Agent Development Kit"). Converting your LangGraph pipeline to ADK is the single highest-impact change. Even wrapping parts of LangGraph with ADK shows the judges you understand both frameworks.

---

### 3. Vertex AI Vector Search

| Field | Detail |
|---|---|
| **Service** | `vertex-ai-vector-search` — ANN vector similarity search |
| **Status** | ⚠️ **Partially integrated** (mocked in `VertexSearchTool`) |
| **Docs** | [cloud.google.com/vertex-ai/docs/vector-search](https://cloud.google.com/vertex-ai/docs/vector-search) |

**What it is:** High-scale, low-latency approximate nearest neighbor (ANN) vector database for semantic search. Uses ScaNN algorithm. Supports streaming updates, filtering, and embedding-based retrieval at scale.

**How to use in Sampark:**

| Component | Vector Search Role |
|---|---|
| **RAG Pipeline** | Store 768-dim embeddings of policy documents |
| **Retriever** | ANN search top-5 chunks with score threshold 0.75 |
| **Intake Agent** (optional) | Semantic similarity matching for issue type classification |

**Where to integrate:**
- `tools/vertex_tool.py` — Replace mock `[[0.1] * 768]` with real Vertex AI `text-embedding-004` model
- `rag/ingestor.py` — Real upsert to `MatchingEngineIndexEndpoint`
- `rag/retriever.py` — Real `find_neighbors()` calls
- `infra/bigquery.tf` — Deploy Vector Search index via Terraform

**🏆 Hackathon Tip:** Combine **BigQuery Vector Search** (native BQ embeddings + ANN) with **Vertex AI Vector Search** for different use cases: BQ for high-volume structured + vector hybrid queries, Vertex for pure semantic document retrieval.

---

### 4. Vertex AI Imagen

| Field | Detail |
|---|---|
| **Service** | `vertex-ai-imagen` — Text-to-image / Image editing |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/vertex-ai/generative-ai/docs/image](https://cloud.google.com/vertex-ai/generative-ai/docs/image) |

**What it is:** Google's most advanced text-to-image generation model. Generate, edit, and caption images. Supports up to 4x resolution enhancement, inpainting, outpainting.

**How to use in Sampark:**

| Use Case | What to Generate |
|---|---|
| **Dashboard** | Generate a heatmap visualization from prediction data |
| **Report Generation** | Generate before/after mockups of repaired roads, cleaned areas |
| **Citizen UI** | Generate illustrative images for issue categories (flood, pothole, etc.) |
| **Admin** | Generate visual summaries of monthly analytics |

**Where to integrate:**
- `backend/main.py` — New endpoint `POST /admin/generate-visual`
- `frontend/` — Admin dashboard page for report visualization

**🏆 Hackathon Tip:** This is a **wow factor** for demos. Show the AI generating a "predicted future state" image of a repaired road alongside the recommendation — incredibly compelling for judges.

---

### 5. Vertex AI Vision API

| Field | Detail |
|---|---|
| **Service** | `vertex-ai-vision` — Image understanding, object detection, OCR |
| **Status** | ✅ **Already integrated** in `VisionTool` |
| **Docs** | [cloud.google.com/vertex-ai/vision](https://cloud.google.com/vertex-ai/vision) |

**What it is:** Pre-trained and custom vision models for object detection, image classification, OCR, and image captioning. Now deeply integrated with Gemini multimodal capabilities.

**How to use in Sampark:**

| Component | Vision API Role |
|---|---|
| **Intake Agent** | Caption uploaded images to extract issue details |
| **Validation Agent** | Cross-reference image content with reported description |
| **Dashboard** | Display image evidence alongside issues |

**Where to integrate:**
- `tools/vision_tool.py` — `caption_image()` already calls Gemini; can add `detect_objects()` and `extract_text()` for deeper analysis

**🏆 Hackathon Tip:** Add object detection to automatically count potholes, measure flood water levels, or detect garbage pile sizes from citizen photos — quantified evidence is more impressive than captions.

---

### 6. Vertex AI Speech-to-Text

| Field | Detail |
|---|---|
| **Service** | `speech-to-text` — Audio transcription |
| **Status** | ✅ **Already integrated** in `SpeechTool` |
| **Docs** | [cloud.google.com/speech-to-text](https://cloud.google.com/speech-to-text) |

**What it is:** High-accuracy speech recognition supporting 125+ languages. Supports real-time streaming, domain-specific vocabulary, automatic punctuation, and speaker diarization.

**How to use in Sampark:**

| Component | Speech-to-Text Role |
|---|---|
| **Intake Agent** | Transcribe voice messages from citizens |
| **Multi-Channel** | Process WhatsApp audio notes, voice recordings |

**Where to integrate:**
- `tools/speech_tool.py` — Already uses v2 API with `auto_decoding_config`

**🏆 Hackathon Tip:** Add **Indian language support** (Hindi, Tamil, Telugu, Bengali, Marathi) — this is a huge differentiator for a "community issue" platform in India. Use `language_code="hi-IN"` as fallback.

---

### 7. Vertex AI Text-to-Speech

| Field | Detail |
|---|---|
| **Service** | `text-to-speech` — Natural speech synthesis |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/text-to-speech](https://cloud.google.com/text-to-speech) |

**What it is:** Convert text to natural-sounding speech using WaveNet and Google's latest neural voice models. 380+ voices across 50+ languages. Custom voice creation available.

**How to use in Sampark:**

| Use Case | What to Synthesize |
|---|---|
| **Notifications** | Voice messages for citizen updates via WhatsApp |
| **Dashboard** | Accessibility: screen-reader-friendly dashboard |
| **Multi-Lingual** | Deliver updates in the citizen's preferred language |

**Where to integrate:**
- `tools/speech_tool.py` — Add `synthesize_speech(text, language_code)` method
- `agents/notification_agent.py` — Voice notification channel

**🏆 Hackathon Tip:** For illiterate citizens, voice notifications are more accessible than SMS. Demo this as an inclusive design choice.

---

### 8. Natural Language API

| Field | Detail |
|---|---|
| **Service** | `natural-language` — Pre-trained NLP models |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/natural-language](https://cloud.google.com/natural-language) |

**What it is:** Pre-trained models for entity extraction, sentiment analysis, content classification, and syntax analysis. Supports 10+ languages.

**How to use in Sampark:**

| Component | NL API Role |
|---|---|
| **Intake Agent** | Entity extraction as fast fallback when Gemini is unavailable |
| **Analytics Agent** | Quick sentiment analysis for large batches (more cost-effective than Gemini) |
| **Admin** | Categorize issue content, auto-tagging |

**Where to integrate:**
- `agents/intake_agent.py` — Conditional path: NL API for entity extraction, Gemini for complex cases
- `agents/analytics_agent.py` — Batch sentiment analysis on 1000+ complaints

**🏆 Hackathon Tip:** Use NL API for **high-volume, low-complexity** tasks and Gemini for **low-volume, high-complexity** tasks. This shows architectural maturity.

---

### 9. Cloud Translation API

| Field | Detail |
|---|---|
| **Service** | `translate` — Neural machine translation |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/translate](https://cloud.google.com/translate) |

**What it is:** Fast, dynamic machine translation supporting 100+ language pairs. Supports AutoML for custom domain-specific models. 2M char/month free tier.

**How to use in Sampark:**

| Component | Translation API Role |
|---|---|
| **Intake Agent** | Translate non-English citizen reports to English for downstream agents |
| **Notification Agent** | Translate government responses back to citizen's language |
| **Dashboard** | Multi-lingual dashboard support |

**Where to integrate:**
- `agents/intake_agent.py` — Replace regex/language prompt with dedicated Translation API call
- `agents/workflow_agent.py` — Translate task descriptions

**🏆 Hackathon Tip:** For an India-centric hackathon, supporting Hindi, Tamil, Telugu, Kannada, Marathi, Bengali, etc. is a massive differentiator. Demo a Hindi voice input flowing through the pipeline end-to-end.

---

### 10. Document AI

| Field | Detail |
|---|---|
| **Service** | `document-ai` — Document understanding & OCR |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/document-ai](https://cloud.google.com/document-ai) |

**What it is:** AI-powered document processing platform. Extract, classify, and enrich data from documents (PDFs, images, forms). Specialized processors for invoices, receipts, identity documents, contracts.

**How to use in Sampark:**

| Use Case | Document AI Role |
|---|---|
| **Policy Ingestion** | Parse municipal PDF documents, extract structured policy rules |
| **RAG Pipeline** | High-quality OCR for scanned government documents |
| **Citizen Uploads** | Extract information from citizen-submitted documents |

**Where to integrate:**
- `rag/ingestor.py` — Replace `pypdf` with Document AI's `OCR Processor` + `Custom Extractor`
- `backend/main.py` — `POST /admin/knowledge-base` with Document AI processing step

**🏆 Hackathon Tip:** Many government documents are scanned PDFs (images, not text). Document AI's OCR is significantly better than `pypdf`. This ensures your RAG pipeline works on real-world data.

---

### 11. Dialogflow CX

| Field | Detail |
|---|---|
| **Service** | `dialogflow-cx` — Conversational AI / Virtual agents |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/dialogflow/cx](https://cloud.google.com/dialogflow/cx) |

**What it is:** Advanced conversational AI platform for building virtual agents with state management, natural language understanding, and generative AI fallback. Supports voice and text channels, multi-turn conversations, and agent-to-agent handoff.

**How to use in Sampark:**

| Component | Dialogflow CX Role |
|---|---|
| **Citizen Chat** | Frontline conversational interface before escalating to agents |
| **WhatsApp Bot** | Handle WhatsApp conversations, collect initial issue details |
| **Voice Channel** | Interactive Voice Response (IVR) for phone call intake |

**Where to integrate:**
- `backend/main.py` — Dialogflow CX webhook endpoint that invokes the LangGraph pipeline
- `frontend/` — Dialogflow CX Messenger widget for citizen chat

**🏆 Hackathon Tip:** Use Dialogflow CX as the **first touchpoint** to collect initial information, then escalate to the LangGraph pipeline for complex reasoning. Judges love seeing this kind of tiered architecture.

---

### 12. BigQuery ML

| Field | Detail |
|---|---|
| **Service** | `bigquery-ml` — ML models in BigQuery |
| **Status** | ❌ **New — High Impact** |
| **Docs** | [cloud.google.com/bigquery/docs/machine-learning](https://cloud.google.com/bigquery/docs/machine-learning) |

**What it is:** Create and execute ML models directly in BigQuery using SQL. Supports logistic regression, k-means clustering, time series (ARIMA), matrix factorization, XGBoost, and deep learning (TensorFlow model import). Also supports LLM calls via `AI.GENERATE_TEXT` and vector search via `AI.GENERATE_EMBEDDING` and `VECTOR_SEARCH`.

**How to use in Sampark:**

| Use Case | BigQuery ML SQL |
|---|---|
| **Flood Prediction** | `CREATE MODEL flood_risk_model OPTIONS(model_type='logistic_reg') AS SELECT ...` |
| **Volume Forecasting** | `CREATE MODEL volume_arima OPTIONS(model_type='ARIMA_PLUS') AS SELECT ...` |
| **Sentiment Analysis** | `SELECT AI.GENERATE_TEXT('Analyze sentiment: ' || description)` |
| **Complaint Clustering** | `CREATE MODEL complaint_clusters OPTIONS(model_type='KMEANS') AS SELECT ...` |
| **Embedding Generation** | `SELECT AI.GENERATE_EMBEDDING(model, text)` |
| **Vector Search** | `SELECT VECTOR_SEARCH(table, 'column', query_embedding, top_k => 5)` |

**Where to integrate:**
- `agents/prediction_agent.py` — Replace heuristic `Math.logistic` with BigQuery ML model queries
- `agents/analytics_agent.py` — Replace manual DBSCAN with `KMEANS` clustering in BQ
- `rag/retriever.py` — Use `VECTOR_SEARCH` instead of (or alongside) Vertex AI Vector Search
- `sql/` — Add ML model creation DDL alongside the dashboard view

**🏆 Hackathon Tip:** This is **THE** hackathon-winning differentiator. Show judges you're using BigQuery's native ML capabilities:
- `AI.GENERATE_TEXT()` for in-database LLM inference (no data movement)
- `VECTOR_SEARCH` for in-database ANN semantic search
- `ARIMA_PLUS` for production-grade time series forecasting

This demonstrates **"Decision Intelligence"** — the hackathon theme — at scale.

---

## 📊 Category 2: Data & Analytics

---

### 13. BigQuery

| Field | Detail |
|---|---|
| **Service** | `bigquery` — Serverless data warehouse |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/bigquery](https://cloud.google.com/bigquery) |

**What it is:** Fully managed, serverless, highly scalable data warehouse. Petabyte-scale analytics with SQL. Supports real-time streaming, BI Engine, and built-in ML/AI capabilities.

**How to use in Sampark:**

| Component | BigQuery Role |
|---|---|
| **Data Intelligence Agent** | Query historical issues, community scores, predictions |
| **Analytics Agent** | Trend computation, aggregation queries |
| **Prediction Agent** | Store prediction results |
| **Dashboard API** | `GET /analytics/dashboard` queries `sampark_dashboard_view` |
| **Health Score** | Daily aggregation of community health scores |

**Where to integrate:**
- `tools/bigquery_tool.py` — Already implemented with `_sync_query_historical_issues()`, `_sync_write_predictions()`, `_sync_read_community_health_score()`
- `sql/sampark_dashboard_view.sql` — Dashboard aggregation view
- `infra/bigquery.tf` — Terraform: `issues`, `community_scores`, `predictions`, `tasks` tables

**🏆 Hackathon Tip:** Use **BI Engine** for sub-second dashboard queries. Show dashboard loading times on stage — fast dashboards impress judges.

---

### 14. Pub/Sub

| Field | Detail |
|---|---|
| **Service** | `pubsub` — Asynchronous messaging |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/pubsub](https://cloud.google.com/pubsub) |

**What it is:** Fully managed, real-time messaging service for event-driven systems. Supports push/pull subscriptions, exactly-once delivery, dead-letter topics, and global routing.

**How to use in Sampark:**

| Topic | Publisher | Subscriber |
|---|---|---|
| `task-created` | Workflow Agent | Notification Agent, Dashboard |
| `task-escalated` | Escalation Function | Notification Agent, Dashboard |
| `health-score-updated` | Health Score Function | Dashboard |

**Where to integrate:**
- `infra/pubsub.tf` — 3 topics + 1 dead-letter topic
- `agents/workflow_agent.py` — Publishes `task-created`
- `functions/escalation.py` — Publishes `task-escalated`
- `functions/health_score.py` — Publishes `health-score-updated`
- `agents/notification_agent.py` — Pub/Sub subscriber

**🏆 Hackathon Tip:** Add **Eventarc** to route Pub/Sub events to Cloud Run directly, showing event-driven architecture maturity.

---

### 15. Dataflow

| Field | Detail |
|---|---|
| **Service** | `dataflow` — Stream & batch data processing |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/dataflow](https://cloud.google.com/dataflow) |

**What it is:** Fully managed, serverless Apache Beam service for stream and batch data processing. Auto-scales, handles out-of-order data, exactly-once semantics.

**How to use in Sampark:**

| Use Case | Dataflow Pipeline |
|---|---|
| **Real-time Analytics** | Stream complaints from Pub/Sub → enrich → write to BigQuery |
| **Batch Health Scores** | Daily batch pipeline → compute health scores for all wards |
| **Data Enrichment** | Enrich issues with weather, traffic data at ingestion time |
| **Export Pipeline** | Generate daily/monthly PDF reports |

**Where to integrate:**
- `functions/` — Replace Cloud Functions with Dataflow pipelines for heavier processing
- `infra/dataflow.tf` — New Terraform file for Dataflow job templates

**🏆 Hackathon Tip:** Show a Dataflow pipeline processing complaints in real-time on your dashboard — "Live Complaint Analytics Pipeline." Judges love seeing streaming data in action.

---

### 16. Cloud Composer

| Field | Detail |
|---|---|
| **Service** | `composer` — Managed Apache Airflow |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/composer](https://cloud.google.com/composer) |

**What it is:** Fully managed workflow orchestration service built on Apache Airflow. Schedule, monitor, and manage complex DAGs across services.

**How to use in Sampark:**

| Use Case | Airflow DAG |
|---|---|
| **Daily Health Score** | Trigger → Compute sub-scores → Detect transitions → Pub/Sub event |
| **RAG Re-index** | Check for new docs → Re-embed → Re-index vector search |
| **Weekly Reports** | Aggregate → Generate PDF → Email to government officers |
| **Model Retraining** | Retrain prediction models with fresh 90-day data |

**Where to integrate:**
- `dags/` — New directory for Airflow DAGs
- `infra/composer.tf` — New Terraform for Composer environment

**🏆 Hackathon Tip:** Cloud Composer is overkill for this hackathon. Use **Cloud Scheduler + Cloud Functions** instead (simpler, cheaper to demo). Mention Composer in architecture as "future production path."

---

### 17. Looker Studio

| Field | Detail |
|---|---|
| **Service** | `looker-studio` — Free BI & dashboarding |
| **Status** | ❌ **New** |
| **Docs** | [lookerstudio.google.com](https://lookerstudio.google.com) |

**What it is:** Free, web-based business intelligence platform. Connect to BigQuery, create interactive dashboards, share with stakeholders. Supports scheduled email delivery, embedding, and data controls.

**How to use in Sampark:**

| Use Case | Looker Studio Dashboard |
|---|---|
| **Government Dashboard** | Community Health Score, complaint trends, risk heatmap |
| **Admin Dashboard** | System metrics, agent performance, pipeline latency |
| **Public Dashboard** | Ward-level health scores (read-only, embedded) |

**Where to integrate:**
- `sql/sampark_dashboard_view.sql` — BQ view that powers the dashboard (already exists)
- `frontend/` — Embed Looker Studio dashboard via iframe or `<DashboardComponent>`
- `infra/looker.tf` — Not Terraform-manageable, but document setup in README

**🏆 Hackathon Tip:** Create 3 Looker Studio dashboards and **embed them in the React app**. This shows you're not just building APIs — you're building stakeholder-facing analytics.

---

## 🗄️ Category 3: Databases & Storage

---

### 18. Firestore

| Field | Detail |
|---|---|
| **Service** | `firestore` — NoSQL document database |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/firestore](https://cloud.google.com/firestore) |

**What it is:** Flexible, scalable NoSQL database for mobile, web, and server development. Real-time listeners, offline support, ACID transactions, and multi-region replication.

**How to use in Sampark:**

| Collection | Documents |
|---|---|
| `users/{user_id}` | Profile, role, preferred_channel, ward_ids |
| `issues/{issue_id}` | Structured issue data, media refs, status |
| `tasks/{task_id}` | Department assignment, priority, due_date, status |
| `sessions/{session_id}/checkpoints/{node_name}` | GraphState snapshots |
| `notifications/{notification_id}` | Delivery logs |
| `knowledge_base/{doc_id}` | Chunk metadata for RAG documents |

**Where to integrate:**
- `tools/firestore_tool.py` — `geo_radius_query()`, CRUD, `onSnapshot()`
- `agents/checkpointing.py` — `FirestoreCheckpointSaver`
- `backend/main.py` — Persistence on `/issues` POST
- `agents/workflow_agent.py` — Task creation
- `agents/notification_agent.py` — Notification logging

**🏆 Hackathon Tip:** Use **Firestore real-time listeners** (`onSnapshot`) for live dashboard updates. When a task status changes, the dashboard updates instantly without polling.

---

### 19. Memorystore (Redis)

| Field | Detail |
|---|---|
| **Service** | `memorystore` — Managed Redis & Memcached |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/memorystore](https://cloud.google.com/memorystore) |

**What it is:** Fully managed in-memory data store for Redis and Memcached. Sub-millisecond latency, auto-failover, scaling, and VPC-native connectivity.

**How to use in Sampark:**

| Use Case | Redis Role |
|---|---|
| **Rate Limiting** | Replace in-memory dict `_rate_limit_cache` with Redis sliding window |
| **Session Cache** | Cache `GraphState` snapshots for faster resume |
| **LLM Response Cache** | Cache Gemini responses for identical queries |
| **Dashboard Cache** | Cache aggregated dashboard data, invalidate on Pub/Sub events |

**Where to integrate:**
- `backend/middleware.py` — Replace `_rate_limit_cache` dict with Redis calls
- `backend/main.py` — Add `redis_client` for dashboard caching
- `backend/config.py` — `REDIS_URL = os.getenv("REDIS_URL")`
- `infra/cloud_run.tf` — VPC connector for Memorystore access

**🏆 Hackathon Tip:** The current rate limiter resets on restart and doesn't work across instances. Replacing it with Memorystore shows production-awareness. Judges notice these details.

---

### 20. Cloud SQL / AlloyDB

| Field | Detail |
|---|---|
| **Service** | `cloud-sql` / `alloydb` — Managed relational databases |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/sql](https://cloud.google.com/sql) / [cloud.google.com/alloydb](https://cloud.google.com/alloydb) |

**What it is:** Fully managed PostgreSQL, MySQL, and SQL Server (Cloud SQL). AlloyDB is a PostgreSQL-compatible, 4x faster alternative optimized for demanding workloads with built-in vector support.

**How to use in Sampark:**

| Use Case | Database Role |
|---|---|
| **User Management** | Structured user profiles, roles, permissions |
| **Audit Logging** | Immutable audit trail of all actions |
| **Task Management** | Relational task tracking with department joins |

**Where to integrate:**
- `backend/` — Add SQLAlchemy models for structured data
- `infra/cloud_sql.tf` — New Terraform for Cloud SQL instance

**🏆 Hackathon Tip:** You likely don't need this on top of Firestore + BigQuery. Mention it as "future production addition" for ACID-compliant transactional data.

---

### 21. Cloud Storage

| Field | Detail |
|---|---|
| **Service** | `storage` — Object storage |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/storage](https://cloud.google.com/storage) |

**What it is:** Unified object storage with virtually unlimited capacity. Supports multi-region, nearline, coldline, and archive storage classes. Signed URLs, object lifecycle management, and event triggers.

**How to use in Sampark:**

| Bucket | Purpose |
|---|---|
| `sampark-media` | Images, audio recordings from citizens |
| `sampark-kb` | Policy documents (PDFs) for RAG pipeline |
| `sampark-exports` | Generated reports and exports |

**Where to integrate:**
- `tools/bigquery_tool.py` (indirect) — Media references in issue records
- `rag/ingestor.py` — Reads PDFs from `sampark-kb`
- `backend/main.py` — Upload endpoint stores to `sampark-media`

---

## ⚡ Category 4: Compute & Serverless

---

### 22. Cloud Run

| Field | Detail |
|---|---|
| **Service** | `run` — Serverless container platform |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/run](https://cloud.google.com/run) |

**What it is:** Fully managed, serverless platform for running containerized applications. Auto-scales from 0 to N, pay-per-use, supports request-based and event-driven workloads.

**How to use in Sampark:**

| Service | Container | Min Instances | Max Instances |
|---|---|---|---|
| `api-gateway` | `sampark/api-gateway:latest` | 1 | 10 |
| `langgraph-engine` | `sampark/langgraph-engine:latest` | 1 | 10 |
| `notification-worker` | `sampark/notification-worker:latest` | 0 | 5 |

**Where to integrate:**
- `backend/Dockerfile` — FastAPI app
- `langgraph/Dockerfile` — LangGraph engine
- `infra/cloud_run.tf` — `google_cloud_run_v2_service` resources

**🏆 Hackathon Tip:** Set **CPU always allocated** (`cpu_idle = false`) for `langgraph-engine` to avoid cold starts during LangGraph pipeline execution. Mention this configuration in your pitch to show production awareness.

---

### 23. Cloud Functions 2nd Gen

| Field | Detail |
|---|---|
| **Service** | `functions` — Event-driven serverless functions |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/functions](https://cloud.google.com/functions) |

**What it is:** Lightweight, event-driven compute. 2nd gen adds longer timeouts (60 min), larger instances (32 GB), and better concurrency. Triggered by Pub/Sub, Storage, Firestore, HTTP, and more.

**How to use in Sampark:**

| Function | Trigger | Purpose |
|---|---|---|
| `health-score-function` | Pub/Sub (Cloud Scheduler daily) | Compute daily health scores |
| `escalation-scheduler` | Cloud Scheduler (hourly) | Escalate overdue tasks |

**Where to integrate:**
- `functions/health_score.py` — `compute_health_score()`
- `functions/escalation.py` — `escalate_overdue_tasks()`
- `.github/workflows/ci-cd.yml` — Deploy commands

---

### 24. Cloud Scheduler

| Field | Detail |
|---|---|
| **Service** | `scheduler` — Managed cron job service |
| **Status** | ⚠️ **Planned** (mentioned in docs) |
| **Docs** | [cloud.google.com/scheduler](https://cloud.google.com/scheduler) |

**What it is:** Fully managed enterprise-grade cron job scheduler. Supports 3 delivery targets: HTTP, Pub/Sub, and App Engine. Handles retries with exponential backoff.

**How to use in Sampark:**

| Job | Schedule | Target |
|---|---|---|
| `health-score-trigger` | `0 0 * * *` (daily midnight) | Pub/Sub `health-score-updated` |
| `escalation-check` | `0 * * * *` (hourly) | HTTP → `escalation-scheduler` |

**Where to integrate:**
- `functions/` — Schedule documentation in docstrings
- `infra/` — Should add `google_cloud_scheduler_job` resources in Terraform

---

### 25. Eventarc

| Field | Detail |
|---|---|
| **Service** | `eventarc` — Event-driven architecture |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/eventarc](https://cloud.google.com/eventarc) |

**What it is:** Unified event ingestion and delivery service. Routes events from 90+ GCP sources (Cloud Storage, BigQuery, Firestore, etc.) to Cloud Run, Cloud Functions, GKE, etc.

**How to use in Sampark:**

| Event Source | Event Type | Destination |
|---|---|---|
| Cloud Storage (PDF upload) | `google.cloud.storage.object.v1.finalized` | Cloud Run: RAG ingestion |
| Firestore (task update) | `google.cloud.firestore.document.v1.updated` | Cloud Run: Dashboard SSE push |
| Cloud Scheduler | Scheduled event | Cloud Functions |

**Where to integrate:**
- `infra/eventarc.tf` — New Terraform for Eventarc triggers
- `rag/ingestor.py` — Auto-trigger ingestion on new policy document upload

**🏆 Hackathon Tip:** Replace Pub/Sub push subscriptions with Eventarc for cleaner, managed event routing. Shows architectural sophistication.

---

### 26. Cloud Tasks

| Field | Detail |
|---|---|
| **Service** | `tasks` — Distributed task queues |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/tasks](https://cloud.google.com/tasks) |

**What it is:** Fully managed distributed task queue. Pull-based task distribution with configurable retry, rate limiting, and scheduling. Ideal for async processing with guaranteed delivery.

**How to use in Sampark:**

| Use Case | Queue | Description |
|---|---|---|
| **Notification Dispatch** | `notification-queue` | Reliable async notification delivery with retry |
| **Report Generation** | `report-queue` | Generate PDF reports asynchronously |
| **Bulk Operations** | `analytics-queue` | Process large analytics queries without blocking |

**Where to integrate:**
- `agents/workflow_agent.py` — Enqueue tasks instead of direct Pub/Sub publish
- `backend/main.py` — `/issues` returns immediately, processing happens via Cloud Tasks

**🏆 Hackathon Tip:** Replace direct Pub/Sub publishing in `workflow_agent.py` with Cloud Tasks. Show monitoring dashboard with queue depth, processing rate, failure rate. Judges love operational maturity.

---

## 🔐 Category 5: Security & Identity

---

### 27. Firebase Authentication

| Field | Detail |
|---|---|
| **Service** | `firebase-auth` — User authentication |
| **Status** | ⚠️ **Partially planned** |
| **Docs** | [firebase.google.com/docs/auth](https://firebase.google.com/docs/auth) |

**What it is:** Complete identity solution supporting email/password, Google, Facebook, Twitter, GitHub, phone auth, and custom JWT. Serverless, scales automatically, integrated with Firestore security rules.

**How to use in Sampark:**

| Provider | Use Case |
|---|---|
| Email/Password | Citizens, Government Officers, Admins |
| Google OAuth | One-click login for government officers |
| Phone Auth | WhatsApp-verified citizens (OTP to phone) |
| Custom JWT | Backend service-to-service auth |

**Where to integrate:**
- `backend/main.py` — Replace hardcoded `admin`/`leader_w1` users with Firebase Auth
- `backend/middleware.py` — Verify Firebase JWTs using `firebase-admin` SDK
- `frontend/` — Firebase Auth UI for login/signup
- `backend/config.py` — `FIREBASE_CREDENTIALS_PATH` config

**🏆 Hackathon Tip:** This is a **must-fix** for a hackathon. The current hardcoded users with mock JWT will lose points. Real Firebase Auth with role-based claims shows production readiness.

---

### 28. Secret Manager

| Field | Detail |
|---|---|
| **Service** | `secret-manager` — Secrets storage |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/secret-manager](https://cloud.google.com/secret-manager) |

**What it is:** Secure, convenient storage for API keys, passwords, certificates, and other sensitive data. Versioned access, audit logging, IAM integration.

**How to use in Sampark:**

| Secret | Used By |
|---|---|
| `sampark-jwt-secret-key` | api-gateway |
| `sampark-firebase-credentials` | api-gateway |
| `sampark-redis-url` | api-gateway |
| `sampark-vertex-ai-api-key` | langgraph-engine |
| `sampark-google-maps-api-key` | langgraph-engine |
| `sampark-weather-api-key` | langgraph-engine |
| `sampark-firestore-database-id` | langgraph-engine |
| `sampark-twilio-account-sid` | notification-worker |
| `sampark-sendgrid-api-key` | notification-worker |
| `sampark-fcm-server-key` | notification-worker |

**Where to integrate:**
- `infra/secrets.tf` — 11 secret containers
- `infra/cloud_run.tf` — Env var `value_source.secret_key_ref` references

---

### 29. Cloud KMS

| Field | Detail |
|---|---|
| **Service** | `kms` — Cryptographic key management |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/kms](https://cloud.google.com/kms) |

**What it is:** Cloud-hosted key management service for generating, using, rotating, and destroying cryptographic keys. FIPS 140-2 Level 3. Envelope encryption, CMEK for Google Cloud services.

**How to use in Sampark:**

| Use Case | KMS Role |
|---|---|
| **Sensitive Data** | Encrypt PII (phone numbers, addresses) in Firestore |
| **JWT Signing** | Use Cloud KMS key for JWT signing instead of hardcoded secret |
| **BigQuery CMEK** | Customer-managed encryption key for analytics dataset |

**Where to integrate:**
- `backend/middleware.py` — Sign/verify JWTs via Cloud KMS instead of `mock_secret_key`

**🏆 Hackathon Tip:** Mention this in your "Security Architecture" slide. You don't need to fully implement it — just showing you've thought about it is impressive.

---

### 30. Cloud Armor

| Field | Detail |
|---|---|
| **Service** | `cloud-armor` — Web application security |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/armor](https://cloud.google.com/armor) |

**What it is:** Google Cloud's web application firewall (WAF) and DDoS protection service. Pre-configured rules for OWASP Top 10, IP allow/deny lists, rate-based blocking, and bot management.

**How to use in Sampark:**

| Security Feature | Cloud Armor Rule |
|---|---|
| **DDoS Protection** | Enable Google Cloud Armor Managed Protection |
| **IP Whitelisting** | Government officer IP ranges only for admin endpoints |
| **Rate Limiting** | Distributed rate limiting per IP before requests hit the API |
| **WAF Rules** | Block SQL injection, XSS, LFI, RFI attacks |

**Where to integrate:**
- `infra/armor.tf` — `google_compute_security_policy` resources
- `infra/cloud_run.tf` — Add `security_policy` to Cloud Run ingress

**🏆 Hackathon Tip:** Overkill for hackathon demo. Mention as production-hardening step.

---

## 🗺️ Category 6: Location & Maps

---

### 31. Google Maps Platform

| Field | Detail |
|---|---|
| **Service** | `google-maps` — Maps, Routes, Places APIs |
| **Status** | ✅ **Already integrated** |
| **Docs** | [developers.google.com/maps](https://developers.google.com/maps) |

**What it is:** Comprehensive location platform. Geocoding, reverse geocoding, Places API (nearby search, details), Directions API, Distance Matrix API, Maps JavaScript API, Street View, and more.

**How to use in Sampark:**

| Component | Maps API Role |
|---|---|
| **Validation Agent** | `geocode()` to verify addresses, detect out-of-boundary locations |
| **Data Intelligence Agent** | `get_traffic_context()` via Places Nearby Search |
| **Dashboard** | Interactive heatmap + map layers showing issue locations |
| **Citizen UI** | Pin drop on map for issue location selection |
| **Admin** | View issue density heatmap across wards |

**Where to integrate:**
- `tools/maps_tool.py` — `geocode()`, `get_traffic_context()` already implemented
- `frontend/` — Google Maps JavaScript API for interactive map components

**🏆 Hackathon Tip:** Show a **live heatmap** on the dashboard with issue density, risk zones, and route optimization for resource dispatch. Demo: "Show me all pothole incidents in Ward 5" → heatmap + list.

---

## 🔧 Category 7: DevOps, CI/CD & Observability

---

### 32. Cloud Build

| Field | Detail |
|---|---|
| **Service** | `cloud-build` — CI/CD |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/build](https://cloud.google.com/build) |

**What it is:** Fully managed CI/CD platform that builds, tests, and deploys in the cloud. 120 minutes free per day. Integrates with GitHub, GitLab, Bitbucket, and Cloud Source Repositories.

**Where to integrate:**
- `.github/workflows/ci-cd.yml` — Build steps for 3 Docker images (api-gateway, langgraph-engine, notification-worker)

---

### 33. Artifact Registry

| Field | Detail |
|---|---|
| **Service** | `artifact-registry` — Container & package registry |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/artifact-registry](https://cloud.google.com/artifact-registry) |

**What it is:** Universal artifact repository for storing container images and language packages (Maven, npm, pip, apt). VPC-scoped, IAM-protected, vulnerability scanning.

**Where to integrate:**
- `.github/workflows/ci-cd.yml` — Push to Artifact Registry after Docker build
- `infra/cloud_run.tf` — `image = "${var.artifact_registry}/sampark/api-gateway:latest"`

---

### 34. Cloud Logging

| Field | Detail |
|---|---|
| **Service** | `logging` — Centralized logging |
| **Status** | ✅ **Already integrated** |
| **Docs** | [cloud.google.com/logging](https://cloud.google.com/logging) |

**What it is:** Fully managed log storage and analysis. Ingests logs from all GCP services. Supports advanced queries, log-based metrics, log sinks to BigQuery/Pub/Sub, and export to Cloud Storage.

**How to use in Sampark:**

| Log Source | What's Logged |
|---|---|
| **API Gateway** | Request logs: `method`, `path`, `user_id`, `status`, `latency_ms` |
| **Agents** | Node execution, SLA breaches, tool failures |
| **Pipeline** | `session_id`, `node_name`, `retry_count` |
| **Errors** | All exceptions with stack traces |

**Where to integrate:**
- `backend/middleware.py` — `LoggingMiddleware` logs every request (already implemented)
- `agents/*.py` — `logger.info/warning/exception` calls throughout
- `infra/cloud_run.tf` — Service accounts get `roles/logging.logWriter`

**🏆 Hackathon Tip:** Create a **Cloud Logging dashboard** showing agent latency, error rates, pipeline completion rates. Project this during your demo — it shows operational maturity.

---

### 35. Cloud Monitoring

| Field | Detail |
|---|---|
| **Service** | `monitoring` — Infrastructure & application monitoring |
| **Status** | ⚠️ **Partially planned** |
| **Docs** | [cloud.google.com/monitoring](https://cloud.google.com/monitoring) |

**What it is:** Full observability platform with dashboards, alerting, uptime checks, and custom metrics. Integrates with Cloud Logging, Cloud Trace, and Cloud Profiler.

**How to use in Sampark:**

| Metric | Custom Metric Name | What it Measures |
|---|---|---|
| **Agent Latency** | `agent_latency_ms` | Per-node execution time |
| **Pipeline Success** | `pipeline_success_rate` | Fraction of successful completions |
| **RAG Retrieval Hit** | `rag_retrieval_hit_rate` | Fraction with policy context found |

**Where to integrate:**
- `agents/graph.py` — Emit custom metrics after each node
- `infra/dashboard.tf` — Create Cloud Monitoring dashboard via Terraform

**🏆 Hackathon Tip:** Show a **live monitoring dashboard** on a second monitor during your demo. When you submit an issue, watch the metrics update in real-time.

---

### 36. Cloud Deploy

| Field | Detail |
|---|---|
| **Service** | `deploy` — Managed continuous delivery |
| **Status** | ❌ **New** |
| **Docs** | [cloud.google.com/deploy](https://cloud.google.com/deploy) |

**What it is:** Managed continuous delivery service that supports canary, blue/green, and rolling deployments to GKE and Cloud Run. Supports deploy policies, approvals, and rollbacks.

**How to use in Sampark:**
- Replace shell-based `gcloud run deploy` in CI/CD with Cloud Deploy delivery pipelines
- Add canary deployment for api-gateway (10% → 50% → 100%)

**🏆 Hackathon Tip:** Overkill for hackathon. Stick with `gcloud run deploy` in CI/CD.

---

## 🤖 Category 8: AI Development Tools

---

### 37. Firebase Genkit

| Field | Detail |
|---|---|
| **Service** | `genkit` — Open-source AI integration framework |
| **Status** | ❌ **New — High Impact** |
| **Docs** | [firebase.google.com/docs/genkit](https://firebase.google.com/docs/genkit) |

**What it is:** Open-source framework (by Google) for building AI-powered applications. Provides server-side prompt management, structured output generation, tool/plugin integration, multi-agent support, and built-in observability — all in TypeScript or Go.

**How to use in Sampark:**

| Genkit Feature | Sampark Use Case |
|---|---|
| **AI Flows** | Define agent pipeline as a Genkit flow with observability |
| **Prompt Management** | Version-controlled prompts for each agent |
| **Tool Integration** | Wrap BigQuery, Firestore, Maps as Genkit tools |
| **Multi-Agent** | Use Genkit's `defineAgent` for sub-agents |
| **Observability** | Built-in tracing and monitoring via Genkit UI |

**Where to integrate:**

```typescript
// Option: Replace LangGraph with Genkit for the frontend-facing API
import { defineFlow, defineAgent, run } from '@genkit-ai/flow';

const intakeAgent = defineAgent(
  name: 'intakeAgent',
  model: geminiPro,
  tools: [visionTool, speechTool],
  systemPrompt: 'Extract issue type, location, description...'
);
```

**🏆 Hackathon Tip:** Add Genkit to your tech stack and show the **Genkit Developer UI** with trace visualizations during your demo. Judges will see: "Start → Intake → Validation → Analytics → ..." with timing per step. This is incredibly impressive.

---

### 38. Agent Development Kit (ADK)

| Field | Detail |
|---|---|
| **Service** | `adk` — Google's Agent Development Kit |
| **Status** | ❌ **New — REQUIRED for Hackathon** |
| **Docs** | [github.com/google/adk-python](https://github.com/google/adk-python) |

**What it is:** Google's open-source framework (Python/TypeScript) for building multi-agent AI systems. Official framework for the hackathon. Provides: `Agent` class, tool/function calling, memory, state management, and multi-agent orchestration. Tight Gemini integration.

**How to use in Sampark:**

```python
# Migrate from LangGraph to ADK
from google.adk import Agent, Runner

supervisor = Agent(
    name="SupervisorAgent",
    model=gemini_pro,
    tools=[router_tool],
    sub_agents=[intake_agent, validation_agent, ...]
)

intake_agent = Agent(
    name="IntakeAgent",
    model=gemini_pro,
    tools=[speech_tool, vision_tool],
    instruction="Extract structured issue from citizen input..."
)
```

**Where to integrate:**
- `agents/adk/` — New directory for ADK-based agents
- `agents/graph.py` — Replace `StateGraph` with ADK `Agent` orchestration

**🏆 Hackathon Tip:** This is **the official hackathon framework**. The judges will specifically look for ADK usage. Spend time converting your LangGraph pipeline to ADK. Even a partial conversion (Supervisor Agent + 2-3 sub-agents) is better than none.

---

### 39. LangChain / LangGraph

| Field | Detail |
|---|---|
| **Service** | `langchain` / `langgraph` — LLM orchestration framework |
| **Status** | ✅ **Already integrated** |
| **Docs** | [langchain.com](https://langchain.com) / [langgraph.com](https://langgraph.com) |

**What it is:** LangChain is the leading open-source framework for building LLM-powered applications. LangGraph extends it with directed graph execution, state management, checkpointing, and parallel nodes.

**How to use in Sampark (already fully integrated):**

| LangGraph Feature | Sampark Implementation |
|---|---|
| `StateGraph` | `agents/graph.py` — Full pipeline graph |
| `Send` API | `parallel_dispatch()` — Parallel analytics + prediction |
| `ConditionalEdge` | `supervisor_router()` — 3-way routing |
| Checkpointing | `checkpointing.py` — Firestore-backed state persistence |

**Where to integrate:**
- `agents/graph.py` — Main graph definition
- `agents/state.py` — `GraphState` TypedDict with 15+ fields

---

## 📦 Complete Architecture Diagram

```
                              ┌─────────────────────────┐
                              │    USER CHANNELS         │
                              │  Web · WhatsApp · Voice  │
                              │  Firebase Auth           │
                              └────────────────────┬────┘
                                                   │
                              ┌────────────────────▼────┐
                              │   CLOUD ARMOR / LB       │
                              │   DDoS · WAF · SSL      │
                              └────────────────────┬────┘
                                                   │
         ┌─────────────────────────────────────────┼─────────────────────────┐
         │                                         │                         │
 ┌───────▼────────┐                    ┌───────────▼───────────┐  ┌─────────▼─────────┐
 │  CLOUD RUN      │                    │  CLOUD RUN             │  │  CLOUD RUN         │
 │  api-gateway    │                    │  langgraph-engine      │  │  notification-worker│
 │  FastAPI        │                    │  ADK / LangGraph       │  │  Python agent       │
 │  PyJWT · Redis  │                    │  8 Agents              │  │  Twilio · SendGrid  │
 └───────┬────────┘                    └───────────┬────────────┘  └──────┬─────────────┘
         │                                         │                       │
         │              ┌──────────────────────────┼───────────────────────┘
         │              │                          │
         │     ┌────────▼────────┐      ┌──────────▼──────────┐
         │     │  CLOUD FUNCTIONS│      │  FIRESTORE           │
         │     │  health-score   │      │  users · issues      │
         │     │  escalation     │      │  tasks · sessions    │
         │     │  auto-trigger   │      │  notifications       │
         │     └────────┬────────┘      └─────────────────────┘
         │              │                          ▲
         │     ┌────────▼────────┐                 │
         │     │  PUB/SUB        │─────────────────┘
         │     │  3 Topics       │     ┌──────────────────────────┐
         │     │  Dead Letter    │─────│  BIGQUERY                │
         │     └─────────────────┘     │  issues · community_scores│
         │                             │  predictions · tasks      │
         │     ┌─────────────────┐     │  ML Models · View         │
         │     │  CLOUD STORAGE  │     │  VECTOR SEARCH            │
         │     │  media · kb     │     └──────────────────────────┘
         │     │  exports        │                    ▲
         │     └────────┬────────┘                    │
         │              │              ┌──────────────┴──────────────┐
         │              └──────────────│  VERTEX AI                 │
         │                            │  Gemini 1.5 Pro / 2.0 Flash │
         │     ┌──────────────────┐   │  Imagen · Vision · Speech  │
         │     │  MEMORYSTORE     │   │  Vector Search · Embeddings │
         │     │  Redis Cache     │   │  Agent Builder (ADK)        │
         │     │  Rate Limiter    │   └─────────────────────────────┘
         │     └──────────────────┘
         │
         │     ┌──────────────────┐
         │     │  GOOGLE MAPS     │
         │     │  Geocoding       │
         │     │  Places API      │
         │     │  Maps JS API     │
         └─────┤  (Dashboard)     │
               └──────────────────┘
```

---

## 🏆 Hackathon-Winning Priority Matrix

### 🔴 Critical — Must Do

| Priority | Tool | Why |
|---|---|---|
| 1 | **Agent Development Kit (ADK)** | Official hackathon framework — judges require it |
| 2 | **Firebase Authentication** | Replace hardcoded users — shows real auth |
| 3 | **BigQuery ML (ARIMA, KMEANS, AI.GENERATE_TEXT)** | Native ML in database — theme of "Decision Intelligence" |
| 4 | **Vertex AI Vector Search (real)** | Replace mock vectors — makes RAG real |

### 🟡 Medium — Strongly Recommended

| Priority | Tool | Why |
|---|---|---|
| 5 | **Memorystore (Redis)** | Production rate limiting, caching |
| 6 | **Cloud Translation API** | Multi-lingual support for Indian languages |
| 7 | **Firebase Genkit** | AI observability for demo — watch every agent step |
| 8 | **Dialogflow CX** | First-line citizen conversation before AI pipeline |
| 9 | **Looker Studio** | Embedded dashboards for government officers |
| 10 | **Cloud Monitoring** | Custom metrics dashboard for demo |

### 🟢 Nice to Have

| Priority | Tool | Why |
|---|---|---|
| 11 | **Vertex AI Imagen** | Generate "after repair" images — wow factor |
| 12 | **Natural Language API** | Low-cost batch sentiment for high volume |
| 13 | **Cloud Functions** | Event-driven pipeline triggers |
| 14 | **Document AI** | Better OCR for scanned government PDFs |
| 15 | **Eventarc** | Clean event routing between services |

---

> 📝 **Last Updated:** July 2025
>
> **Reference:** [Google Cloud Products](https://cloud.google.com/products) | [Firebase Docs](https://firebase.google.com/docs) | [ADK Docs](https://github.com/google/adk-python)
