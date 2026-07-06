# FREE Google Services Reference — Sampark AI Platform

This document catalogs all **FREE Google technologies** used by the Sampark AI Platform.  
**No Google Cloud billing account required.** Everything runs on free tiers and APIs.

---

## 🎯 Design Philosophy

| Constraint | Approach |
| :--- | :--- |
| **No GCP billing** | All services are either free-tier Google APIs or local replacements |
| **No Vertex AI** | Replaced with Gemini API from Google AI Studio |
| **No Firestore/BigQuery** | Replaced with SQLite and DuckDB (local, free) |
| **No Cloud Run** | Deployed directly with uvicorn or on free platforms (Render, Railway) |
| **No Pub/Sub** | Replaced with Python `asyncio.Queue` |
| **No Secret Manager** | Replaced with `.env` file |
| **Google-first** | Use Gemini API, Google OAuth, Google Fonts, Material Design |

---

## 📋 Service Inventory

| # | Google Technology | Category | Purpose | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Gemini API (AI Studio)** | AI/ML | Primary LLM — classification, extraction, sentiment, generation | ✅ Active |
| 2 | **Gemini Embeddings API** | AI/ML | Text embeddings for RAG vector search (768-dim) | ✅ Active |
| 3 | **Gemini Vision** | AI/ML | Image captioning & analysis via Gemini API | ✅ Active |
| 4 | **Google AI Studio** | Prompt Mgmt | Prompt development, testing, management | ✅ Active |
| 5 | **Gemini 2.5 Flash** | AI/ML | Fast, cost-effective model for most tasks | ✅ Active |
| 6 | **Gemini 2.5 Pro** | AI/ML | Complex reasoning (used when needed) | ⚙️ Optional |
| 7 | **Gemini Function Calling** | AI/ML | Structured output parsing from agent pipeline | ✅ Active |
| 8 | **Google Maps Embed API** | Location | Map display in frontend (free quota) | ✅ Active |
| 9 | **Google Fonts** | Frontend | Typography - Poppins, Inter fonts | ✅ Active |
| 10 | **Material Icons** | Frontend | UI icons via Google Fonts CDN | ✅ Active |
| 11 | **Material Design** | Frontend | UI design system (glassmorphism theme) | ✅ Active |
| 12 | **Firebase Auth (Spark)** | Auth | JWT-based authentication (demo mode built-in) | ⚙️ Optional |
| 13 | **Google OAuth** | Auth | Sign-in via Google accounts | ⚙️ Future |
| 14 | **Browser Web Speech API** | Speech | Client-side speech-to-text (free, unlimited) | ✅ Active |

---

## 1. 🤖 Gemini API (Google AI Studio)

**Purpose:** Powers the core AI reasoning — issue classification, language detection, sentiment analysis, entity extraction, and grounded response generation.

**Replaces:** Vertex AI Gemini (paid GCP service)

### Usage Locations

| File | Usage |
| :--- | :--- |
| `agents/graph.py` | `google.generativeai.GenerativeModel("gemini-2.5-flash")` — primary LLM |
| `agents/intake_agent.py` | Problem classification, entity extraction, language detection |
| `agents/analytics_agent.py` | Sentiment scoring |
| `rag/generator.py` | Grounded answer generation with retrieved policy context |
| `tools/vision_tool.py` | Image captioning via Gemini Vision |

### Configuration

```python
# Get your FREE API key from: https://aistudio.google.com/apikey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
```

### Local Mode Mock

In `APP_MODE=local`, the graph uses `MockGeminiModel` which returns deterministic mock responses without making any API calls. **No API key needed.**

### Setup Instructions

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click **Get API Key** → Create API Key
3. Copy the key and set it as `GEMINI_API_KEY` in `.env`
4. Optionally set `GEMINI_MODEL` (default: `gemini-2.5-flash`)

### Free Tier Limits

| Model | Requests per minute | Requests per day | Input | Output |
| :--- | :--- | :--- | :--- | :--- |
| Gemini 2.5 Flash | 30 RPM | 1,500 RPD | 1M tokens/min | Free |
| Gemini 2.5 Pro | 5 RPM | 50 RPD | 1M tokens/min | Free |

---

## 2. 🧠 Gemini Embeddings API

**Purpose:** Generates text embeddings for the RAG pipeline. Used by `EmbeddingSearchTool` to embed policy document chunks and query vectors.

**Replaces:** Vertex AI text-embedding-004 (paid)

### Usage Locations

| File | Usage |
| :--- | :--- |
| `tools/embeddings_tool.py` | `EmbeddingSearchTool.get_embeddings()` — embeds texts via Gemini API |
| `rag/ingestor.py` | Document chunk → embedding → FAISS index |
| `rag/retriever.py` | Query → embedding → FAISS similarity search |

### Configuration

```python
GEMINI_EMBEDDING_MODEL = "models/text-embedding-004"
```

### Implementation

