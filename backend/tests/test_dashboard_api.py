"""Unit tests for Dashboard API endpoints (Task 16)."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.tests.test_gateway import _make_token

@pytest.fixture
def admin_token():
    return _make_token(user_id="admin1", role="government_officer", ward_ids=["*"])
    
@pytest.fixture
def leader_token():
    return _make_token(user_id="leader1", role="community_leader", ward_ids=["w1"])

@pytest.mark.asyncio
async def test_dashboard_ward_filtering(admin_token, leader_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Admin gets everything
        resp_admin = await client.get("/analytics/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp_admin.status_code == 200
        admin_data = resp_admin.json()
        assert len(admin_data["heatmap"]) == 2 # Mock data has w1 and w2
        
        # Leader only gets w1
        resp_leader = await client.get("/analytics/dashboard", headers={"Authorization": f"Bearer {leader_token}"})
        assert resp_leader.status_code == 200
        leader_data = resp_leader.json()
        assert len(leader_data["heatmap"]) == 1
        assert leader_data["heatmap"][0]["ward_id"] == "w1"

@pytest.mark.asyncio
async def test_dashboard_sse_stream(leader_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Stream endpoint test using httpx
        # Read the stream lines
        async with client.stream("GET", "/analytics/dashboard/stream", headers={"Authorization": f"Bearer {leader_token}"}) as response:
            assert response.status_code == 200
            
            lines = []
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    lines.append(line)
                    
            # Leader (w1) should only see w1 events. 
            # The mock generator emits t1 (w1), t2 (w2), t3 (w1).
            # So leader should only get t1 and t3.
            assert len(lines) == 2
            assert "t1" in lines[0]
            assert "t3" in lines[1]
            assert "t2" not in "".join(lines)
