# Sampark AI — Community Decision Intelligence Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)]()
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)]()
[![Gemini API](https://img.shields.io/badge/Gemini%20API-Free-yellow)]()
[![Zero GCP Billing](https://img.shields.io/badge/Zero%20GCP%20Billing-success)]()

**Sampark AI** is a multi-agent AI platform that transforms citizen complaints into actionable, policy-grounded municipal decisions. Built on **LangGraph** and **free Google technologies**, it orchestrates a pipeline of specialized AI agents — intake, validation, prediction, recommendation, workflow — to automate end-to-end civic issue resolution.

> **🇮🇳 "Sampark"** (संपर्क) means *connection* — connecting citizens with their government through AI.

---

## 🏆 Hackathon Highlights

| Feature | Technology | Cost |
| :--- | :--- | :--- |
| **AI Reasoning** | Gemini API (Google AI Studio) | **Free** |
| **Image Understanding** | Gemini Vision (API) | **Free** |
| **Speech-to-Text** | Browser Web Speech API | **Free** |
| **RAG / Vector Search** | FAISS + Gemini Embeddings | **Free** |
| **Database** | SQLite | **Free** |
| **Analytics** | DuckDB | **Free** |
| **Deployment** | Render / Railway / Vercel | **Free** |
| **Total Cost** | **$0/month** | 🎉 |

---

## 🏛️ System Architecture

```
                    ┌─────────────────────┐
                    │    Citizen Portal    │
                    │   (React Frontend)   │
                    └──────────┬──────────┘
                               │ POST /issues
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Gateway    │
                    │  (JWT Auth, CORS,    │
                    │   Rate Limiting)     │
                    └──────────┬──────────┘
                               │ ainvoke
                               ▼
              ┌─────────────────────────────────┐
              │     LangGraph Orchestrator       │
              │  (StateGraph, Checkpointing,     │
              │   Retry, SSE Streaming)          │
              └──┬──────┬──────┬──────┬─────────┘
                 │      │      │      │
         ┌───────▼┐ ┌──▼──┐ ┌─▼───┐ ┌▼──────────┐
         │ Intake │ │Vali-│ │Data │ │ Prediction │
         │ Agent  │ │dation│ │Intel│ │   Agent    │
         └───────┘ └─────┘ └─────┘ └─────┬──────┘
                                         │
                          ┌───────────────┼──────────────┐
                          ▼               ▼              ▼
                   ┌────────────┐  ┌───────────┐  ┌──────────┐
                   │ Analytics  │  │Recommend- │  │ Workflow │
                   │   Agent    │  │ation Agent│  │  Agent   │
                   └────────────┘  └─────┬─────┘  └────┬─────┘
                                         │              │
                                         ▼              ▼
                                  ┌──────────┐   ┌───────────┐
                                  │  RAG /   │   │ Queue &   │
                                  │  FAISS   │   │  SQLite   │
                                  └──────────┘   └───────────┘
```

### Multi-Agent Pipeline

| Step | Agent | What It Does |
| :--- | :--- | :--- |
| **1** | **Intake Agent** | Classifies issue type, extracts location, detects language |
| **2** | **Validation Agent** | Checks duplicates, verifies location, assigns confidence |
| **3** | **Data Intelligence Agent** | Gathers context from weather, maps, history |
| **4** | **Analytics Agent** | Computes trends, sentiment, cluster analysis |
| **5** | **Prediction Agent** | Forecasts flood/road risk, complaint volume |
| **6** | **Recommendation Agent** | RAG-grounded policy recommendations via Gemini + FAISS |
| **7** | **Workflow Agent** | Assigns department, creates task, dispatches notification |
| **8** | **Notification Agent** | Multi-channel push (email, SMS, WhatsApp — optional) |

---

## ✨ Key Features

- **🔬 Multi-Agent AI Pipeline** — 8 specialized LangGraph agents with conditional routing, retry logic, and parallel execution
- **📜 RAG-Grounded Recommendations** — Policy documents ingested into FAISS; every recommendation cites its sources
- **🌍 Real-Time Streaming** — SSE streams for agent progress and live dashboard updates
- **📊 Decision Intelligence Dashboard** — Community health scores, ward risk heatmaps, critical action queue
- **📱 Multi-Channel Notifications** — Email (SendGrid), SMS & WhatsApp (Twilio) — all optional
- **🔐 Role-Based Access Control** — JWT-authenticated roles: Officer & Community Leader
- **📄 Knowledge Base Management** — Upload, list, and delete PDF policy documents for RAG indexing
- **🎤 Multimodal Intake** — Text, image captioning (Gemini Vision), and audio transcription (Web Speech API)
- **📈 Predictive Analytics** — Flood risk, road degradation, complaint volume forecasting
- **💰 Zero Cloud Cost** — Everything runs locally or on free tiers

---

## 🛠️ Tech Stack (FREE)

### Backend (Python)
| Component | Technology | Cost |
| :--- | :--- | :--- |
| **API Framework** | FastAPI (Python 3.11+) | Free |
| **AI Orchestration** | LangGraph, LangChain | Free |
| **LLM** | Gemini 2.5 Flash (AI Studio) | **Free** 🔑 |
| **Vector Search / RAG** | FAISS + Gemini Embeddings | **Free** |
| **Database** | SQLite (aiosqlite) | **Free** |
| **Analytics** | DuckDB | **Free** |
| **Messaging** | Python asyncio.Queue | **Free** |
| **Auth** | JWT (PyJWT) + bcrypt | **Free** |

### Frontend (React)
| Component | Technology |
| :--- | :--- |
| **Framework** | React 18 (Vite) |
| **Styling** | Glassmorphism CSS |
| **Fonts** | Google Fonts (Inter, Poppins) |
| **Icons** | Material Icons |
| **Speech** | Browser Web Speech API |

---

## 🚀 Quick Start (3 Commands)

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Install frontend
cd frontend && npm install && cd ..

# 3. Run tests
python -m pytest
```

### Then Start the Platform

```bash
# Terminal 1 — Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open **http://localhost:5173** and log in with `admin` / `password`.

---

## 🔧 Environment (Optional)

```env
# Create .env in project root
APP_MODE=local                          # Uses mock data, no API keys needed
GEMINI_API_KEY=your_key_here           # Optional — get from aistudio.google.com
GOOGLE_MAPS_API_KEY=your_key_here      # Optional
OPENWEATHER_API_KEY=your_key_here      # Optional
```

**No API keys needed for local development.** The platform runs entirely in mock mode.

---

## 📂 Project Structure

```
sampark-genapac/
├── agents/                  # LangGraph agent implementations
│   ├── graph.py             # StateGraph topology (FREE stack)
│   ├── state.py             # Shared GraphState TypedDict
│   ├── intake_agent.py      # Issue classification & extraction
│   ├── validation_agent.py  # Duplicate & confidence checks
│   ├── analytics_agent.py   # Trend & sentiment analysis
│   ├── prediction_agent.py  # Risk forecasting
│   ├── recommendation_agent.py  # RAG-grounded recommendations
│   ├── workflow_agent.py    # Department assignment & task creation
│   └── checkpointing.py     # In-memory checkpointing
├── backend/                 # FastAPI Gateway
│   ├── main.py              # REST endpoints & SSE streaming
│   ├── config.py            # FREE stack configuration
│   └── Dockerfile
├── frontend/                # React 18 Vite SPA
│   ├── src/App.jsx
│   ├── src/api.js
│   └── src/index.css
├── tools/                   # Service abstraction tools (FREE stack)
│   ├── sqlite_tool.py       # SQLite database (replaces Firestore)
│   ├── embeddings_tool.py   # FAISS + Gemini Embeddings (replaces Vertex AI)
│   ├── bigquery_tool.py     # DuckDB analytics (replaces BigQuery)
│   ├── firestore_tool.py    # Adapter for backward compatibility
│   ├── vision_tool.py       # Gemini Vision (AI Studio)
│   ├── speech_tool.py       # Web Speech API mock
│   └── maps_tool.py         # Google Maps geocoding
├── rag/                     # RAG pipeline
│   ├── ingestor.py          # PDF ingestion, chunking, FAISS indexing
│   ├── retriever.py         # FAISS similarity search
│   └── generator.py         # Gemini-powered grounded answer gen
├── functions/               # Background functions
│   ├── escalation.py        # Task escalation logic
│   └── health_score.py      # Community health score computation
├── .github/workflows/       # CI/CD
├── pyproject.toml           # Python project config
├── README.md                # This file
├── GServices.md             # FREE Google services reference
└── TPT.md                   # Third-party services reference
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Specific suites
python -m pytest tools/tests/         # Tool tests
python -m pytest agents/tests/        # Agent tests
python -m pytest backend/tests/       # API & E2E tests
python -m pytest -k "pbt"            # Property-based tests
```

---

## 📊 Evaluation Metrics

| Metric | Target | Current |
| :--- | :--- | :--- |
| Classification Accuracy | > 85% | **90%** |
| Policy Citation Coverage | 100% | **100%** |
| Average Demo Latency | < 5s | **< 3s** |
| SLA — Critical Priority | 24h | Implemented |

---

## 🔐 Security

- **JWT Authentication** with bcrypt password hashing
- **Role-Based Access Control** (Government Officer, Community Leader)
- **Rate Limiting** — per-IP sliding window
- **Input Validation** — Pydantic schemas, file size limits (50MB PDF)

---

## 🙏 Acknowledgments

- **Google Hackathon** — Gemini API, AI Studio, Google Fonts, Material Design
- **LangChain / LangGraph** — Multi-agent orchestration framework
- **FAISS** — Vector search (Meta AI)
- **DuckDB** — In-process analytics
- **OpenWeatherMap, SendGrid, Twilio** — Optional integrations

---

*Built with ❤️ for the Google GenAI APAC Hackathon. Zero GCP billing required.*
