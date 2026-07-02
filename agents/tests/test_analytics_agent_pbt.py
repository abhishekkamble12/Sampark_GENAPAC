"""Property-based tests for Analytics Agent."""

import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from agents.analytics_agent import make_analytics_node
from agents.state import GraphState

def _make_state(issues) -> GraphState:
    return {
        "query": "test", "user": {}, "issue": {"location": {"ward_id": "w1"}},
        "validation": {},
        "context": {"historical_issues": issues},
        "analytics": None, "prediction": None, "rag_chunks": None, "recommendation": None,
        "workflow": None, "response": None, "intake_error": None,
        "translation_error": False, "extraction_error": False, "no_policy_context": False,
        "execution": {"session_id": "s1", "status": "running", "retry_count": 0, "node_checkpoints": []},
    }

class _FakeGeminiModel:
    def __init__(self, score):
        self.score = score
    def generate_content(self, prompt: str):
        import json
        return type('obj', (object,), {'text': json.dumps({"sentiment_score": self.score})})()

class _FakeBigQuery:
    async def read_community_health_score(self, ward_id):
        return 80.0

@given(
    st.lists(
        st.integers(min_value=0, max_value=80), 
        min_size=5, max_size=50
    ),
    st.floats(min_value=-1.0, max_value=1.0)
)
@settings(max_examples=50)
def test_analytics_pbt_bounds(days_ago_list, sentiment):
    """PBT verifying bounds for sentiment and finite trends."""
    now = datetime.now(timezone.utc)
    issues = [
        {
            "reported_at": (now - timedelta(days=d)).isoformat(),
            "description": "test",
            "location": {"lat": 18.5, "lng": 73.8}
        }
        for d in days_ago_list
    ]
    
    async def _run():
        node = make_analytics_node(_FakeGeminiModel(sentiment), _FakeBigQuery())
        state = await node(_make_state(issues))
        analytics = state["analytics"]
        
        assert analytics is not None
        assert not analytics["insufficient_data"]
        
        # sentiment
        if analytics["sentiment_score"] is not None:
            assert -1.0 <= analytics["sentiment_score"] <= 1.0
            
        # trends
        if not analytics["zero_baseline"]:
            assert analytics["trend_7d"] is not None
            assert analytics["trend_30d"] is not None
            import math
            assert math.isfinite(analytics["trend_7d"])
            assert math.isfinite(analytics["trend_30d"])
            
    asyncio.run(_run())
