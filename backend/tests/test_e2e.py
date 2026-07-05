"""End-to-End integration tests for Sampark AI Platform (FREE Stack).

All API calls are mocked to use the in-memory local DB and MockGeminiModel.
No GCP services are needed.
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.config import settings
from tools.firestore_tool import FirestoreTool


# The backend already uses MockGeminiModel when APP_MODE=local,
# so we just need to patch the external API tools (maps, weather).


@pytest.fixture(autouse=True)
def clean_db():
    """Clear the local in-memory DB before each test."""
    FirestoreTool._local_db.clear()


@pytest.fixture
def mock_external_apis():
    # Patch MapsTool geocode
    patch_maps = patch("tools.maps_tool.MapsTool.geocode", return_value={
        "lat": 18.5204, "lng": 73.8567, "address": "MG Road, Ward 1", "ward_id": "w1"
    })
    # Patch WeatherTool
    patch_weather = patch("tools.weather_tool.WeatherTool.get_current_and_forecast", return_value={
        "current": {"weather_description": "clear sky", "temp": 28.0},
        "hourly_48h": [],
        "rainfall_forecast_48h": 0.0
    })
    with patch_maps, patch_weather:
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
    assert token is not None

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
    assert issue_id in FirestoreTool._local_db.get("issues", {}), \
        f"Issue {issue_id} not found in local DB"
    assert session_id in FirestoreTool._local_db.get("sessions", {}), \
        f"Session {session_id} not found in local DB"

    # 4. Check that the workflow agent created a task in local DB
    task_id = f"task_{issue_id}"
    assert task_id in FirestoreTool._local_db.get("tasks", {}), \
        f"Task {task_id} not found in local DB"
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
        assert issue_id in issue_ids, \
            f"Issue {issue_id} not found in top_critical_issues"
