"""
agents/validation_agent.py — Validation Agent for the Sampark AI Platform.

Scores the credibility of a citizen-reported issue by combining four
evidence signals into a ``confidence_score``.

External dependencies (FirestoreTool, MapsTool, WeatherTool) are injected
via ``make_validation_node`` so that unit tests can supply mocks without
real API calls.

Logic (per design.md §4.2):
1. Geo-query Firestore for open issues within 500 m with the same type.
2. Call ``MapsTool.geocode(address)`` to verify the address is within the
   configured municipal boundary.
3. Call ``WeatherTool.get_current_and_forecast(lat, lng)`` for corroborating
   weather context.
4. Compute ``confidence_score``:
   - +0.3 if ≥1 corroborating complaint found (duplicate check)
   - +0.3 if location verified by Maps
   - +0.2 if weather corroborates the issue type
   - +0.2 if image/audio evidence is present (non-empty ``issue.media_refs``)
5. Set ``validation.status`` to ``"low_confidence"`` if score < 0.4,
   else ``"valid"``.

SLA: ≤8 seconds enforced with ``asyncio.timeout``.

Edge cases:
- ``state["issue"]`` is None or has no location → low_confidence, score 0.0.
- Any individual tool call failing → treat that evidence component as False.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

from agents.state import GraphState, ValidationResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SLA_SECONDS = 8

# Issue types for which rain/flooding weather is considered corroborating.
_WEATHER_CORROBORATED_TYPES: frozenset[str] = frozenset({"flood", "road", "sanitation"})

_SCORE_DUPLICATE: float = 0.3
_SCORE_LOCATION: float = 0.3
_SCORE_WEATHER: float = 0.2
_SCORE_MEDIA: float = 0.2

_THRESHOLD_LOW_CONFIDENCE: float = 0.4


# ---------------------------------------------------------------------------
# Weather corroboration helper
# ---------------------------------------------------------------------------


def _weather_corroborates(issue_type: str, weather: dict[str, Any]) -> bool:
    """Return True when the weather context supports the given issue type.

    For issue types in ``_WEATHER_CORROBORATED_TYPES`` (flood, road,
    sanitation), rain is considered corroborating evidence when:
    - ``rainfall_forecast_48h > 0``, OR
    - The current weather description contains the word "rain".

    For all other issue types, always returns False.

    Args:
        issue_type: The canonical issue type string.
        weather:    Dict returned by ``WeatherTool.get_current_and_forecast``.

    Returns:
        True if the weather corroborates the issue, False otherwise.
    """
    if issue_type not in _WEATHER_CORROBORATED_TYPES:
        return False

    # Check 48-hour rainfall forecast
    if weather.get("rainfall_forecast_48h", 0) > 0:
        return True

    # Check current weather description for "rain"
    current = weather.get("current") or {}
    description: str = current.get("weather_description") or ""
    if "rain" in description.lower():
        return True

    return False


# ---------------------------------------------------------------------------
# Confidence score computation
# ---------------------------------------------------------------------------


def compute_confidence_score(
    duplicate: bool,
    location_verified: bool,
    weather_corroborated: bool,
    has_media: bool,
) -> float:
    """Compute a composite credibility score in [0.0, 1.0].

    Scoring components:
    - +0.3 if at least one corroborating complaint was found nearby.
    - +0.3 if the location was verified by the Maps geocoding service.
    - +0.2 if the current/forecast weather corroborates the issue type.
    - +0.2 if image or audio evidence is attached (``media_refs`` non-empty).

    The returned value is always clamped to [0.0, 1.0].

    Args:
        duplicate:            True if ≥1 nearby issue of the same type was found.
        location_verified:    True if geocoding confirmed the address.
        weather_corroborated: True if weather context supports the issue type.
        has_media:            True if ``issue.media_refs`` is non-empty.

    Returns:
        Float in [0.0, 1.0].
    """
    score = 0.0
    if duplicate:
        score += _SCORE_DUPLICATE
    if location_verified:
        score += _SCORE_LOCATION
    if weather_corroborated:
        score += _SCORE_WEATHER
    if has_media:
        score += _SCORE_MEDIA
    # Clamp to [0.0, 1.0] as a safety measure
    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def make_validation_node(
    firestore_tool: Any,
    maps_tool: Any,
    weather_tool: Any,
) -> Callable[[GraphState], Coroutine[Any, Any, GraphState]]:
    """Return an async ``validation_node`` function with injected dependencies.

    Args:
        firestore_tool: Instance of ``FirestoreTool`` (or compatible mock).
                        Must expose ``async geo_radius_query(collection, lat,
                        lng, radius_meters, filters) -> list[dict]``.
        maps_tool:      Instance of ``MapsTool`` (or compatible mock).
                        Must expose ``async geocode(location_str) -> dict | None``.
        weather_tool:   Instance of ``WeatherTool`` (or compatible mock).
                        Must expose ``async get_current_and_forecast(lat, lng)
                        -> dict``.

    Returns:
        An async callable ``validation_node(state) -> state`` suitable for
        LangGraph node registration.
    """

    async def validation_node(state: GraphState) -> GraphState:  # noqa: C901
        """LangGraph node: score issue credibility and populate ValidationResult."""

        issue = state.get("issue")

        # ------------------------------------------------------------------
        # Edge case: no issue or no location → low_confidence with zero score
        # ------------------------------------------------------------------
        if issue is None or issue.get("location") is None:
            logger.warning("validation_node: issue or location is None; setting low_confidence")
            state["validation"] = ValidationResult(
                duplicate=False,
                confidence_score=0.0,
                status="low_confidence",
                location_verified=False,
                failure_reason="issue or location is missing",
            )
            return state

        location: dict = issue["location"]
        issue_type: str = issue.get("type", "other")
        lat: float | None = location.get("lat")
        lng: float | None = location.get("lng")
        address: str | None = location.get("address")
        media_refs: list[str] = issue.get("media_refs") or []

        # ------------------------------------------------------------------
        # Evidence signals (collected within the 8-second SLA)
        # ------------------------------------------------------------------
        duplicate = False
        location_verified = False
        weather_corroborated = False
        has_media = bool(media_refs)

        try:
            async with asyncio.timeout(_SLA_SECONDS):

                # ---- 1. Duplicate / corroborating complaint check --------
                if lat is not None and lng is not None:
                    try:
                        nearby_issues = await firestore_tool.geo_radius_query(
                            "issues",
                            lat=lat,
                            lng=lng,
                            radius_meters=500,
                            filters={"type": issue_type, "status": "open"},
                        )
                        duplicate = len(nearby_issues) >= 1
                    except Exception:
                        logger.exception(
                            "validation_node: Firestore geo_radius_query failed; "
                            "treating duplicate as False"
                        )

                # ---- 2. Location verification via Maps geocoding ----------
                location_str: str | None = address
                if not location_str and lat is not None and lng is not None:
                    location_str = f"{lat},{lng}"

                if location_str:
                    try:
                        geocode_result = await maps_tool.geocode(location_str)
                        location_verified = geocode_result is not None
                    except Exception:
                        logger.exception(
                            "validation_node: MapsTool.geocode failed; "
                            "treating location_verified as False"
                        )

                # ---- 3. Weather corroboration ----------------------------
                if lat is not None and lng is not None:
                    try:
                        weather = await weather_tool.get_current_and_forecast(lat, lng)
                        weather_corroborated = _weather_corroborates(issue_type, weather)
                    except Exception:
                        logger.exception(
                            "validation_node: WeatherTool call failed; "
                            "treating weather_corroborated as False"
                        )

        except TimeoutError:
            logger.warning(
                "validation_node: 8-second SLA exceeded; proceeding with partial evidence"
            )

        # ------------------------------------------------------------------
        # 4. Compute confidence score
        # ------------------------------------------------------------------
        confidence_score = compute_confidence_score(
            duplicate=duplicate,
            location_verified=location_verified,
            weather_corroborated=weather_corroborated,
            has_media=has_media,
        )

        # ------------------------------------------------------------------
        # 5. Determine validation status
        # ------------------------------------------------------------------
        status = "valid" if confidence_score >= _THRESHOLD_LOW_CONFIDENCE else "low_confidence"

        state["validation"] = ValidationResult(
            duplicate=duplicate,
            confidence_score=confidence_score,
            status=status,
            location_verified=location_verified,
            failure_reason=None,
        )

        logger.info(
            "validation_node complete: duplicate=%s location_verified=%s "
            "weather=%s media=%s score=%.2f status=%s",
            duplicate,
            location_verified,
            weather_corroborated,
            has_media,
            confidence_score,
            status,
        )

        return state

    return validation_node
