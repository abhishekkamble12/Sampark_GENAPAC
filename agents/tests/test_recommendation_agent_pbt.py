"""Property-based tests for Recommendation Agent (Task 10)."""

import asyncio
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from agents.recommendation_agent import make_recommendation_node
from agents.tests.test_recommendation_agent import _MockRetriever, _MockGenerator, _make_state

@given(
    st.floats(min_value=0.0, max_value=1.0),
    st.floats(min_value=0.0, max_value=1.0),
    st.sampled_from(["high", "medium", "low", "unknown"]),
    st.sampled_from(["low", "valid"]),
    st.booleans()
)
@settings(max_examples=50)
def test_recommendation_pbt(flood, road, traffic, conf, no_policy):
    """Verify priority bounds and output invariants."""
    async def _run():
        node = make_recommendation_node(_MockRetriever(no_policy=no_policy), _MockGenerator())
        state = await node(_make_state(flood, road, traffic, conf))
        rec = state["recommendation"]
        
        # 10.9 Priority bounds
        assert rec["priority"] in ["Critical", "High", "Medium", "Low"]
        
        # 10.9 Cited policies is always a list
        assert isinstance(rec["cited_policies"], list)
        
        if no_policy:
            assert len(rec["cited_policies"]) == 0
            assert rec["disclaimer"] is not None
            
        if rec["priority"] in ["Critical", "High"] and conf == "low":
            assert rec["confidence_caveat"] is True
        else:
            assert rec["confidence_caveat"] is False
            
    asyncio.run(_run())
