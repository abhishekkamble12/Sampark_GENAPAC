"""Unit tests for the Notification Agent (Task 12)."""

import asyncio
import pytest
from agents.notification_agent import NotificationAgent, NotificationProvider

class _MockFirestore:
    def __init__(self):
        self.logs = []
    async def get_user_profile(self, user_id):
        return {"preferred_channel": "whatsapp", "contact": "12345"}
    async def get_assigned_officer(self, dept):
        return {"email": "officer@sampark.local"}
    async def log_notification(self, log_entry):
        self.logs.append(log_entry)

class _MockProvider(NotificationProvider):
    def __init__(self, name, fail_count=0):
        self.name = name
        self.fail_count = fail_count
        self.attempts = 0
    async def send(self, target, msg):
        self.attempts += 1
        if self.attempts <= self.fail_count:
            return False
        return True

@pytest.mark.asyncio
async def test_fallback_chain_whatsapp_to_email():
    fs = _MockFirestore()
    # whatsapp fails 3 times (exhausting its 2 tries), email succeeds on first try
    providers = {
        "whatsapp": _MockProvider("whatsapp", fail_count=3),
        "email": _MockProvider("email", fail_count=0),
        "sms": _MockProvider("sms", fail_count=0)
    }
    agent = NotificationAgent(fs, providers)
    
    # speed up sleep
    import agents.notification_agent
    orig_sleep = agents.notification_agent.asyncio.sleep
    agents.notification_agent.asyncio.sleep = lambda x: asyncio.sleep(0.001)
    
    try:
        await agent.handle_pubsub_event("task-created", {"user_id": "u1", "task_id": "t1"})
        
        assert providers["whatsapp"].attempts == 2
        assert providers["email"].attempts == 1
        assert providers["sms"].attempts == 0
        
        assert len(fs.logs) == 3
        assert fs.logs[0]["channel"] == "whatsapp" and fs.logs[0]["status"] == "failed"
        assert fs.logs[1]["channel"] == "whatsapp" and fs.logs[1]["status"] == "failed"
        assert fs.logs[2]["channel"] == "email" and fs.logs[2]["status"] == "success"
    finally:
        agents.notification_agent.asyncio.sleep = orig_sleep

@pytest.mark.asyncio
async def test_escalation_routing():
    fs = _MockFirestore()
    providers = {"email": _MockProvider("email", fail_count=0)}
    agent = NotificationAgent(fs, providers)
    
    await agent.handle_pubsub_event("task-escalated", {"task_id": "t1", "department": "Public Works"})
    
    assert providers["email"].attempts == 1
    assert len(fs.logs) == 1
    assert fs.logs[0]["target"] == "officer@sampark.local"