```python
# Uses the SAME Gemini API key from AI Studio
result = gemini_model.embed_content(
    content=texts,
    output_dimensionality=768,
)
```

### Free Tier

| Limit | Value |
| :--- | :--- |
| **Cost** | Free with Gemini API key |
| **Dimensions** | 768 (matches Vertex AI text-embedding-004) |
| **Rate limit** | 1,500 requests per day |

---

## 3. 👁️ Gemini Vision

**Purpose:** Captions and analyzes images submitted with citizen complaints to extract visual context and evidence.

**Replaces:** Vertex AI Vision API, Cloud Vision API (both paid)

### Usage Locations

| File | Usage |
| :--- | :--- |
| `tools/vision_tool.py` | `VisionTool.caption_image()` — sends image to Gemini for description |
| `agents/intake_agent.py` | Image evidence processing pipeline |

### Implementation

```python
# FREE: Uses Gemini API directly (no Vertex AI needed)
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content([image_part, caption_prompt])
```

---

## 4. 🎤 Browser Web Speech API

**Purpose:** Transcribes audio recordings of citizen complaints into text.

**Replaces:** Google Cloud Speech-to-Text v2 (paid — $0.006/speech second)

### Usage Locations

| File | Usage |
| :--- | :--- |
| `frontend/src/App.jsx` | `webkitSpeechRecognition` / `SpeechRecognition` API |
| `tools/speech_tool.py` | Backend mock for testing |

### Implementation

Transcription happens entirely in the browser (client-side):

```javascript
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = 'en-IN';
recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    // Send transcript to backend for processing
};
```

### Benefits

- **Completely free** — no API costs
- **Unlimited usage** — no rate limits
- **Low latency** — processes locally
- **No GCP required** — runs in any modern browser

---

## 5. 📍 Google Maps Embed API (Free)

**Purpose:** Displays ward-level maps and issue locations in the frontend dashboard.

**Replaces:** Full Google Maps JavaScript API (paid after $200/month credit)

### Usage

```html
<!-- FREE embed — no API key required for basic usage -->
<iframe
    src="https://www.google.com/maps/embed/v1/place?key=YOUR_KEY&q=Pune"
    allowfullscreen>
</iframe>
```

### Free Tier

| Feature | Limit |
| :--- | :--- |
| Maps Embed API | Free for all usage |
| Maps JavaScript API | $200/month free credit |
| Geocoding API | $200/month free credit |

---

## 6. 🎨 Google Fonts + Material Icons

**Purpose:** Provides typography and icons for the React frontend.

### Usage

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
```

---

## 7. 🔐 Firebase Authentication (Spark — Optional)

**Purpose:** JWT-based authentication for role-based access control (citizen, officer, admin).

**Replaces:** Custom auth with bcrypt + PyJWT (already built-in)

### Integration

The platform uses built-in JWT authentication with PyJWT + bcrypt. Firebase Auth is available as an enhancement:

```python
# Current: demo auth with mock credentials
# Future option: Firebase Auth with Google Sign-In
```

### Firebase Spark Plan

| Feature | Limit |
| :--- | :--- |
| Authentication | 10,000 users/month |
| Cost | **Free forever** |

---

## 🔧 Environment Variables Summary

| Variable | Service | Required? | Source |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | All AI features | Optional (mock mode default) | [Google AI Studio](https://aistudio.google.com/) |
| `GEMINI_MODEL` | AI model selection | No (default: `gemini-2.5-flash`) | — |
| `GOOGLE_MAPS_API_KEY` | Maps geocoding | Optional (mock mode default) | Google Cloud Console |
| `APP_MODE` | Mock vs real | No (default: `local`) | — |

---

## 📋 FREE Stack vs Original GCP Comparison

| Original GCP (Paid) | Free Alternative | Savings |
| :--- | :--- | :--- |
| Vertex AI Gemini | Gemini API (AI Studio) | ~$3.50/1K tokens → **$0** |
| Vertex AI Embeddings | Gemini Embeddings API | ~$0.001/1K tokens → **$0** |
| Vertex AI Vector Search | FAISS (local) | ~$300+/month → **$0** |
| Firestore | SQLite (local) | ~$30+ / month → **$0** |
| BigQuery | DuckDB (local) | ~$5/TB queried → **$0** |
| Cloud Pub/Sub | Python asyncio.Queue | ~$0/month (free tier) → **$0** |
| Cloud Run | uvicorn / Render / Railway | ~$0 for low traffic → **$0** |
| Secret Manager | `.env` file | ~$6/month → **$0** |
| Cloud Storage | Local filesystem | ~$0.026/GB → **$0** |
| Cloud Speech-to-Text | Browser Web Speech API | ~$0.006/speech second → **$0** |

**Total monthly savings: $350+ per month** 🎉

---

*For questions about Google AI Studio setup, visit [aistudio.google.com](https://aistudio.google.com/)*
