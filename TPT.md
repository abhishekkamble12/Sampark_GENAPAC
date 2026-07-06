# Third-Party Services Reference — Sampark AI Platform (FREE Stack)

This document catalogs all **non-Google third-party services** used by the Sampark AI Platform.  
**All services are optional** — the platform runs entirely in `APP_MODE=local` with zero external dependencies.

---

## 📋 Third-Party Service Inventory

| # | Service | Category | Required? | Free Tier Available |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **OpenWeatherMap** | Weather Data | ❌ Local mock | ✅ 1,000 calls/day |
| 2 | **SendGrid** | Email Delivery | ❌ Local fallback | ✅ 100 emails/day |
| 3 | **Twilio** | SMS / WhatsApp | ❌ Local fallback | ✅ $15 trial credit |
| 4 | **FAISS** | Vector Search | ✅ Core (local, free) | ✅ Open source |
| 5 | **DuckDB** | Analytics | ✅ Core (local, free) | ✅ Open source |
| 6 | **SQLite** | Database | ✅ Core (local, free) | ✅ Open source |

---

## ▶️ Run With Zero Dependencies

```bash
# No API keys needed. Everything is mocked:
APP_MODE=local
pip install -e ".[dev]"
uvicorn backend.main:app --port 8000
```

---

## 1. 🌤️ OpenWeatherMap (Optional)

**Purpose:** Provides real-time weather data for the Validation Agent (to corroborate flood/drainage complaints) and the Prediction Agent (for flood risk forecasting).

### Integration

| Property | Value |
| :--- | :--- |
| **API** | One Call API 3.0 |
| **Base URL** | `https://api.openweathermap.org/data/3.0/onecall` |
| **Auth** | API Key (query param `appid`) |
| **Free tier** | 1,000 calls/day |
| **SDK** | `httpx` (direct HTTP) |

### Local Mode

In `APP_MODE=local`, returns mock weather data:
```python
{"current": {"temp": 24.0, "weather_description": "heavy rain", ...},
 "rainfall_forecast_48h": 25.0}
```

### Setup (Optional)

```bash
OPENWEATHER_API_KEY=your_key_here
```

Sign up: [openweathermap.org](https://openweathermap.org/api) (free tier: 1,000 calls/day)

---

## 2. 📧 SendGrid (Optional)

**Purpose:** Sends transactional email notifications for issue status updates.

### Integration

| Property | Value |
| :--- | :--- |
| **Python SDK** | `sendgrid` |
| **Auth** | API Key (`SENDGRID_API_KEY`) |
| **Free tier** | 100 emails/day |

### Setup (Optional)

```bash
SENDGRID_API_KEY=SG.xxxxx.xxxxx
```

Sign up: [sendgrid.com](https://sendgrid.com) (free: 100 emails/day)

---

## 3. 📱 Twilio (Optional)

**Purpose:** Sends SMS and WhatsApp notifications for issue status updates.

### Integration

| Property | Value |
| :--- | :--- |
| **Python SDK** | `twilio` |
| **Auth** | Account SID + Auth Token |
| **Free tier** | $15 trial credit (~400 SMS) |

### Setup (Optional)

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
```

Sign up: [twilio.com](https://twilio.com) (free trial: ~$15 credit)

---

## 4. 🗄️ FAISS (Core — Free, Open Source)

**Purpose:** Local vector similarity search for RAG pipeline. Replaces Vertex AI Vector Search.

| Property | Value |
| :--- | :--- |
| **Package** | `faiss-cpu` |
| **License** | MIT (open source) |
| **Cost** | **$0** |
| **Performance** | Sub-millisecond search on 100K+ vectors |

---

## 5. 📊 DuckDB (Core — Free, Open Source)

**Purpose:** In-process analytical database for dashboard queries. Replaces BigQuery.

| Property | Value |
| :--- | :--- |
| **Package** | `duckdb` |
| **License** | MIT (open source) |
| **Cost** | **$0** |
| **Performance** | Sub-second queries on 100K+ rows |

---

## 6. 🗄️ SQLite (Core — Free, Open Source)

**Purpose:** Local document database for operational data. Replaces Firestore.

| Property | Value |
| :--- | :--- |
| **Package** | `aiosqlite` |
| **License** | Python standard library / open source |
| **Cost** | **$0** |
| **Performance** | Excellent for local workloads |

---

## 🔧 Python Dependencies

```toml
[project.dependencies]
# Core (FREE, open source)
fastapi                # REST API framework
uvicorn                # ASGI server
langgraph              # Multi-agent orchestration
google-generativeai    # FREE Gemini API (AI Studio)
faiss-cpu              # FREE vector search (replaces Vertex AI Vector Search)
aiosqlite              # FREE database (replaces Firestore)
duckdb                 # FREE analytics (replaces BigQuery)

# Optional (free tiers available)
sendgrid               # FREE tier: 100 emails/day
twilio                 # FREE trial: $15 credit
```

---

## 💰 Total Cost

| Scenario | Monthly Cost |
| :--- | :--- |
| **Local mode** (no API keys) | **$0** |
| **All optional services** | ~$5-10/mo (OpenWeatherMap starter) |

---

## 🔑 Environment Variables

```bash
# Optional — not needed for local development
OPENWEATHER_API_KEY=       # For weather data
SENDGRID_API_KEY=          # For email notifications
TWILIO_ACCOUNT_SID=        # For SMS/WhatsApp
TWILIO_AUTH_TOKEN=         # For SMS/WhatsApp
```

---

*For local development, set `APP_MODE=local` and no API keys are required.*
