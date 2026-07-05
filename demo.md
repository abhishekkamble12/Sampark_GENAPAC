# 🕹️ Sampark AI Platform — Demo Walkthrough & Setup Guide (FREE Stack)

This guide provides step-by-step instructions to set up the **Sampark AI Platform** on a fresh machine and run the full end-to-end interactive demo. **No Google Cloud billing required.**

---

## 🛠️ Quick Start (3 Commands)

```bash
# 1. Install Backend dependencies
pip install -e ".[dev]"

# 2. Install Frontend dependencies
cd frontend && npm install && cd ..

# 3. Run the automated test suite
python -m pytest
```

---

## 📋 Comprehensive Setup & Configuration

### Step 1: Backend Setup
1. Make sure you are using **Python 3.11+**.
2. Run the dependency installation:
   ```bash
   pip install -e ".[dev]"
   ```
3. Create a `.env` file in the project root:
   ```env
   # Application Mode (local runs with mock fallback DB and APIs)
   APP_MODE=local

   # JWT Config
   JWT_SECRET=mock_secret_key
   JWT_ALGORITHM=HS256

   # API Keys (optional in local mode)
   GEMINI_API_KEY=
   GOOGLE_MAPS_API_KEY=
   OPENWEATHER_API_KEY=
   ```

### Step 2: Frontend Setup
1. Make sure you have **Node.js (v18+)** installed.
2. Install packages:
   ```bash
   cd frontend
   npm install
   ```

### Step 3: Run Tests
```bash
python -m pytest
```

---

## 🕹️ Interactive Demo Walkthrough

### Step 1: Start Backend API Gateway
From the root directory:
```bash
uvicorn backend.main:app --reload --port 8000
```
*API docs at `http://localhost:8000/docs`*

### Step 2: Start Frontend Client
From the `frontend` directory:
```bash
npm run dev
```
*Open `http://localhost:5173` in your browser.*

### Step 3: Run the Demo Flow

#### 1. Authentication
| Role | Username | Password |
| :--- | :--- | :--- |
| **Officer / Admin** | `admin` | `password` |
| **Community Leader** | `leader_w1` | `password` |

#### 2. Citizen Issue Reporting
- Navigate to the **Report Issue** tab.
- Enter a realistic municipal complaint, e.g.:
  > *"Large water leak on the main road in Ward 1 causing road degradation."*
- Click **Submit to Decision Engine**.
- Watch the **Real-Time Agent Progress** stream update as each agent completes.
- View the complete **AI Decision Trace** with validation, prediction, and recommendation details.

#### 3. Real-Time Decision Intelligence Dashboard
- Open a second browser tab and log in as `admin`.
- Navigate to the **Dashboard** tab.
- Monitor global municipal metrics:
  - **Community Health Score**
  - **Critical Open Tasks Count**
  - **Geospatial Risk Levels** per ward
  - **AI Insights** — automated trend analysis

#### 4. Municipal Knowledge Base Administration
- Navigate to the **Knowledge Base** tab (admin only).
- Upload PDF policy documents for RAG indexing.
- Manage existing policy references.

---

## 🌐 Deployment (Optional — Free Platforms)

### Deploy to Render (backend)
1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set Build Command: `pip install -e ".[dev]"`
5. Set Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port 10000`

### Deploy to Vercel (frontend)
1. Connect your GitHub repo to [vercel.com](https://vercel.com)
2. Set Root Directory: `frontend`
3. Set Build Command: `npm run build`
4. Set Output Directory: `dist`
