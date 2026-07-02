"""Property-based tests for Prediction Agent (Task 8)."""

import asyncio
from datetime import datetime, timezone
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from agents.prediction_agent import make_prediction_node
from agents.state import GraphState

def _make_state(rainfall, flood_count, pothole_count) -> GraphState:
    now = datetime.now(timezone.utc)
    issues = [{"reported_at": now.isoformat(), "type": "flood"} for _ in range(flood_count)]
    issues.extend([{"reported_at": now.isoformat(), "type": "road"} for _ in range(pothole_count)])
    
    return {
        "query": "test", "user": {}, "issue": None, "validation": None,
        "context": {"weather": {"rainfall_forecast_48h": rainfall}, "historical_issues": issues},
        "analytics": {"trend_7d": 0.0}, "prediction": None, "rag_chunks": None, "recommendation": None,
        "workflow": None, "response": None, "intake_error": None,
        "translation_error": False, "extraction_error": False, "no_policy_context": False,
        "execution": {"session_id": "s", "status": "running", "retry_count": 0, "node_checkpoints": []},
    }

@given(
    st.floats(min_value=0.0, max_value=1000.0),
    st.integers(min_value=0, max_value=100),
    st.integers(min_value=0, max_value=100)
)
@settings(max_examples=50)
def test_prediction_pbt(rainfall, flood_count, pothole_count):
    """Verify bounds and explainability sum."""
    async def _run():
        node = make_prediction_node()
        state = await node(_make_state(rainfall, flood_count, pothole_count))
        pred = state["prediction"]
        
        # Bounds check
        assert 0.0 <= pred["flood_risk"] <= 1.0
        assert 0.0 <= pred["road_risk"] <= 1.0
        
        # Explainability check
        expl = pred["explainability"]
        if expl:
            total_pct = sum(e["weight_pct"] for e in expl)
            assert abs(total_pct - 100.0) < 0.001
            
    asyncio.run(_run())
