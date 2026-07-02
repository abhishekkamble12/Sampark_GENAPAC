"""
functions/escalation.py — Task Escalation Cloud Function script.

Queries overdue open tasks in Firestore, bumps their priority,
and fires Pub/Sub escalation events.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

async def escalate_overdue_tasks(firestore_client, pubsub_client):
    """
    11.8 Escalate overdue open tasks.
    Run this periodically via Cloud Scheduler.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    # In reality, this would be a compounded query in Firestore:
    # collection("tasks").where("status", "==", "open").where("due_date", "<", now_iso)
    try:
        overdue_tasks = await firestore_client.query_overdue_open_tasks(now_iso)
    except Exception:
        logger.exception("Failed to query overdue tasks")
        return
        
    for task in overdue_tasks:
        task_id = task.get("id")
        current_priority = task.get("priority", "Low")
        
        new_priority = current_priority
        if current_priority == "Low":
            new_priority = "Medium"
        elif current_priority == "Medium":
            new_priority = "High"
        elif current_priority == "High":
            new_priority = "Critical"
            
        # If it's already critical, we just re-publish to annoy them every 24h
        # (Assuming the query fetched it because 24h passed since last due_date bump)
        
        # We bump the due_date to 24h from now so it doesn't trigger every minute
        from datetime import timedelta
        new_due_date = (now + timedelta(hours=24)).isoformat()
        
        updates = {
            "priority": new_priority,
            "due_date": new_due_date,
            "escalated_at": now_iso
        }
        
        try:
            await firestore_client.update_document("tasks", task_id, updates)
            
            # Publish event
            payload = {
                "task_id": task_id,
                "issue_id": task.get("issue_id"),
                "old_priority": current_priority,
                "new_priority": new_priority
            }
            await pubsub_client.publish("task-escalated", payload)
            logger.info("Escalated task %s from %s to %s", task_id, current_priority, new_priority)
        except Exception:
            logger.exception("Failed to process escalation for task %s", task_id)
