"""Property-based tests for Workflow Agent."""

import asyncio
from datetime import datetime, timezone
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from agents.workflow_agent import make_workflow_node
from agents.tests.test_workflow_agent import _MockFirestore, _MockPubSub, _make_state

@given(
    st.sampled_from(["Critical", "High", "Medium", "Low"]),
    st.sampled_from(["pothole", "flood", "garbage", "unknown"])
)
@settings(max_examples=50)
def test_workflow_due_date_future_pbt(priority, issue_type):
    """11.10 due_date is always in the future for any priority."""
    async def _run():
        node = make_workflow_node(_MockFirestore(), _MockPubSub())
        start_time = datetime.now(timezone.utc)
        
        state = await node(_make_state(issue_type=issue_type, priority=priority))
        wf = state["workflow"]
        
        assert wf["due_date"] is not None
        due = datetime.fromisoformat(wf["due_date"])
        
        # Must be explicitly in the future
        assert due > start_time
        
    asyncio.run(_run())
