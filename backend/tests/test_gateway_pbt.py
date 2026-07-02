"""Property-based tests for FastAPI Gateway (Task 13)."""

import pytest
from httpx import AsyncClient, ASGITransport
from hypothesis import given, settings
from hypothesis import strategies as st
from backend.main import app

@given(st.text())
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_jwt_rejection_pbt(bad_token):
    """13.11 Any request with missing/malformed JWT always returns HTTP 401."""
    # We must run this using a test client inside hypothesis, 
    # but hypothesis and asyncio need a bit of wrapper care.
    # We use a dedicated async client per test execution.
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Pass garbage as the token
        headers = {"Authorization": f"Bearer {bad_token}"}
        resp = await client.post("/issues", headers=headers)
        
        # It must safely reject it without crashing (500)
        assert resp.status_code == 401
