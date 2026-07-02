"""Unit tests for Workflow Agent (Task 11)."""

import asyncio
import pytest
from datetime import datetime, timezone
from agents.workflow_agent import make_workflow_node
from agents.state import GraphState

class _MockFirestore:
    def __init__(self, fail_first=False, fail_always=False):
        self.fail_first = fail_first
        self.fail_always = fail_always
        self.attempts = 0
        self.docs = {}
    async def set_document(self, col, doc_id, data):
        self.attempts += 1
        if self.fail_always or (self.fail_first and self.attempts == 1):
            raise Exception("Firestore error")
        self.docs[doc_id] = data
        
class _MockPubSub:
    def __init__(self, fail=False):
        self.fail = fail
        self.published = []
    async def publish(self, topic, payload):
        if self.fail:
            raise Exception("PubSub down")
        self.published.append((topic, payload))

def _make_state(issue_type="road", priority="High") -> GraphState:
    return {
        "issue": {"id": "123", "type": issue_type},
        "recommendation": {"priority": priority},
        "workflow": None, "response": None,
        "query": "test", "user": {}, "validation": None, "context": None,
        "analytics": None, "prediction": None, "rag_chunks": None,
        "intake_error": None, "translation_error": False, "extraction_error": False, "no_policy_context": False,
        "execution": {"session_id": "s", "status": "running", "retry_count": 0, "node_checkpoints": []},
    }

@pytest.mark.asyncio
async def test_routing_fallback():
    node = make_workflow_node(_MockFirestore(), _MockPubSub())
    # known type
    res1 = await node(_make_state(issue_type="road"))
    assert res1["workflow"]["assigned_department"] == "Public Works Department"
    assert res1["workflow"]["routing_fallback"] is False
    
    # unknown type
    res2 = await node(_make_state(issue_type="alien_invasion"))
    assert res2["workflow"]["assigned_department"] == "Admin Review"
    assert res2["workflow"]["routing_fallback"] is True

@pytest.mark.asyncio
async def test_due_date_calculation():
    node = make_workflow_node(_MockFirestore(), _MockPubSub())
    
    res_crit = await node(_make_state(priority="Critical"))
    due_c = datetime.fromisoformat(res_crit["workflow"]["due_date"])
    diff_c = due_c - datetime.now(timezone.utc)
    assert 23 < (diff_c.total_seconds() / 3600) <= 24
    
    res_high = await node(_make_state(priority="High"))
    due_h = datetime.fromisoformat(res_high["workflow"]["due_date"])
    diff_h = due_h - datetime.now(timezone.utc)
    assert 71 < (diff_h.total_seconds() / 3600) <= 72
    
    res_low = await node(_make_state(priority="Low"))
    due_l = datetime.fromisoformat(res_low["workflow"]["due_date"])
    diff_l = due_l - datetime.now(timezone.utc)
    assert 6 < (diff_l.total_seconds() / (3600*24)) <= 7

@pytest.mark.asyncio
async def test_firestore_retry():
    # To avoid tests taking 2s, we mock the asyncio.sleep in the agent module
    import agents.workflow_agent
    orig_sleep = agents.workflow_agent.asyncio.sleep
    agents.workflow_agent.asyncio.sleep = lambda x: asyncio.sleep(0.001)
    
    try:
        # First attempt fails, second succeeds
        fs = _MockFirestore(fail_first=True)
        node = make_workflow_node(fs, _MockPubSub())
        res = await node(_make_state())
        assert res["workflow"]["workflow_error"] is False
        assert fs.attempts == 2
        assert len(fs.docs) == 1
        
        # Double failure
        fs2 = _MockFirestore(fail_always=True)
        pubsub = _MockPubSub()
        node2 = make_workflow_node(fs2, pubsub)
        res2 = await node2(_make_state())
        assert res2["workflow"]["workflow_error"] is True
        assert fs2.attempts == 2
        assert len(pubsub.published) == 0 # Pubsub skipped
    finally:
        agents.workflow_agent.asyncio.sleep = orig_sleep

@pytest.mark.asyncio
async def test_pubsub_failure_logging():
    fs = _MockFirestore()
    pubsub = _MockPubSub(fail=True)
    node = make_workflow_node(fs, pubsub)
    
    res = await node(_make_state())
    # Workflow shouldn't crash or error out if ONLY pubsub fails
    assert res["workflow"]["workflow_error"] is False
    assert len(fs.docs) == 1
