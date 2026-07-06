"""
agents/checkpointing.py — Local Checkpoint Persistence (FREE replacement for Firestore)

Every node transition persists a full GraphState snapshot to an in-memory
dictionary (and optionally SQLite for persistence across restarts).

Replaces Firestore-backed checkpointing with zero cloud dependencies.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Awaitable, Callable

from agents.state import GraphState

logger = logging.getLogger(__name__)


class LocalCheckpointSaver:
    """In-memory checkpoint saver with optional SQLite persistence.

    Replaces FirestoreCheckpointSaver. Stores checkpoints in memory
    by default, with an option to persist to SQLite.
    """

    def __init__(self, db: Any = None, collection_prefix: str = "sessions"):
        self._db = db
        self._prefix = collection_prefix
        self._checkpoints: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.datetime.utcnow().isoformat() + "Z"

    async def save_checkpoint(
        self, session_id: str, node_name: str, state: GraphState
    ) -> None:
        """Persist a GraphState snapshot after a node completes."""
        now = self._utcnow_iso()
        checkpoint_key = f"{session_id}:{node_name}"
        checkpoint_data = {
            "node_name": node_name,
            "state_snapshot": dict(state),
            "completed_at": now,
        }

        # Store in memory
        self._checkpoints[checkpoint_key] = checkpoint_data

        # Optionally persist to SQLite
        if self._db is not None:
            try:
                session_data = {
                    "checkpoints": {
                        node_name: checkpoint_data,
                    },
                    "last_checkpoint": node_name,
                    "updated_at": now,
                    "status": state.get("execution", {}).get("status", "running"),
                }

                # Merge checkpoints into existing session
                existing = await self._db.get_document(self._prefix, session_id)
                if existing:
                    existing.setdefault("checkpoints", {})[node_name] = checkpoint_data
                    existing["last_checkpoint"] = node_name
                    existing["updated_at"] = now
                    existing["status"] = state.get("execution", {}).get("status", "running")
                    await self._db.set_document(self._prefix, session_id, existing, merge=False)
                else:
                    await self._db.set_document(self._prefix, session_id, session_data)
            except Exception:
                logger.warning("Failed to persist checkpoint to SQLite (continuing)")

        logger.debug("Checkpoint saved: session=%s node=%s", session_id, node_name)

    async def load_checkpoint(
        self, session_id: str, node_name: str
    ) -> GraphState | None:
        """Load a persisted GraphState snapshot."""
        # Try memory first
        checkpoint_key = f"{session_id}:{node_name}"
        cp = self._checkpoints.get(checkpoint_key)
        if cp:
            return cp.get("state_snapshot")

        # Try SQLite
        if self._db is not None:
            try:
                session = await self._db.get_document(self._prefix, session_id)
                if session:
                    checkpoints = session.get("checkpoints", {})
                    cp = checkpoints.get(node_name)
                    if cp:
                        return cp.get("state_snapshot")
            except Exception:
                pass

        return None

    async def list_completed_nodes(self, session_id: str) -> list[str]:
        """Return all completed node names for a session."""
        # From memory
        node_names = [
            cp["node_name"]
            for key, cp in self._checkpoints.items()
            if key.startswith(f"{session_id}:")
        ]

        # From SQLite (add any not already in memory)
        if self._db is not None:
            try:
                session = await self._db.get_document(self._prefix, session_id)
                if session:
                    checkpoints = session.get("checkpoints", {})
                    stored_nodes = list(checkpoints.keys())
                    for node in stored_nodes:
                        if node not in node_names:
                            node_names.append(node)
            except Exception:
                pass

        return node_names


# ---------------------------------------------------------------------------
# Checkpoint wrapper factory
# ---------------------------------------------------------------------------


def create_checkpoint_wrapper(
    saver: LocalCheckpointSaver,
) -> Callable[
    [Callable[..., Awaitable[GraphState]], str],
    Callable[..., Awaitable[GraphState]],
]:
    """Return a decorator factory that wraps node functions with checkpointing.

    Usage:
        wrapper = create_checkpoint_wrapper(saver)
        wrapped_node = wrapper(my_node_fn, "my_node")
    """

    def wrapper(
        node_fn: Callable[[GraphState], Awaitable[GraphState]],
        node_name: str,
    ) -> Callable[[GraphState], Awaitable[GraphState]]:
        async def checkpointed_node(state: GraphState) -> GraphState:
            result = await node_fn(state)
            session_id: str = result.get("execution", {}).get("session_id", "unknown")
            await saver.save_checkpoint(session_id, node_name, result)
            return result

        checkpointed_node.__name__ = node_fn.__name__
        checkpointed_node.__qualname__ = node_fn.__qualname__
        return checkpointed_node

    return wrapper
