"""
agents/resume.py — Resume-from-checkpoint logic for the Sampark AI pipeline.

When a new execution arrives with an existing ``session_id``, the pipeline
loads the last completed checkpoint from Firestore and restores the
``GraphState`` from that point, skipping all previously completed nodes.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.checkpointing import FirestoreCheckpointSaver
from agents.state import GraphState

logger = logging.getLogger(__name__)

# Ordered list of all pipeline nodes — used to determine which nodes come
# after the last completed checkpoint so we can skip earlier ones.
PIPELINE_NODE_ORDER: list[str] = [
    "intake_node",
    "validation_node",
    "data_intelligence_node",
    "analytics_node",
    "prediction_node",
    "recommendation_node",
    "workflow_node",
    "notification_dispatch_node",
    "response_node",
]


async def try_resume(
    session_id: str,
    saver: FirestoreCheckpointSaver,
) -> tuple[GraphState | None, str | None]:
    """Attempt to restore pipeline state from the most recent checkpoint.

    Reads all completed checkpoint documents for ``session_id`` from
    Firestore, determines the furthest completed node in
    ``PIPELINE_NODE_ORDER``, and loads that node's ``GraphState`` snapshot.

    Parameters
    ----------
    session_id:
        The pipeline run identifier to look up.
    saver:
        Configured :class:`~agents.checkpointing.FirestoreCheckpointSaver`.

    Returns
    -------
    tuple[GraphState | None, str | None]
        A ``(state, resume_node)`` pair where:

        * ``state`` is the restored ``GraphState`` at the last checkpoint, or
          ``None`` if no checkpoint exists.
        * ``resume_node`` is the name of the *next* node to execute (the one
          immediately after the last completed checkpoint), or ``None`` if the
          pipeline is complete or no checkpoint was found.
    """
    completed_nodes = await saver.list_completed_nodes(session_id)
    if not completed_nodes:
        logger.debug("No checkpoints found for session=%s — starting fresh", session_id)
        return None, None

    # Find the furthest completed node in pipeline order
    last_completed_index = -1
    last_completed_name: str | None = None
    for node in completed_nodes:
        try:
            idx = PIPELINE_NODE_ORDER.index(node)
            if idx > last_completed_index:
                last_completed_index = idx
                last_completed_name = node
        except ValueError:
            # Node not in ordered list (e.g. error_response_node) — skip
            pass

    if last_completed_name is None:
        logger.debug(
            "Completed nodes %s not in pipeline order for session=%s",
            completed_nodes,
            session_id,
        )
        return None, None

    # Load the state snapshot from the last completed checkpoint
    state = await saver.load_checkpoint(session_id, last_completed_name)
    if state is None:
        logger.warning(
            "Checkpoint document missing for session=%s node=%s despite being listed",
            session_id,
            last_completed_name,
        )
        return None, None

    # Determine the next node to run
    next_index = last_completed_index + 1
    if next_index >= len(PIPELINE_NODE_ORDER):
        # Pipeline was already complete
        logger.info("Session %s is already complete — no resume needed", session_id)
        return state, None

    resume_node = PIPELINE_NODE_ORDER[next_index]
    logger.info(
        "Resuming session=%s from node=%s (last completed=%s)",
        session_id,
        resume_node,
        last_completed_name,
    )
    return state, resume_node


async def build_initial_state(
    query: str,
    user: dict[str, Any],
    session_id: str,
    saver: FirestoreCheckpointSaver | None = None,
) -> tuple[GraphState, str | None]:
    """Build the starting ``GraphState`` for a pipeline invocation.

    If ``saver`` is provided and a prior checkpoint exists for
    ``session_id``, the restored state and resume node are returned.
    Otherwise a fresh ``GraphState`` is returned with ``resume_node=None``
    (meaning the graph starts from ``START``).

    Parameters
    ----------
    query:
        Raw citizen input string.
    user:
        Decoded JWT user dict ``{user_id, role, ward_ids, preferred_channel}``.
    session_id:
        Unique run identifier.
    saver:
        Optional checkpoint saver.  Pass ``None`` to always start fresh
        (useful in unit tests).

    Returns
    -------
    tuple[GraphState, str | None]
        ``(state, resume_node)`` — if ``resume_node`` is not ``None`` the
        caller should invoke the graph starting at that node rather than
        ``START``.
    """
    if saver is not None:
        restored_state, resume_node = await try_resume(session_id, saver)
        if restored_state is not None:
            return restored_state, resume_node

    fresh_state: GraphState = {
        "query": query,
        "user": user,
        "issue": None,
        "validation": None,
        "context": None,
        "analytics": None,
        "prediction": None,
        "rag_chunks": None,
        "recommendation": None,
        "workflow": None,
        "response": None,
        "intake_error": None,
        "translation_error": False,
        "extraction_error": False,
        "no_policy_context": False,
        "execution": {
            "session_id": session_id,
            "status": "running",
            "retry_count": 0,
            "node_checkpoints": [],
        },
    }
    return fresh_state, None
