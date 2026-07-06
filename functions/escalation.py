"""
functions/escalation.py — Task Escalation (FREE Stack)

Queries overdue open tasks from SQLite, bumps their priority,
and fires escalation events via the local event queue.

Replaces Firestore + Pub/Sub with SQLite + in-memory async queue.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


async def escalate_overdue_tasks(firestore_client, pubsub_client):
    """Escalate overdue open tasks.

    Run this periodically via a background asyncio task.
    Replaces Cloud Scheduler + Pub/Sub with local processing.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    try:
        overdue_tasks = await firestore_client.query_overdue_open_tasks(now_iso)
    except Exception:
        logger.exception("Failed to query overdue tasks")
        return

    for task in overdue_tasks:
        task_id = task.get("id")
        if not task_id:
            continue

        current_priority = task.get("priority", "Low")

        new_priority = current_priority
        if current_priority == "Low":
            new_priority = "Medium"
        elif current_priority == "Medium":
            new_priority = "High"
        elif current_priority == "High":
            new_priority = "Critical"

        new_due_date = (now + timedelta(hours=24)).isoformat()

        updates = {
            "priority": new_priority,
            "due_date": new_due_date,
            "escalated_at": now_iso,
        }

        try:
            await firestore_client.update_document("tasks", task_id, updates)

            # Publish event via local event queue (replaces Pub/Sub)
            payload = {
                "task_id": task_id,
                "issue_id": task.get("issue_id"),
                "old_priority": current_priority,
                "new_priority": new_priority,
            }
            await pubsub_client.publish("task-escalated", payload)
            logger.info("Escalated task %s from %s to %s", task_id, current_priority, new_priority)
        except Exception:
            logger.exception("Failed to process escalation for task %s", task_id)
