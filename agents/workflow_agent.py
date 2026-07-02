"""
agents/workflow_agent.py — Workflow Agent for the Sampark AI Platform.

Handles departmental routing, SLA due date calculations, task creation in Firestore,
and event dispatch via Pub/Sub.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Coroutine, Dict

from agents.state import GraphState, WorkflowResult

logger = logging.getLogger(__name__)

ROUTING_TABLE = {
    "pothole": "Public Works",
    "flood": "Water Management",
    "garbage": "Sanitation",
}

def make_workflow_node(
    firestore_client: Any,
    pubsub_client: Any
) -> Callable[[GraphState], Coroutine[Any, Any, GraphState]]:
    """Return an async workflow_node function."""

    async def workflow_node(state: GraphState) -> GraphState:
        result: WorkflowResult = {
            "task_id": None,
            "assigned_department": None,
            "due_date": None,
            "routing_fallback": False,
            "workflow_error": False,
        }

        issue = state.get("issue") or {}
        issue_id = issue.get("id")
        issue_type = issue.get("type", "unknown").lower()
        
        recommendation = state.get("recommendation") or {}
        priority = recommendation.get("priority", "Low")
        
        # 11.2 Routing lookup
        dept = ROUTING_TABLE.get(issue_type)
        if not dept:
            dept = "Admin Review"
            result["routing_fallback"] = True
            
        result["assigned_department"] = dept
        
        # 11.4 SLA Due Date
        now = datetime.now(timezone.utc)
        if priority == "Critical":
            due = now + timedelta(hours=24)
        elif priority == "High":
            due = now + timedelta(hours=72)
        else:
            due = now + timedelta(days=7)
            
        result["due_date"] = due.isoformat()
        
        task_id = f"task_{issue_id}" if issue_id else f"task_{int(now.timestamp())}"
        result["task_id"] = task_id
        
        task_doc = {
            "issue_id": issue_id,
            "assigned_department": dept,
            "priority": priority,
            "due_date": result["due_date"],
            "status": "open",
            "created_at": now.isoformat(),
        }
        
        # 11.3 & 11.6 Firestore Creation & Retry (1 retry after 2s)
        fs_success = False
        try:
            await firestore_client.create_document("tasks", task_id, task_doc)
            fs_success = True
        except Exception:
            logger.warning("Firestore initial write failed. Retrying in 2 seconds...")
            await asyncio.sleep(2.0)
            try:
                await firestore_client.create_document("tasks", task_id, task_doc)
                fs_success = True
            except Exception:
                logger.exception("Firestore retry failed for task %s", task_id)
                result["workflow_error"] = True
                
        if not fs_success:
            state["workflow"] = result
            return state
            
        # 11.5 Pub/Sub Dispatch
        event_payload = {
            "task_id": task_id,
            "issue_id": issue_id,
            "priority": priority,
            "department": dept
        }
        try:
            await pubsub_client.publish("task-created", event_payload)
        except Exception:
            # 11.7 Log failure for manual replay
            logger.error(
                "PubSub publish failed for topic=task-created task_id=%s issue_id=%s",
                task_id, issue_id
            )
            # We don't set workflow_error=True here per tasks.md (only double FS failure does that)
            # The task exists in Firestore, just notification failed.

        state["workflow"] = result
        return state

    return workflow_node
