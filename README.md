# Sampark AI Platform

Sampark AI turns citizen complaints into explainable, policy-grounded government action using multi-agent AI, RAG, risk prediction, and live task routing.

> *Cities do not need another complaint form. They need a decision intelligence layer that validates reports, predicts risk, cites policy, routes tasks, and helps officers act faster.*

---

## 🏗️ System Architecture

```mermaid
graph TD
    A[Citizen / Portal] -->|POST /issues| B[FastAPI Gateway]
    B -->|ainvoke| C[LangGraph Orchestrator]
    
    C --> D[Intake Node]
    D --> E[Validation Node]
    E --> F[Data Intelligence Node]
    F --> G[Prediction Node]
    G --> H[Recommendation Node]
    H --> I[Workflow Node]
    I --> J[Notification Node]
    
    E -->|Maps & Weather API| K[Corroboration & Geocoding]
    H -->|Vertex AI Search RAG| L[Municipal Policies]
    I -->|Firestore & Pub/Sub| M[Task Persistence & Topic Events]
    
    B -->|GET /analytics/dashboard| N[Dashboard Services]
    N -->|BigQuery View / Local DB| O[Risk Analytics & Health Scores]
```

---

## 💻 Local Development Setup

Follow these steps to set up the backend and frontend services locally.

### 1. Backend Setup

1. **Install Dependencies**:
   Initialize development mode package bindings and linting/testing suites:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory based on `.env.example`:
   ```bash
   # Agent Keys & Configuration
   GEMINI_API_KEY=your_gemini_api_key_here
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
   OPENWEATHER_API_KEY=your_openweather_api_key_here
   
   # Google Cloud Settings
   GCP_PROJECT_ID=sampark-genapac
   BIGQUERY_DATASET=sampark_dataset
   APP_MODE=local  # Runs in-memory local DB fallback if set to 'local'
   ```

### 2. Frontend Setup

The frontend is a gorgeous Vite-powered React client application built with custom glassmorphism styling.

```bash
cd frontend
npm install
```

---

## 🧪 Running Tests

Validate the application backend, LangGraph node transitions, persistence layers, and gateway endpoints:

```bash
python -m pytest
```

This will run all units and the comprehensive end-to-end integration test suite (`backend/tests/test_e2e.py`).

---

## 🚀 Running the Platform Locally

### Option A: One-Command Start (Windows)
Run the launcher script from the root directory:
```bash
start-demo.bat
```
This automatically verifies dependencies, launches the FastAPI backend and React Vite frontend in separate console windows, and opens your browser.

### Option B: Manual Execution
Ensure both services are running concurrently to test the complete flow:

1. **Start Backend API Gateway**:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   *The API docs will be available at `http://localhost:8000/docs`.*

2. **Start Frontend Client**:
   ```bash
   cd frontend
   npm run dev
   ```
   *Open `http://localhost:5173` in your browser.*

For a detailed interactive guide, refer to the [demo.md](file:///d:/Genapac/Sampark_GENAPAC/demo.md) guide.


## 🕹️ Interactive Demo Walkthrough

Once the platform is running locally, follow these steps to experience the complete workflow:

### 1. Authentication
- Open `http://localhost:5173` in your browser.
- **Officer Login**: Use username `admin` and password `password`.

### 2. Citizen Issue Report Portal
- Go to the **Report Issue** tab.
- Click **✨ Quick Fill Sample** or enter a description (e.g., *"Large water leak on the main road in Ward 1 causing road degradation."*).
- Select a Ward ID and click **Submit to Decision Engine**.
- **Real-Time Agent Progress**: An EventSource SSE stream will display node execution checkpoints (`Intake Node`, `Validation Node`, `Workflow Node`) as they complete.
- **Decision Results**: When processing completes, you will see the generated Session ID, Assigned Department, Validation Confidence Score, and the **AI Decision Trace** containing the exact **Policy Citation**.

### 3. Officer Decision Intelligence Dashboard
- Go to the **Dashboard** tab.
- Inspect the **Critical Action Queue** showing priority tasks with real-time **SLA Countdowns** and **Estimated Impact**.
- Use the **Approve**, **Escalate**, or **Request Evidence** buttons to manage human-in-the-loop workflows.
- See **Geospatial Risk Levels** per ward visualized on risk score bars.

### 4. The "Wow Moment": Dynamic Policy Grounding
- Go to the **Knowledge Base** tab (visible to Admin/Officer).
- Upload a new dummy policy document named `Drone Inspection Protocol.pdf` containing the text: *"All severe structural complaints require drone inspection."*
- Go back to **Report Issue** and submit a related complaint.
- Watch the AI recommendation dynamically change to cite your new protocol and recommend drone deployment! This proves the RAG pipeline operates locally and dynamically.

---

## ☁️ Production Deployment Guide

Deploy the application to Google Cloud Run only after verifying local demo behavior.

### 1. Build and Run Containers (Docker)
Build multi-stage production-ready containers:
```bash
# Build Backend
docker build -t gcr.io/sampark-genapac/backend:latest ./backend

# Build Frontend (Nginx SPA proxy)
docker build -t gcr.io/sampark-genapac/frontend:latest ./frontend
```

### 2. Cloud Run Deploy
```bash
gcloud run deploy sampark-backend \
  --image gcr.io/sampark-genapac/backend:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars APP_MODE=production

gcloud run deploy sampark-frontend \
  --image gcr.io/sampark-genapac/frontend:latest \
  --platform managed \
  --region us-central1
```

### 3. Terraform Infrastructure
Provision project-level resources (BigQuery, Firestore, GCS buckets, Pub/Sub topics) securely:
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

---

## 🖼️ Screenshots

Below are high-fidelity mockups of the Sampark AI platform interface showing the complete decision intelligence flow:

### 1. Citizen Report Portal
![Citizen Report Portal](file:///C:/Users/Abhishek/.gemini/antigravity-ide/brain/2856b871-5636-45f3-b0e7-a86ffaffb4cc/report_1783444390112.png)

### 2. AI Decision Trace Panel & Agent Reasoning
![AI Decision Trace](file:///C:/Users/Abhishek/.gemini/antigravity-ide/brain/2856b871-5636-45f3-b0e7-a86ffaffb4cc/ai_trace_1783444406723.png)

### 3. Officer Decision Intelligence Command Center
![Officer Command Center Dashboard](file:///C:/Users/Abhishek/.gemini/antigravity-ide/brain/2856b871-5636-45f3-b0e7-a86ffaffb4cc/dashboard_1783444375151.png)

### 4. Knowledge Base Administration
![Knowledge Base](file:///C:/Users/Abhishek/.gemini/antigravity-ide/brain/2856b871-5636-45f3-b0e7-a86ffaffb4cc/knowledge_base_1783444421485.png)
