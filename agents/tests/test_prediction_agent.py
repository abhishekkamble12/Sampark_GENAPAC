"""Unit tests for the Prediction Agent (Task 8)."""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from agents.prediction_agent import make_prediction_node
from agents.state import GraphState

def _make_state(weather=None, analytics=None, issues=None) -> GraphState:
    ctx_weather = weather if weather is not None else {"rainfall_forecast_48h": 10.0}
    ctx_analytics = analytics if analytics is not None else {"trend_7d": 5.0}
    
    return {
        "query": "test", "user": {}, "issue": None,
        "validation": None, 
        "context": {"weather": ctx_weather, "historical_issues": issues or []}, 
        "analytics": ctx_analytics,
        "prediction": None, "rag_chunks": None, "recommendation": None,
        "workflow": None, "response": None, "intake_error": None,
        "translation_error": False, "extraction_error": False,
        "no_policy_context": False,
        "execution": {"session_id": "s1", "status": "running", "retry_count": 0, "node_checkpoints": []},
    }

@pytest.mark.asyncio
async def test_insufficient_context_guard():
    node = make_prediction_node()
    state = _make_state(weather=None)  # missing weather
    result = await node(state)
    assert result["prediction"]["error"] == "insufficient_context"
    
    state2 = _make_state(analytics=False) # missing analytics
    result2 = await node(state2)
    assert result2["prediction"]["error"] == "insufficient_context"

@pytest.mark.asyncio
async def test_normal_prediction():
    node = make_prediction_node()
    now = datetime.now(timezone.utc)
    issues = [
        {"reported_at": now.isoformat(), "type": "flood"},
        {"reported_at": now.isoformat(), "type": "road"},
    ]
    state = _make_state(issues=issues)
    result = await node(state)
    
    pred = result["prediction"]
    assert pred["error"] is None
    assert 0.0 <= pred["flood_risk"] <= 1.0
    assert 0.0 <= pred["road_risk"] <= 1.0
    
    # Check SHAP explainability sums to 100
    expl = pred["explainability"]
    assert len(expl) <= 3
    assert abs(sum(e["weight_pct"] for e in expl) - 100.0) < 0.01
    
    # Check ARIMA mock
    assert len(pred["volume_forecast"]) == 7

@pytest.mark.asyncio
async def test_high_risk_alert():
    node = make_prediction_node()
    # Mock extreme weather
    state = _make_state(weather={"rainfall_forecast_48h": 500.0}) 
    result = await node(state)
    assert result["prediction"]["flood_risk"] > 0.75
    assert result["prediction"]["high_risk_alert"] is True

@pytest.mark.asyncio
async def test_timeout_sla():
    node = make_prediction_node()
    import agents.prediction_agent
    original_sla = agents.prediction_agent._SLA_SECONDS
    agents.prediction_agent._SLA_SECONDS = 0.0001
    try:
        # Give it a lot of fake data to slow it down
        issues = [{"reported_at": datetime.now().isoformat(), "type": "flood"} for _ in range(50000)]
        state = _make_state(issues=issues)
        result = await node(state)
        # Assuming parsing 50k takes > 0.1ms
        assert result["prediction"]["error"] == "timeout" or result["prediction"]["error"] == "internal_error"
    finally:
         agents.prediction_agent._SLA_SECONDS = original_sla
