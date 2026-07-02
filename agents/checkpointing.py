"""
agents/checkpointing.py — Firestore-backed checkpoint persistence for the
Sampark AI LangGraph pipeline.

Every node transition persists a full ``GraphState`` snapshot to Firestore
under the path::

    sessions/{session_id}/checkpoints/{node_name}

On resume with an existing ``session_id``, the pipeline reads completed
checkpoints and skips already-finished nodes.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Awaitable, Callable

from agents.state import GraphState

logger = logging.getLogger(__name__)


class FirestoreCheckpointSaver:
    """Persists and retrieves ``GraphState`` checkpoints in Firestore.

    Parameters
    ----------
    db:
        An initialised ``google.cloud.firestore.AsyncClient`` instance.
        Injected rather than created internally so it can be mocked in tests.
    collection_prefix:
        Top-level Firestore collection name.  Defaults to ``"sessions"``.
    """

    def __init__(self, db: Any, collection_prefix: str = "sessions") -> None:
        self._db = db
        self._prefix = collection_prefix

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session_ref(self, session_id: str):
        return self._db.collection(self._prefix).document(session_id)

    def _checkpoint_ref(self, session_id: str, node_name: str):
        return (
            self._db.collection(self._prefix)
            .document(session_id)
            .collection("checkpoints")
            .document(node_name)
        )

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.datetime.utcnow().isoformat() + "Z"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save_checkpoint(
        self, session_id: str, node_name: str, state: GraphState
    ) -> None:
        """Persist a ``GraphState`` snapshot after a node completes.

        Writes to ``sessions/{session_id}/checkpoints/{node_name}`` and
        updates the parent session document's ``last_checkpoint`` field.

        Failures are logged but do **not** propagate — a checkpoint write
        error must never crash the pipeline.

        Parameters
        ----------
        session_id:
            Unique pipeline run identifier from ``state["execution"]["session_id"]``.
        node_name:
            Name of the node that just completed (e.g. ``"validation_node"``).
        state:
            Current ``GraphState`` to snapshot.
        """
        now = self._utcnow_iso()
        checkpoint_data = {
            "node_name": node_name,
            "state_snapshot": dict(state),
            "completed_at": now,
        }
        try:
            # Write checkpoint document
            await self._checkpoint_ref(session_id, node_name).set(checkpoint_data)
            # Update parent session metadata
            await self._session_ref(session_id).set(
                {"last_checkpoint": node_name, "updated_at": now},
                merge=True,
            )
            logger.debug(
                "Checkpoint saved: session=%s node=%s", session_id, node_name
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to save checkpoint session=%s node=%s: %s",
                session_id,
                node_name,
                exc,
                exc_info=True,
            )

    async def load_checkpoint(
        self, session_id: str, node_name: str
    ) -> GraphState | None:
        """Load a persisted ``GraphState`` snapshot for the given node.

        Parameters
        ----------
        session_id:
            Pipeline run identifier.
        node_name:
            Node whose checkpoint to retrieve.

        Returns
        -------
        GraphState or None
            Deserialised state dict, or ``None`` if no checkpoint exists.
        """
        try:
            doc = await self._checkpoint_ref(session_id, node_name).get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            return data.get("state_snapshot")  # type: ignore[return-value]
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to load checkpoint session=%s node=%s: %s",
                session_id,
                node_name,
                exc,
                exc_info=True,
            )
            return None

    async def list_completed_nodes(self, session_id: str) -> list[str]:
        """Return the names of all nodes that have saved checkpoints.

        Parameters
        ----------
        session_id:
            Pipeline run identifier.

        Returns
        -------
        list[str]
            Ordered list of node names (Firestore document IDs) for which a
            checkpoint document exists under this session.
        """
        try:
            docs = (
                self._db.collection(self._prefix)
                .document(session_id)
                .collection("checkpoints")
                .stream()
            )
            node_names: list[str] = []
            async for doc in docs:
                node_names.append(doc.id)
            return node_names
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to list checkpoints for session=%s: %s",
                session_id,
                exc,
                exc_info=True,
            )
            return []


# ---------------------------------------------------------------------------
# Checkpoint wrapper factory
# ---------------------------------------------------------------------------


def create_checkpoint_wrapper(
    saver: FirestoreCheckpointSaver,
) -> Callable[[Callable[..., Awaitable[GraphState]], str], Callable[..., Awaitable[GraphState]]]:
    """Return a decorator factory that wraps node functions with checkpointing.

    Usage::

        wrapper = create_checkpoint_wrapper(saver)
        wrapped_node = wrapper(my_node_fn, "my_node")

    The wrapper calls the original node function, then — on success — persists
    the resulting state to Firestore.  If the checkpoint write fails, the
    pipeline continues unaffected (the error is logged).

    Parameters
    ----------
    saver:
        Configured :class:`FirestoreCheckpointSaver` instance.

    Returns
    -------
    Callable
        A factory ``wrapper(node_fn, node_name)`` that produces a
        checkpoint-enabled async node function.
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
