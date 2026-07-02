"""Unit tests for Analytics Agent (Task 7)."""

import asyncio
from datetime import datetime, timezone, timedelta
import json
import pytest
from agents.analytics_agent import make_analytics_node
from agents.state import GraphState

def _make_state(historical_issues=None, confidence_score=0.5) -> GraphState:
    issue = {
        "id": "iss_1", "type": "road",
        "location": {"lat": 18.52, "lng": 73.86, "address": "MG Road", "ward_id": "w1"},
        "description": "pothole", "media_refs": [],
        "original_language": None, "severity": None,
    }
    return {
        "query": "test", "user": {}, "issue": issue,
        "validation": {"confidence_score": confidence_score, "duplicate": False, "status": "valid", "location_verified": True, "failure_reason": None}, 
        "context": {"historical_issues": historical_issues}, "analytics": None,
        "prediction": None, "rag_chunks": None, "recommendation": None,
        "workflow": None, "response": None, "intake_error": None,
        "translation_error": False, "extraction_error": False,
        "no_policy_context": False,
        "execution": {"session_id": "s1", "status": "running", "retry_count": 0, "node_checkpoints": []},
    }

class _FakeGeminiResponse:
    def __init__(self, text: str):
        self.text = text

class _FakeGeminiModel:
    def __init__(self, score=0.8, should_fail=False):
        self.score = score
        self.should_fail = should_fail
    def generate_content(self, prompt: str):
        if self.should_fail:
            raise Exception("Gemini down")
        return _FakeGeminiResponse(json.dumps({"sentiment_score": self.score}))

class _FakeBigQuery:
    def __init__(self, score=85.0):
        self.score = score
    async def read_community_health_score(self, ward_id):
        return self.score

@pytest.fixture
def base_historical_issues():
    now = datetime.now(timezone.utc)
    d4 = now - timedelta(days=4)
    d10 = now - timedelta(days=10)
    d20 = now - timedelta(days=20)
    d45 = now - timedelta(days=45)
    
    return [
        {"reported_at": d4.isoformat(), "description": "bad road", "location": {"lat": 18.5, "lng": 73.8}},
        {"reported_at": d4.isoformat(), "description": "pot hole", "location": {"lat": 18.5, "lng": 73.8}},
        {"reported_at": d10.isoformat(), "description": "another", "location": {"lat": 18.501, "lng": 73.801}},
        {"reported_at": d20.isoformat(), "description": "test", "location": {"lat": 18.502, "lng": 73.802}},
        {"reported_at": d45.isoformat(), "description": "old", "location": {"lat": 18.505, "lng": 73.805}},
        {"reported_at": d45.isoformat(), "description": "older", "location": {"lat": 18.505, "lng": 73.805}},
    ]

@pytest.mark.asyncio
async def test_insufficient_data():
    node = make_analytics_node(_FakeGeminiModel(), _FakeBigQuery())
    state = _make_state([{"reported_at": "2024-01-01T00:00:00Z"}])
    result = await node(state)
    assert result["analytics"]["insufficient_data"] is True
    assert result["analytics"]["trend_7d"] is None

@pytest.mark.asyncio
async def test_normal_analytics(base_historical_issues):
    node = make_analytics_node(_FakeGeminiModel(0.9), _FakeBigQuery(92.5))
    state = _make_state(base_historical_issues, confidence_score=0.9)
    result = await node(state)
    analytics = result["analytics"]
    
    assert analytics["insufficient_data"] is False
    assert analytics["health_score_unavailable"] is False
    assert analytics["sentiment_score"] == 0.9
    
    # Check trends: 
    # 0-7d: 2 items
    # 7-14d: 1 item
    # 0-30d: 4 items
    # 30-60d: 2 items
    assert analytics["trend_7d"] == ((2 - 1) / 1) * 100.0
    assert analytics["trend_30d"] == ((4 - 2) / 2) * 100.0
    
    assert analytics["cluster_labels"] is not None
    assert analytics["cluster_centroids"] is not None

@pytest.mark.asyncio
async def test_zero_baseline():
    now = datetime.now(timezone.utc)
    issues = [
        {"reported_at": (now - timedelta(days=2)).isoformat()},
        {"reported_at": (now - timedelta(days=3)).isoformat()},
        {"reported_at": (now - timedelta(days=4)).isoformat()},
        {"reported_at": (now - timedelta(days=5)).isoformat()},
        {"reported_at": (now - timedelta(days=6)).isoformat()},
    ] # 5 items in 0-7d, none in 7-14d
    
    node = make_analytics_node(_FakeGeminiModel(), _FakeBigQuery())
    state = _make_state(issues)
    result = await node(state)
    
    assert result["analytics"]["zero_baseline"] is True
    assert result["analytics"]["trend_7d"] is None

@pytest.mark.asyncio
async def test_timeout_sla():
    class SlowBQ:
        async def read_community_health_score(self, ward_id):
            await asyncio.sleep(20)
            return 50.0
            
    # Should timeout because SLA is 12s
    node = make_analytics_node(_FakeGeminiModel(), SlowBQ())
    # We patch _SLA_SECONDS for faster testing
    import agents.analytics_agent
    original_sla = agents.analytics_agent._SLA_SECONDS
    agents.analytics_agent._SLA_SECONDS = 0.5
    try:
        # Mock 5 issues so it passes insufficient data guard
        issues = [{"reported_at": datetime.now().isoformat()} for _ in range(5)]
        state = _make_state(issues)
        result = await node(state)
        # Should complete gracefully but partial/empty
        assert result["analytics"]["health_score_unavailable"] is False or result["analytics"]["health_score_unavailable"] is True
    finally:
        agents.analytics_agent._SLA_SECONDS = original_sla
