"""Property-based tests for Notification Agent (Task 12)."""

import asyncio
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from agents.notification_agent import NotificationAgent, NotificationProvider
from agents.tests.test_notification_agent import _MockFirestore

class _ChaosProvider(NotificationProvider):
    def __init__(self, will_fail):
        self.will_fail = will_fail
    async def send(self, target, msg):
        if self.will_fail:
            raise RuntimeError("Chaos!")
        return True

@given(
    st.sampled_from(["task-created", "task-escalated"]),
    st.booleans(),
    st.booleans(),
    st.booleans()
)
@settings(max_examples=50)
def test_notification_log_invariants(event_type, wa_fail, em_fail, sms_fail):
    """12.10 For any notification event, at least one delivery attempt is ALWAYS logged."""
    
    async def _run():
        fs = _MockFirestore()
        providers = {
            "whatsapp": _ChaosProvider(wa_fail),
            "email": _ChaosProvider(em_fail),
            "sms": _ChaosProvider(sms_fail)
        }
        
        agent = NotificationAgent(fs, providers)
        
        import agents.notification_agent
        orig_sleep = agents.notification_agent.asyncio.sleep
        agents.notification_agent.asyncio.sleep = lambda x: asyncio.sleep(0.001)
        
        try:
            await agent.handle_pubsub_event(event_type, {"user_id": "u1", "task_id": "t1"})
            
            # The invariant: even if everything fails, we must have at least one log entry
            # unless the very first provider throws an unhandled error BEFORE logging, 
            # which our code handles.
            assert len(fs.logs) >= 1
            
        finally:
            agents.notification_agent.asyncio.sleep = orig_sleep
            
    asyncio.run(_run())
