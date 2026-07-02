"""Unit tests for the Recommendation Agent (Task 10)."""

import asyncio
import pytest
from agents.recommendation_agent import make_recommendation_node
from agents.state import GraphState

class _MockRetriever:
    def __init__(self, chunks=None, no_policy=False):
        self.chunks = chunks or []
        self.no_policy = no_policy
    async def retrieve(self, query):
        return self.chunks, self.no_policy

class _MockGenerator:
    def __init__(self, fail=False):
        self.fail = fail
    async def generate_recommendation(self, query, chunks):
        if self.fail:
            raise RuntimeError("Gemini error")
        return {
            "action": "Do this",
            "rationale": "Because",
            "cited_policies": [c["doc_name"] for c in chunks] if chunks else []
        }

def _make_state(flood, road, traffic, conf, no_policy=False) -> GraphState:
    return {
        "query": "test", "user": {}, 
        "issue": {"type": "pothole", "location": {"ward_id": "w1"}},
        "validation": {"status": "low_confidence" if conf == "low" else "valid"},
        "context": {"traffic": {"traffic_density": traffic}},
        "analytics": {},
        "prediction": {"flood_risk": flood, "road_risk": road},
        "no_policy_context": no_policy,
        "recommendation": None, "rag_chunks": None, "workflow": None, "response": None,
        "intake_error": None, "translation_error": False, "extraction_error": False,
        "execution": {"session_id": "s1", "status": "running", "retry_count": 0, "node_checkpoints": []},
    }

@pytest.mark.asyncio
async def test_priority_matrix():
    node = make_recommendation_node(_MockRetriever(), _MockGenerator())
    
    # Critical
    res = await node(_make_state(0.8, 0.8, "high", "valid"))
    assert res["recommendation"]["priority"] == "Critical"
    
    # High (one risk)
    res = await node(_make_state(0.8, 0.1, "low", "valid"))
    assert res["recommendation"]["priority"] == "High"
    
    # High (traffic)
    res = await node(_make_state(0.1, 0.1, "high", "valid"))
    assert res["recommendation"]["priority"] == "High"
    
    # Medium
    res = await node(_make_state(0.1, 0.1, "medium", "valid"))
    assert res["recommendation"]["priority"] == "Medium"
    
    # Low
    res = await node(_make_state(0.1, 0.1, "low", "valid"))
    assert res["recommendation"]["priority"] == "Low"

@pytest.mark.asyncio
async def test_caveat_and_disclaimer():
    node = make_recommendation_node(_MockRetriever(no_policy=True), _MockGenerator())
    
    # High priority + low confidence -> caveat True
    res = await node(_make_state(0.8, 0.1, "low", "low"))
    rec = res["recommendation"]
    
    assert rec["confidence_caveat"] is True
    assert rec["disclaimer"] is not None
    assert "No relevant municipal policy" in rec["disclaimer"]
    
    # Medium priority + low confidence -> caveat False
    res2 = await node(_make_state(0.1, 0.1, "medium", "low"))
    assert res2["recommendation"]["confidence_caveat"] is False

@pytest.mark.asyncio
async def test_timeout_sla():
    class SlowRetriever:
        async def retrieve(self, q):
            await asyncio.sleep(2)
            return [], True
            
    node = make_recommendation_node(SlowRetriever(), _MockGenerator())
    
    import agents.recommendation_agent
    original = agents.recommendation_agent._SLA_SECONDS
    agents.recommendation_agent._SLA_SECONDS = 0.1
    try:
        res = await node(_make_state(0.1, 0.1, "low", "valid"))
        assert res["recommendation"]["error"] == "timeout"
    finally:
        agents.recommendation_agent._SLA_SECONDS = original
