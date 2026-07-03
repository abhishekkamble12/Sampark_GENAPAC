"""End-to-End integration tests for Sampark AI Platform."""

import pytest
import time
import jwt
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.config import settings
from tools.firestore_tool import FirestoreTool

class MockResponse:
    def __init__(self, text):
        self.text = text

def mock_generate_content(prompt):
    prompt_str = str(prompt)
    if "sentiment" in prompt_str:
        return MockResponse('{"sentiment_score": -0.8}')
    elif "Language identification" in prompt_str or "language" in prompt_str:
        return MockResponse('{"language": "en", "is_english": true, "translated_text": ""}')
    elif "extract" in prompt_str or "extracted information" in prompt_str:
        return MockResponse('{"type": "road", "location": "MG Road", "description": "pothole on MG Road"}')
    elif "retrieved" in prompt_str or "Retrieved Policies" in prompt_str:
        return MockResponse('{"action": "Deploy repair crew to MG Road", "rationale": "High severity pothole posing safety risk", "cited_policies": ["Road Repair Act"]}')
    return MockResponse('{}')

@pytest.fixture
def mock_external_apis():
    # Patch Gemini generate_content
    patch_gemini = patch("google.generativeai.GenerativeModel.generate_content", side_effect=mock_generate_content)
    
    # Patch MapsTool geocode
    patch_maps = patch("tools.maps_tool.MapsTool.geocode", return_value={"lat": 18.5204, "lng": 73.8567, "address": "MG Road, Ward 1", "ward_id": "w1"})
    
    # Patch WeatherTool get_current_and_forecast
    patch_weather = patch("tools.weather_tool.WeatherTool.get_current_and_forecast", return_value={
        "current": {"weather_description": "clear sky", "temp": 28.0},
        "hourly_48h": [],
        "rainfall_forecast_48h": 0.0
    })
    
    # Patch BigQueryTool read_community_health_score
    patch_bq = patch("tools.bigquery_tool.BigQueryTool.read_community_health_score", return_value=85.0)
    
    # Patch Retriever retrieve method
    patch_retriever = patch("rag.retriever.Retriever.retrieve", return_value=(
        [{"doc_name": "Road Repair Act", "page_number": 1, "text": "Pothole repairs should be completed within 72 hours."}],
        False
    ))
    
    # Patch VertexSearchTool methods (just in case)
    patch_vertex_embed = patch("tools.vertex_tool.VertexSearchTool.get_embeddings", return_value=[[0.1] * 768])
    patch_vertex_search = patch("tools.vertex_tool.VertexSearchTool.search_vectors", return_value=[{"id": "doc_0", "score": 0.85}])
    
    with patch_gemini, patch_maps, patch_weather, patch_bq, patch_retriever, patch_vertex_embed, patch_vertex_search:
        yield

@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

@pytest.mark.asyncio
async def test_e2e_flow(client, mock_external_apis):
    # 1. Login as officer/admin to get JWT token
    login_payload = {
        "username": settings.DEMO_ADMIN_USERNAME,
        "password": settings.DEMO_ADMIN_PASSWORD
    }
    login_resp = await client.post("/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Submit a new issue report
    issue_payload = {
        "description": "Severe pothole on MG Road causing traffic issues.",
        "image_url": "http://example.com/pothole.jpg",
        "location": {
            "lat": 18.5204,
            "lng": 73.8567,
            "ward_id": "w1"
        }
    }
    
    issue_resp = await client.post("/issues", json=issue_payload, headers=headers)
    assert issue_resp.status_code == 200
    
    data = issue_resp.json()
    assert "session_id" in data
    assert "issue_id" in data
    assert "task_id" in data
    assert "message" in data
    assert "issue_type" in data
    assert "priority" in data
    assert "department" in data
    assert "confidence" in data
    assert "next_action" in data
    
    session_id = data["session_id"]
    issue_id = data["issue_id"]
    
    # 3. Check that the issue and session have been persisted in local DB
    assert issue_id in FirestoreTool._local_db.get("issues", {})
    assert session_id in FirestoreTool._local_db.get("sessions", {})
    
    # 4. Check that the workflow agent created a task in local DB
    task_id = f"task_{issue_id}"
    assert task_id in FirestoreTool._local_db.get("tasks", {})
    task = FirestoreTool._local_db["tasks"][task_id]
    assert task["issue_id"] == issue_id
    assert task["status"] == "open"
    assert task["priority"] in ("Low", "Medium", "High", "Critical")
    
    # 5. Fetch dashboard data and verify the issue/task is reflected
    dash_resp = await client.get("/analytics/dashboard", headers=headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    
    assert "health_score" in dash_data
    assert "heatmap" in dash_data
    
    # Verify the created critical issue is in the top list
    top_issues = dash_data.get("top_critical_issues", [])
    issue_ids = [iss["id"] for iss in top_issues]
    if task["priority"] in ("High", "Critical"):
        assert issue_id in issue_ids
