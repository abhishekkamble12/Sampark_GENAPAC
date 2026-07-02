"""
agents/data_intelligence_agent.py — Data Intelligence Agent.

Gathers raw context from BigQuery, Weather, and Maps concurrently using
asyncio.gather with per-source 5s timeouts and a 10s total SLA.

Design: make_data_intelligence_node(bigquery_tool, weather_tool, maps_tool)
factory pattern for testability.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

from agents.state import GraphState

logger = logging.getLogger(__name__)

_SOURCE_TIMEOUT = 5.0
_TOTAL_SLA = 10.0


def make_data_intelligence_node(
    bigquery_tool: Any,
    weather_tool: Any,
    maps_tool: Any,
) -> Callable[[GraphState], Coroutine[Any, Any, GraphState]]:
    """Return an async data_intelligence_node with injected dependencies."""

    async def _fetch_bigquery(issue) -> list[dict] | None:
        try:
            async with asyncio.timeout(_SOURCE_TIMEOUT):
                ward_id = (issue.get("location") or {}).get("ward_id", "")
                return await bigquery_tool.query_historical_issues(
                    ward_id=ward_id,
                    issue_type=issue.get("type", "other"),
                    days=90,
                )
        except (TimeoutError, asyncio.TimeoutError):
            logger.warning("BigQuery source timed out after %ds", _SOURCE_TIMEOUT)
            return None
        except Exception:
            logger.exception("BigQuery source failed")
            return None

    async def _fetch_weather(issue) -> dict | None:
        loc = issue.get("location") or {}
        lat, lng = loc.get("lat"), loc.get("lng")
        if lat is None or lng is None:
            return None
        try:
            async with asyncio.timeout(_SOURCE_TIMEOUT):
                return await weather_tool.get_current_and_forecast(lat, lng)
        except (TimeoutError, asyncio.TimeoutError):
            logger.warning("Weather source timed out after %ds", _SOURCE_TIMEOUT)
            return None
        except Exception:
            logger.exception("Weather source failed")
            return None

    async def _fetch_maps(issue) -> dict | None:
        loc = issue.get("location") or {}
        lat, lng = loc.get("lat"), loc.get("lng")
        if lat is None or lng is None:
            return None
        try:
            async with asyncio.timeout(_SOURCE_TIMEOUT):
                return await maps_tool.get_traffic_context(lat, lng)
        except (TimeoutError, asyncio.TimeoutError):
            logger.warning("Maps source timed out after %ds", _SOURCE_TIMEOUT)
            return None
        except Exception:
            logger.exception("Maps source failed")
            return None

    async def data_intelligence_node(state: GraphState) -> GraphState:
        """Fetch data from all sources concurrently and write to state.context."""
        issue = state.get("issue")

        context: dict[str, Any] = {
            "historical_issues": None,
            "weather": None,
            "traffic": None,
        }

        if issue is None:
            state["context"] = context
            return state

        try:
            async with asyncio.timeout(_TOTAL_SLA):
                results = await asyncio.gather(
                    _fetch_bigquery(issue),
                    _fetch_weather(issue),
                    _fetch_maps(issue),
                    return_exceptions=True,
                )

            bq_result, weather_result, maps_result = results

            context["historical_issues"] = (
                bq_result if not isinstance(bq_result, BaseException) else None
            )
            context["weather"] = (
                weather_result if not isinstance(weather_result, BaseException) else None
            )
            context["traffic"] = (
                maps_result if not isinstance(maps_result, BaseException) else None
            )

        except (TimeoutError, asyncio.TimeoutError):
            logger.warning("data_intelligence_node total SLA exceeded (%ds)", _TOTAL_SLA)

        state["context"] = context
        return state

    return data_intelligence_node
