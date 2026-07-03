Critical Issues To Fix First
Issue ID mismatch breaks the end-to-end flow
In [backend/main.py (line 188)](D:/Genapac/Sampark_GENAPAC/backend/main.py:188), the API creates an issue_id. But [agents/intake_agent.py](D:/Genapac/Sampark_GENAPAC/agents/intake_agent.py) later creates a new issue ID inside the intake node.
Result:
API returns issue_id = A
LangGraph workflow creates task for issue_id = B
Firestore saves issue under key A but issue body may contain id B
Frontend/test expects task_A but backend created task_B
This is probably the most important bug. Fix by preserving the existing state["issue"]["id"] inside intake_agent.py instead of generating a new one.
Frontend likely will not build
[frontend/src/api.js (line 1)](D:/Genapac/Sampark_GENAPAC/frontend/src/api.js:1) imports:
import { jwtDecode } from './App.jsx';
But App.jsx does not export jwtDecode, and api.js does not use it anyway. Remove that import.
Tests cannot currently run in this environment
I tried:
python -m pytest
It failed with:
No module named pytest
So your setup is still not reproducible on a fresh environment. First fix should be:
pip install -e ".[dev]"
python -m pytest
Frontend build could not be verified
I tried:
npm run build
but npm is not installed/available in this environment. You should verify this locally once Node.js is available.
LangGraph parallel fan-out may conflict
[agents/graph.py](D:/Genapac/Sampark_GENAPAC/agents/graph.py) fans out from data_intelligence_node to both analytics_node and prediction_node. Both branches likely return the full state. In LangGraph, parallel branches writing the same keys can cause state merge conflicts unless reducers are defined.
Fix options:
Option A: Make analytics and prediction sequential for now.
Option B: Add reducer annotations to GraphState.
Option C: Make each parallel node return only its own changed field.
For demo speed, I would choose Option A first.
Production Pub/Sub publish is probably wrong
[agents/workflow_agent.py (line 110)](D:/Genapac/Sampark_GENAPAC/agents/workflow_agent.py:110) does:
await pubsub_client.publish("task-created", event_payload)
Google Pub/Sub PublisherClient.publish() is not an async coroutine in the usual client. It returns a future and also expects bytes payload. Your mock works locally, but production may fail.
SSE streams skip authentication
[backend/middleware.py (line 51)](D:/Genapac/Sampark_GENAPAC/backend/middleware.py:51) skips auth for:
/chat/stream/*
/analytics/dashboard/stream
This makes frontend EventSource easy, but anyone can connect to streams. Better approach:
Local demo: allow unauthenticated streams
Production: use token query param or cookie auth and validate session ownership
High Priority Improvements
Create a real local LLM/mock mode
Right now [agents/graph.py](D:/Genapac/Sampark_GENAPAC/agents/graph.py) creates a Gemini model even in local mode. If no API key exists, the graph can degrade unpredictably.
Add:
APP_MODE=local -> MockGeminiModel
APP_MODE=production -> Gemini
The mock should return stable JSON for intake, sentiment, and recommendation.
Make /issues return richer proof
Current response is good, but for best demo return:
{
  "session_id": "...",
  "issue_id": "...",
  "task_id": "...",
  "message": "...",
  "issue_type": "road",
  "department": "Public Works Department",
  "priority": "High",
  "confidence": 0.8,
  "next_action": "Deploy repair crew..."
}
This makes the multi-agent system visible.
Fix local persistence consistency
When /issues completes, save:
issues/{issue_id}
sessions/{session_id}
tasks/{task_id}
Make sure all three reference the same issue_id.
Make dashboard reflect submitted issues
The local dashboard is much better now, but [backend/main.py (line 534)](D:/Genapac/Sampark_GENAPAC/backend/main.py:534) still returns:
"trend_7d": []
Add simple local trend data so the dashboard looks alive.
Improve frontend API config
[frontend/src/api.js (line 3)](D:/Genapac/Sampark_GENAPAC/frontend/src/api.js:3) hardcodes:
const BASE_URL = 'http://localhost:8000';
Use Vite env:
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
Clean visual/text encoding
Several files show broken characters like â€”, ðŸ, etc. This hurts polish. Normalize docs and frontend text to clean UTF-8 or plain ASCII.
Medium Priority Improvements
Auth hardening
Demo users are now configurable in [backend/config.py](D:/Genapac/Sampark_GENAPAC/backend/config.py), which is good. Next, avoid default mock_secret_key in production. Fail startup if APP_MODE=production and JWT secret is weak/missing.

Rate limiting
Current rate limiting is in-memory in [backend/middleware.py (line 18)](D:/Genapac/Sampark_GENAPAC/backend/middleware.py:18). Good for local, not production. Use Redis/Memorystore later.

CORS
[backend/main.py (line 28)](D:/Genapac/Sampark_GENAPAC/backend/main.py:28) allows all origins. Fine for local, unsafe for production. Make it config-based.

RAG quality
The RAG pipeline exists, but the demo needs visible policy citations. Add 2-3 small sample policy documents and seed them automatically in local mode.

Knowledge-base UX
The frontend upload screen exists. Add status states:
uploaded
chunked
embedded
active
failed

Infra/schema alignment
Terraform has tables for issues, community scores, predictions, and tasks. Make sure BigQuery queries in backend/tools use the same column names exactly.

Recommended Fix Order
1. Fix frontend api.js bad import
2. Fix issue_id mismatch between backend and intake agent
3. Add local MockGeminiModel
4. Temporarily make LangGraph analytics/prediction sequential
5. Run pip install -e ".[dev]" and pytest
6. Make /issues return task_id, priority, issue_type
7. Verify frontend build
8. Make dashboard update from submitted issue/task
9. Add production-safe auth/CORS/stream handling
10. Polish README and demo script
Best Demo Narrative
Your final demo should show this exact flow:
Login as officer
Submit road issue
Watch agent checkpoints stream live
See issue classified as road
See confidence score
See recommendation with policy citation
See task assigned to Public Works Department
Open dashboard
See critical issue reflected in ward risk/action list
That one reliable flow will make the project feel excellent. Right now the foundation is strong, but reliability and polish are the difference between “impressive architecture” and “best project.”

Web previewWebsiteOpenOpen in



1:46 PM









Add to chatAsk in side chat