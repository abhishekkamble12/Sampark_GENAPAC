"""Unit tests for FastAPI Gateway (Task 13)."""

import time
import jwt
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.middleware import JWT_SECRET, JWT_ALGORITHM, _rate_limit_cache

def _make_token(user_id="u1", role="citizen", ward_ids=None, expired=False):
    if ward_ids is None:
        ward_ids = []
    exp = time.time() - 3600 if expired else time.time() + 3600
    payload = {"user_id": user_id, "role": role, "ward_ids": ward_ids, "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

@pytest.fixture
def client():
    # Clear rate limit cache before each test
    _rate_limit_cache.clear()
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_jwt_rejection(client):
    # Missing token
    resp1 = await client.post("/issues")
    assert resp1.status_code == 401
    
    # Invalid token format
    resp2 = await client.post("/issues", headers={"Authorization": "Bearer badtoken"})
    assert resp2.status_code == 401
    
    # Expired token
    token_exp = _make_token(expired=True)
    resp3 = await client.post("/issues", headers={"Authorization": f"Bearer {token_exp}"})
    assert resp3.status_code == 401

@pytest.mark.asyncio
async def test_rbac_enforcement(client):
    # Leader of w1 trying to access w2
    token_w1 = _make_token(user_id="leader1", role="community_leader", ward_ids=["w1"])
    resp_fail = await client.get("/analytics/ward/w2", headers={"Authorization": f"Bearer {token_w1}"})
    assert resp_fail.status_code == 403
    
    # Leader of w1 trying to access w1
    resp_ok = await client.get("/analytics/ward/w1", headers={"Authorization": f"Bearer {token_w1}"})
    assert resp_ok.status_code == 200
    
    # Admin accessing w2
    token_admin = _make_token(user_id="admin1", role="government_officer", ward_ids=["*"])
    resp_admin = await client.get("/analytics/ward/w2", headers={"Authorization": f"Bearer {token_admin}"})
    assert resp_admin.status_code == 200

@pytest.mark.asyncio
async def test_rate_limiting(client):
    token = _make_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Fire 60 valid requests (rate limit is 60)
    for _ in range(60):
        # We don't care about pydantic body errors (422) for this, 
        # because rate limit triggers BEFORE pydantic body parsing.
        resp = await client.post("/issues", headers=headers)
        # Even if 422, it passed auth and rate limiting
        assert resp.status_code in (200, 422)
        
    # The 61st request should hit 429
    resp_429 = await client.post("/issues", headers=headers)
    assert resp_429.status_code == 429
    assert "Retry-After" in resp_429.headers
