"""
agents/retry.py — Node retry wrapper for the Sampark AI LangGraph pipeline.

Per the design spec (Section 3.5):
- Max retries: 2
- Backoff: 2 seconds fixed
- On final failure: set ``execution.status = "failed"`` and return error state
"""

from __future__ import annotations

import asyncio
import copy
import logging
from typing import Awaitable, Callable

from agents.state import GraphState

logger = logging.getLogger(__name__)

MAX_RETRIES: int = 2
RETRY_BACKOFF_SECONDS: float = 2.0


def with_retry(
    node_fn: Callable[[GraphState], Awaitable[GraphState]],
    node_name: str,
) -> Callable[[GraphState], Awaitable[GraphState]]:
    """Wrap an async node function with retry-on-exception behaviour.

    On unhandled exception, the wrapper waits :data:`RETRY_BACKOFF_SECONDS`
    and retries up to :data:`MAX_RETRIES` times.  If all attempts fail,
    ``execution.status`` is set to ``"failed"`` and the (minimally mutated)
    state is returned so the graph can terminate gracefully rather than
    crashing.

    Parameters
    ----------
    node_fn:
        The async LangGraph node function to wrap.
    node_name:
        Human-readable name used in log messages (e.g. ``"analytics_node"``).

    Returns
    -------
    Callable
        A drop-in async replacement for ``node_fn`` with retry semantics.

    Example
    -------
    ::

        from agents.retry import with_retry

        @with_retry
        async def analytics_node(state: GraphState) -> GraphState:
            ...

        # or equivalently:
        analytics_node = with_retry(analytics_node, "analytics_node")
    """

    async def wrapped(state: GraphState) -> GraphState:
        session_id: str = state.get("execution", {}).get("session_id", "unknown")
        last_exc: BaseException | None = None

        for attempt in range(MAX_RETRIES + 1):  # attempts 0, 1, 2
            try:
                return await node_fn(state)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                retry_count = state.get("execution", {}).get("retry_count", 0) + 1

                # Mutate retry_count in execution metadata
                execution = dict(state.get("execution") or {})
                execution["retry_count"] = retry_count
                state = {**state, "execution": execution}  # type: ignore[misc]

                if attempt < MAX_RETRIES:
                    logger.warning(
                        "Node %s failed (attempt %d/%d) for session=%s: %s — retrying in %.0fs",
                        node_name,
                        attempt + 1,
                        MAX_RETRIES + 1,
                        session_id,
                        exc,
                        RETRY_BACKOFF_SECONDS,
                    )
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                else:
                    logger.error(
                        "Node %s exhausted all %d retries for session=%s: %s",
                        node_name,
                        MAX_RETRIES,
                        session_id,
                        exc,
                        exc_info=True,
                    )

        # All attempts failed — mark execution as failed and return
        execution = dict(state.get("execution") or {})
        execution["status"] = "failed"
        failed_state: GraphState = {**state, "execution": execution}  # type: ignore[misc]
        return failed_state

    wrapped.__name__ = node_fn.__name__
    wrapped.__qualname__ = f"retry_wrapped({node_fn.__qualname__})"
    return wrapped
