"""
agents/notification_agent.py — Notification Agent for the Sampark AI Platform.

Handles Pub/Sub subscriptions and Firestore listeners to dispatch lifecycle
event notifications using a robust multi-channel fallback chain.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_SLA_SECONDS = 60.0
_RETRY_DELAY = 30.0

class NotificationProvider:
    """Abstract interface for mock delivery providers."""
    async def send(self, target: str, message: str) -> bool:
        raise NotImplementedError

class NotificationAgent:
    def __init__(self, firestore_client: Any, providers: dict[str, NotificationProvider]):
        """
        providers expected keys: 'whatsapp', 'email', 'sms'
        """
        self.firestore = firestore_client
        self.providers = providers

    # 12.1 Pub/Sub entrypoint
    async def handle_pubsub_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if event_type == "task-created":
            await self._dispatch_with_sla(payload, "Issue Received")
        elif event_type == "task-escalated":
            await self._dispatch_with_sla(payload, "Escalated")

    # 12.2 Firestore onSnapshot entrypoint
    async def handle_firestore_snapshot(self, task_id: str, new_status: str, task_data: dict[str, Any]) -> None:
        if new_status == "in_progress":
            await self._dispatch_with_sla(task_data, "Engineer Assigned")
        elif new_status == "resolved":
            await self._dispatch_with_sla(task_data, "Resolved")

    async def _dispatch_with_sla(self, payload: dict[str, Any], event_name: str) -> None:
        """12.8 Enforce 60-second dispatch SLA."""
        try:
            async with asyncio.timeout(_SLA_SECONDS):
                await self._process_lifecycle_event(payload, event_name)
        except (TimeoutError, asyncio.TimeoutError):
            logger.error("Notification SLA timeout exceeded for event %s", event_name)
        except Exception:
            logger.exception("Notification dispatch failed for event %s", event_name)

    async def _process_lifecycle_event(self, payload: dict[str, Any], event_name: str) -> None:
        """12.4 Setup routing targets and channels for lifecycle events."""
        target = ""
        preferred_channel = "email"
        message = f"[{event_name}] Update regarding your issue."

        # 12.6 Escalation targets Government Officer
        if event_name == "Escalated":
            dept = payload.get("department")
            officer = None
            if dept:
                try:
                    officer = await self.firestore.get_assigned_officer(dept)
                except Exception:
                    pass
            target = officer.get("email") if officer else "admin-review@sampark.local"
            preferred_channel = "email"
            message = f"[ESCALATED] Task {payload.get('task_id')} priority bumped to {payload.get('new_priority')}"
        else:
            user_id = payload.get("user_id")
            if user_id:
                try:
                    profile = await self.firestore.get_user_profile(user_id)
                    preferred_channel = profile.get("preferred_channel", "email").lower()
                    target = profile.get("contact", "")
                except Exception:
                    preferred_channel = "email"
                    target = "unknown@sampark.local"

        await self._run_fallback_chain(target, preferred_channel, message, payload.get("task_id", "unknown"))

    async def _run_fallback_chain(self, target: str, initial_channel: str, message: str, task_id: str) -> None:
        """12.5 Implement fallback chain with 1 retry per channel."""
        chain = []
        if initial_channel in ("whatsapp", "fcm"):
            chain = ["whatsapp", "email", "sms"]
        elif initial_channel == "email":
            chain = ["email", "sms"]
        elif initial_channel == "sms":
            chain = ["sms"]
        else:
            chain = ["email", "sms"]

        for channel in chain:
            provider = self.providers.get(channel)
            if not provider:
                continue

            # First attempt
            success, reason = await self._attempt_send(provider, channel, target, message, task_id, attempt=1)
            if success:
                return

            # Retry attempt
            await asyncio.sleep(_RETRY_DELAY)
            success, reason = await self._attempt_send(provider, channel, target, message, task_id, attempt=2)
            if success:
                return

        logger.error("All fallback channels exhausted for task %s", task_id)

    async def _attempt_send(self, provider: NotificationProvider, channel: str, target: str, msg: str, task_id: str, attempt: int) -> tuple[bool, str]:
        """Send and 12.7 log the attempt to Firestore."""
        success = False
        reason = ""
        try:
            success = await provider.send(target, msg)
            if not success:
                reason = "Provider rejected"
        except Exception as e:
            reason = str(e)
            
        now_iso = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "task_id": task_id,
            "channel": channel,
            "target": target,
            "status": "success" if success else "failed",
            "attempt_count": attempt,
            "failure_reason": reason,
            "timestamp": now_iso
        }
        
        try:
            # 12.7 Log all attempts
            await self.firestore.log_notification(log_entry)
        except Exception:
            logger.error("Failed to log notification attempt to Firestore")
            
        return success, reason
