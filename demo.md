# 🕹️ Sampark AI Platform - Demo Walkthrough & Setup Guide

This guide provides step-by-step instructions to set up the **Sampark AI Platform** on a fresh machine and run the full end-to-end interactive demo.

---

## 🛠️ Quick Start (3 Commands)

You can run and verify the entire backend, frontend, and tests on a fresh machine with three commands:

```bash
# 1. Install Backend dependencies in editable development mode
pip install -e ".[dev]"

# 2. Install Frontend dependencies
cd frontend && npm install && cd ..

# 3. Run the automated test suite
python -m pytest
```

---

## 📋 Comprehensive Setup & Configuration

Follow these steps for a complete local execution configuration:

### Step 1: Backend Setup
1. Make sure you are using **Python 3.12+**.
2. Run the dependency installation:
   ```bash
   pip install -e ".[dev]"
   ```
3. Set up the local environment variables. Create a `.env` file in the project root:
   ```env
   # Application Mode (local runs with mock fallback DB and APIs)
   APP_MODE=local

   # JWT Config
   JWT_SECRET=mock_secret_key
   JWT_ALGORITHM=HS256

   # Mock variables for local mode (Not required to contain real keys in local mode)
   GCP_PROJECT_ID=sampark-demo
   BIGQUERY_DATASET=sampark_analytics
   GEMINI_API_KEY=
   GOOGLE_MAPS_API_KEY=
   OPENWEATHER_API_KEY=
   ```

### Step 2: Frontend Setup
1. Make sure you have **Node.js (v18+)** installed.
2. Navigate to the `frontend` directory and install the packages:
   ```bash
   cd frontend
   npm install
   ```

### Step 3: Run Tests
Validate the application backend, LangGraph node transitions, memory persistence, and Gateway APIs using:
```bash
python -m pytest
```

---

## 🕹️ Interactive Demo Walkthrough

Once setup is complete, run the application locally to present the demo.

### Step 1: Start Backend API Gateway
From the root directory:
```bash
uvicorn backend.main:app --reload --port 8000
```
*The interactive API documentation is available at `http://localhost:8000/docs`.*

### Step 2: Start Frontend Client
From the `frontend` directory:
```bash
npm run dev
```
*Open `http://localhost:5173` in your browser.*

### Step 3: Run the Demo Flow

#### 1. Authentication & Role-Based Access Control (RBAC)
- **Officer Login**: 
  - Username: `admin`
  - Password: `password`
- **Community Leader Login**: 
  - Username: `leader_w1`
  - Password: `password`

#### 2. Citizen Issue Reporting with Real-Time Progress Stream
- Navigate to the **Report Issue** tab.
- Enter a realistic municipal complaint, for example:
  > *"Large water leak on the main road in Ward 1 causing road degradation."*
- Click **Submit to Decision Engine**.
- **Visual Checkpoints**: Watch the **Real-Time Agent Progress** section. An EventSource SSE stream (`/chat/stream/{session_id}`) will print each active agent checkpoint as they complete (e.g. `Intake Node`, `Validation Node`, `Workflow Node`).
- **Grounded Results**: View the computed response:
  - **Issue ID** and **Session ID**.
  - **Assigned Department** (e.g. *Water Supply Department*).
  - **Validation Confidence Score** (e.g. *95%*).
  - **NLP Citizen Message** formatted by the response agent.
  - **Grounded Municipal Policy Action** retrieved using Vertex AI Search.

#### 3. Real-Time Decision Intelligence Dashboard
- Open a second browser tab and log in as `admin`.
- Navigate to the **Dashboard** tab.
- Monitor global municipal metrics:
  - **Community Health Score**
  - **Critical Open Tasks Count**
  - **Geospatial Risk Levels** per ward visualized on risk score bars.
  - **Critical Action List** containing active tickets.
- **SSE Live Push Alert Test**: Keep both tabs visible side-by-side. File a new ticket in the first tab. Watch the Dashboard in the second tab automatically update in real-time (via `/analytics/dashboard/stream`) within 5 seconds without a page refresh!

#### 4. Municipal Knowledge Base Administration
- Navigate to the **Knowledge Base** tab (visible to administrators).
- Upload PDF policy acts (such as road repair rules or water usage plans).
- Manage existing policy references, with support for index updates and cascaded document deletions.
