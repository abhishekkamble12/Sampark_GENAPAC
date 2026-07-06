"""
agents/validation_agent.py — Validation Agent for the Sampark AI Platform.

Scores issue credibility, detects duplicates, and verifies location.

Logic (per design.md §4.2):
1. Geo-query Firestore for open issues within 500m with same issue.type.
2. Call MapsTool.geocode() to verify address within boundary.
3. Call WeatherTool for corroborating evidence.
4. Compute confidence_score from 4 boolean components.
5. Set validation.status based on threshold.

SLA: ≤8 seconds (asyncio.timeout).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

from agents.state import GraphState, ValidationResult

logger = logging.getLogger(__name__)

_SLA_SECONDS = 8

# Issue types where rainfall increases confidence
_WEATHER_CORROBORATE_TYPES = {"flood", "road", "sanitation"}


def _weather_corroborates(issue_type: str, weather: dict | None) -> bool:
    """Return True if weather data supports the given issue type."""
    if weather is None or issue_type not in _WEATHER_CORROBORATE_TYPES:
        return False
    current = weather.get("current") or {}
    desc = (current.get("weather_description") or "").lower()
    rain_48h = weather.get("rainfall_forecast_48h", 0.0) or 0.0
    return rain_48h > 0 or "rain" in desc or "drizzle" in desc or "storm" in desc


def _compute_confidence(
    has_duplicate: bool,
    location_verified: bool,
    weather_corroborated: bool,
    has_media: bool,
) -> float:
    """Compute confidence score from 4 boolean evidence components.

    Weights:
        duplicate complaint: +0.3
        location verified:   +0.3
        weather corroboration: +0.2
        media evidence:      +0.2
    """
    score = 0.0
    if has_duplicate:
        score += 0.3
    if location_verified:
        score += 0.3
    if weather_corroborated:
        score += 0.2
    if has_media:
        score += 0.2
    return round(min(max(score, 0.0), 1.0), 2)


def make_validation_node(
    firestore_tool: Any,
    maps_tool: Any,
    weather_tool: Any,
) -> Callable[[GraphState], Coroutine[Any, Any, GraphState]]:
    """Return an async validation_node with injected dependencies.

    Args:
        firestore_tool: FirestoreTool instance.
        maps_tool:      MapsTool instance.
        weather_tool:   WeatherTool instance.
    """

    async def validation_node(state: GraphState) -> GraphState:
        """Score issue credibility and write ValidationResult to state."""
        issue = state.get("issue")

        # Edge case: no issue or no location
        if issue is None or issue.get("location") is None:
            state["validation"] = ValidationResult(
                duplicate=False,
                confidence_score=0.0,
                status="low_confidence",
                location_verified=False,
                failure_reason="missing_issue_or_location",
            )
            return state

        location = issue["location"]
        issue_type = issue.get("type", "other")
        lat = location.get("lat")
        lng = location.get("lng")
        address = location.get("address", "")

        try:
            async with asyncio.timeout(_SLA_SECONDS):
                # ---- 1. Duplicate detection (Firestore geo-radius) --------
                has_duplicate = False
                try:
                    if lat is not None and lng is not None:
                        nearby = await firestore_tool.geo_radius_query(
                            collection="issues",
                            lat=lat,
                            lng=lng,
                            radius_meters=500,
                            filters={"type": issue_type, "status": "open"},
                        )
                        has_duplicate = len(nearby) > 0
                except Exception:
                    logger.warning("Duplicate detection failed — treating as no duplicate")

                # ---- 2. Location verification (Maps geocoding) ------------
                location_verified = False
                failure_reason: str | None = None
                try:
                    geocoded = await maps_tool.geocode(address or f"{lat},{lng}")
                    if geocoded is not None:
                        location_verified = True
                        # Enrich location with geocoded coordinates if missing
                        if lat is None:
                            issue["location"]["lat"] = geocoded["lat"]
                            issue["location"]["lng"] = geocoded["lng"]
                            state["issue"] = issue
                    else:
                        failure_reason = "geocode_no_result"
                except Exception:
                    logger.warning("Location verification failed")
                    failure_reason = "geocode_error"

                # ---- 3. Weather corroboration ----------------------------
                weather_corroborated = False
                try:
                    if lat is not None and lng is not None:
                        weather = await weather_tool.get_current_and_forecast(lat, lng)
                        weather_corroborated = _weather_corroborates(issue_type, weather)
                except Exception:
                    logger.warning("Weather corroboration failed")

                # ---- 4. Media evidence -----------------------------------
                has_media = bool(issue.get("media_refs"))

                # ---- 5. Confidence score & status -----------------------
                score = _compute_confidence(
                    has_duplicate, location_verified, weather_corroborated, has_media
                )
                status = "valid" if score >= 0.4 else "low_confidence"

        except TimeoutError:
            logger.warning("validation_node SLA exceeded (%ds)", _SLA_SECONDS)
            state["validation"] = ValidationResult(
                duplicate=False,
                confidence_score=0.0,
                status="low_confidence",
                location_verified=False,
                failure_reason="timeout",
                weather_corroborated=False,
                has_media=False,
            )
            return state

        state["validation"] = ValidationResult(
            duplicate=has_duplicate,
            confidence_score=score,
            status=status,
            location_verified=location_verified,
            failure_reason=failure_reason,
            weather_corroborated=weather_corroborated,
            has_media=has_media,
        )
        return state

    return validation_node
