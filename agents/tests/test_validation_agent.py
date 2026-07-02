"""
Unit tests for agents.validation_agent — tasks 5.1–5.8.

Covers:
- Duplicate found → validation.duplicate = True, score includes +0.3
- Location invalid (geocode returns None) → location_verified = False
- Low confidence (score < 0.4) → status = "low_confidence"
- Valid path (score >= 0.4) → status = "valid"
- Weather corroboration for flood issue
- All tools raise exceptions → still produces a valid ValidationResult
- Edge case: issue is None → low_confidence, score 0.0
- Edge case: issue location is None → low_confidence, score 0.0
"""

from __future__ import annotations

import pytest

from agents.state import GraphState, IssueObject
from agents.validation_agent import (
    _weather_corroborates,
    compute_confidence_score,
    make_validation_node,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    issue: IssueObject | None = None,
) -> GraphState:
    """Build a minimal GraphState for validation testing."""
    if issue is None:
        issue = _default_issue()
    return {
        "query": "test query",
        "user": {
            "user_id": "u1",
            "role": "citizen",
            "ward_ids": ["w1"],
            "preferred_channel": "email",
        },
        "issue": issue,
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
            "session_id": "sess_test",
            "status": "running",
            "retry_count": 0,
            "node_checkpoints": [],
        },
    }


def _default_issue(
    issue_type: str = "road",
    lat: float = 18.52,
    lng: float = 73.86,
    address: str = "MG Road, Pune",
    media_refs: list[str] | None = None,
) -> IssueObject:
    return {
        "id": "iss_001",
        "type": issue_type,
        "location": {"lat": lat, "lng": lng, "address": address, "ward_id": "w1"},
        "description": "Large pothole near school",
        "media_refs": media_refs or [],
        "original_language": None,
        "severity": None,
    }


# ---------------------------------------------------------------------------
# Mock tool factories
# ---------------------------------------------------------------------------


class _MockFirestoreTool:
    """Configurable mock for FirestoreTool.geo_radius_query."""

    def __init__(self, nearby_issues: list[dict] | None = None, raise_exc: bool = False):
        self._nearby = nearby_issues or []
        self._raise = raise_exc

    async def geo_radius_query(
        self,
        collection: str,  # noqa: ARG002
        lat: float,  # noqa: ARG002
        lng: float,  # noqa: ARG002
        radius_meters: float,  # noqa: ARG002
        filters: dict | None = None,  # noqa: ARG002
    ) -> list[dict]:
        if self._raise:
            raise RuntimeError("Firestore unavailable")
        return self._nearby


class _MockMapsTool:
    """Configurable mock for MapsTool.geocode."""

    def __init__(self, result: dict | None = None, raise_exc: bool = False):
        self._result = result
        self._raise = raise_exc

    async def geocode(self, location_str: str) -> dict | None:  # noqa: ARG002
        if self._raise:
            raise RuntimeError("Maps API unavailable")
        return self._result


class _MockWeatherTool:
    """Configurable mock for WeatherTool.get_current_and_forecast."""

    def __init__(self, weather: dict | None = None, raise_exc: bool = False):
        self._weather = weather or {
            "current": {"weather_description": "clear sky"},
            "hourly_48h": [],
            "rainfall_forecast_48h": 0.0,
        }
        self._raise = raise_exc

    async def get_current_and_forecast(self, lat: float, lng: float) -> dict:  # noqa: ARG002
        if self._raise:
            raise RuntimeError("Weather API unavailable")
        return self._weather


# ---------------------------------------------------------------------------
# Tests: compute_confidence_score (pure function)
# ---------------------------------------------------------------------------


class TestComputeConfidenceScore:
    def test_all_false_gives_zero(self):
        score = compute_confidence_score(False, False, False, False)
        assert score == 0.0

    def test_all_true_gives_one(self):
        score = compute_confidence_score(True, True, True, True)
        assert score == 1.0

    def test_duplicate_only(self):
        score = compute_confidence_score(True, False, False, False)
        assert abs(score - 0.3) < 1e-9

    def test_location_only(self):
        score = compute_confidence_score(False, True, False, False)
        assert abs(score - 0.3) < 1e-9

    def test_weather_only(self):
        score = compute_confidence_score(False, False, True, False)
        assert abs(score - 0.2) < 1e-9

    def test_media_only(self):
        score = compute_confidence_score(False, False, False, True)
        assert abs(score - 0.2) < 1e-9

    def test_duplicate_and_location(self):
        score = compute_confidence_score(True, True, False, False)
        assert abs(score - 0.6) < 1e-9

    def test_score_below_threshold_is_low_confidence(self):
        # Only weather: 0.2 < 0.4
        score = compute_confidence_score(False, False, True, False)
        assert score < 0.4

    def test_score_above_threshold_is_valid(self):
        # Duplicate + location: 0.6 >= 0.4
        score = compute_confidence_score(True, True, False, False)
        assert score >= 0.4


# ---------------------------------------------------------------------------
# Tests: _weather_corroborates (pure function)
# ---------------------------------------------------------------------------


class TestWeatherCorroborates:
    def test_flood_with_rain_forecast(self):
        weather = {
            "current": {"weather_description": "clear sky"},
            "rainfall_forecast_48h": 5.0,
        }
        assert _weather_corroborates("flood", weather) is True

    def test_road_with_rain_description(self):
        weather = {
            "current": {"weather_description": "light rain"},
            "rainfall_forecast_48h": 0.0,
        }
        assert _weather_corroborates("road", weather) is True

    def test_sanitation_with_rain_description(self):
        weather = {
            "current": {"weather_description": "heavy rain"},
            "rainfall_forecast_48h": 0.0,
        }
        assert _weather_corroborates("sanitation", weather) is True

    def test_flood_with_no_rain(self):
        weather = {
            "current": {"weather_description": "sunny"},
            "rainfall_forecast_48h": 0.0,
        }
        assert _weather_corroborates("flood", weather) is False

    def test_electricity_never_corroborated(self):
        weather = {
            "current": {"weather_description": "heavy rain"},
            "rainfall_forecast_48h": 100.0,
        }
        assert _weather_corroborates("electricity", weather) is False

    def test_health_never_corroborated(self):
        weather = {
            "current": {"weather_description": "heavy rain"},
            "rainfall_forecast_48h": 10.0,
        }
        assert _weather_corroborates("health", weather) is False

    def test_water_never_corroborated(self):
        weather = {
            "current": {"weather_description": "heavy rain"},
            "rainfall_forecast_48h": 10.0,
        }
        assert _weather_corroborates("water", weather) is False

    def test_current_none_with_rain_forecast(self):
        """current may be None if weather tool returned error response."""
        weather = {"current": None, "rainfall_forecast_48h": 2.0}
        assert _weather_corroborates("flood", weather) is True

    def test_current_none_no_rain(self):
        weather = {"current": None, "rainfall_forecast_48h": 0.0}
        assert _weather_corroborates("flood", weather) is False


# ---------------------------------------------------------------------------
# Tests: make_validation_node / validation_node (async integration)
# ---------------------------------------------------------------------------


class TestValidationNodeDuplicateDetection:
    @pytest.mark.asyncio
    async def test_duplicate_found_sets_duplicate_true(self):
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(nearby_issues=[{"id": "iss_other", "type": "road"}]),
            maps_tool=_MockMapsTool(result=None),  # location not verified
            weather_tool=_MockWeatherTool(),
        )
        state = _make_state()
        result = await node(state)
        assert result["validation"]["duplicate"] is True

    @pytest.mark.asyncio
    async def test_duplicate_found_adds_score(self):
        """Duplicate contributes +0.3 to the score."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(nearby_issues=[{"id": "iss_other"}]),
            maps_tool=_MockMapsTool(result=None),
            weather_tool=_MockWeatherTool(),
        )
        state = _make_state()
        result = await node(state)
        assert result["validation"]["confidence_score"] >= 0.3

    @pytest.mark.asyncio
    async def test_no_duplicates_sets_duplicate_false(self):
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(nearby_issues=[]),
            maps_tool=_MockMapsTool(result=None),
            weather_tool=_MockWeatherTool(),
        )
        state = _make_state()
        result = await node(state)
        assert result["validation"]["duplicate"] is False


class TestValidationNodeLocationVerification:
    @pytest.mark.asyncio
    async def test_geocode_returns_result_sets_location_verified_true(self):
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(),
            maps_tool=_MockMapsTool(result={"lat": 18.52, "lng": 73.86, "address": "MG Road"}),
            weather_tool=_MockWeatherTool(),
        )
        state = _make_state()
        result = await node(state)
        assert result["validation"]["location_verified"] is True

    @pytest.mark.asyncio
    async def test_geocode_returns_none_sets_location_verified_false(self):
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(),
            maps_tool=_MockMapsTool(result=None),
            weather_tool=_MockWeatherTool(),
        )
        state = _make_state()
        result = await node(state)
        assert result["validation"]["location_verified"] is False


class TestValidationNodeConfidenceStatus:
    @pytest.mark.asyncio
    async def test_low_confidence_when_score_below_threshold(self):
        """All tools return nothing useful → score = 0.0 → low_confidence."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(nearby_issues=[]),
            maps_tool=_MockMapsTool(result=None),
            weather_tool=_MockWeatherTool(
                weather={
                    "current": {"weather_description": "clear"},
                    "rainfall_forecast_48h": 0.0,
                }
            ),
        )
        state = _make_state(issue=_default_issue(issue_type="road"))
        result = await node(state)
        assert result["validation"]["status"] == "low_confidence"
        assert result["validation"]["confidence_score"] < 0.4

    @pytest.mark.asyncio
    async def test_valid_when_score_meets_threshold(self):
        """Duplicate + location verified → 0.6 >= 0.4 → valid."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(nearby_issues=[{"id": "iss_other"}]),
            maps_tool=_MockMapsTool(result={"lat": 18.52, "lng": 73.86, "address": "MG Road"}),
            weather_tool=_MockWeatherTool(),
        )
        state = _make_state()
        result = await node(state)
        assert result["validation"]["status"] == "valid"
        assert result["validation"]["confidence_score"] >= 0.4

    @pytest.mark.asyncio
    async def test_media_refs_contribute_to_score(self):
        """Issue with media_refs should score +0.2 for media."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(nearby_issues=[]),
            maps_tool=_MockMapsTool(result=None),
            weather_tool=_MockWeatherTool(),
        )
        issue = _default_issue(media_refs=["gs://sampark-media/iss_001/image1.jpg"])
        state = _make_state(issue=issue)
        result = await node(state)
        assert result["validation"]["confidence_score"] >= 0.2


class TestValidationNodeWeatherCorroboration:
    @pytest.mark.asyncio
    async def test_weather_corroborates_flood_issue_with_rain(self):
        """Flood issue + rain forecast → weather contributes +0.2."""
        rainy_weather = {
            "current": {"weather_description": "light rain"},
            "hourly_48h": [],
            "rainfall_forecast_48h": 3.5,
        }
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(nearby_issues=[]),
            maps_tool=_MockMapsTool(result=None),
            weather_tool=_MockWeatherTool(weather=rainy_weather),
        )
        state = _make_state(issue=_default_issue(issue_type="flood"))
        result = await node(state)
        # Score should be exactly 0.2 (weather only)
        assert abs(result["validation"]["confidence_score"] - 0.2) < 1e-9

    @pytest.mark.asyncio
    async def test_weather_does_not_corroborate_electricity_issue(self):
        """Rain weather should NOT corroborate an electricity issue."""
        rainy_weather = {
            "current": {"weather_description": "heavy rain"},
            "hourly_48h": [],
            "rainfall_forecast_48h": 10.0,
        }
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(nearby_issues=[]),
            maps_tool=_MockMapsTool(result=None),
            weather_tool=_MockWeatherTool(weather=rainy_weather),
        )
        state = _make_state(issue=_default_issue(issue_type="electricity"))
        result = await node(state)
        assert result["validation"]["confidence_score"] == 0.0


class TestValidationNodeErrorHandling:
    @pytest.mark.asyncio
    async def test_all_tools_raise_still_produces_valid_result(self):
        """If every tool call raises, we get a ValidationResult with score 0."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(raise_exc=True),
            maps_tool=_MockMapsTool(raise_exc=True),
            weather_tool=_MockWeatherTool(raise_exc=True),
        )
        state = _make_state()
        result = await node(state)
        validation = result["validation"]
        # Should still have a complete ValidationResult
        assert validation is not None
        assert "confidence_score" in validation
        assert "status" in validation
        assert "duplicate" in validation
        assert "location_verified" in validation
        assert validation["duplicate"] is False
        assert validation["location_verified"] is False
        assert validation["confidence_score"] == 0.0
        assert validation["status"] == "low_confidence"

    @pytest.mark.asyncio
    async def test_firestore_raises_others_succeed(self):
        """Firestore failure → duplicate=False, but location + weather can still score."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(raise_exc=True),
            maps_tool=_MockMapsTool(result={"lat": 18.52, "lng": 73.86, "address": "MG Road"}),
            weather_tool=_MockWeatherTool(
                weather={
                    "current": {"weather_description": "light rain"},
                    "rainfall_forecast_48h": 1.0,
                }
            ),
        )
        state = _make_state(issue=_default_issue(issue_type="road"))
        result = await node(state)
        assert result["validation"]["duplicate"] is False
        assert result["validation"]["location_verified"] is True
        # location(0.3) + weather(0.2) = 0.5
        assert abs(result["validation"]["confidence_score"] - 0.5) < 1e-9


class TestValidationNodeEdgeCases:
    @pytest.mark.asyncio
    async def test_issue_is_none_returns_low_confidence(self):
        """If state['issue'] is None, output low_confidence with score 0."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(),
            maps_tool=_MockMapsTool(),
            weather_tool=_MockWeatherTool(),
        )
        state = _make_state(issue=None)
        state["issue"] = None  # explicit override
        result = await node(state)
        assert result["validation"]["status"] == "low_confidence"
        assert result["validation"]["confidence_score"] == 0.0
        assert result["validation"]["location_verified"] is False
        assert result["validation"]["duplicate"] is False

    @pytest.mark.asyncio
    async def test_issue_location_is_none_returns_low_confidence(self):
        """If issue.location is None, output low_confidence with score 0."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(),
            maps_tool=_MockMapsTool(),
            weather_tool=_MockWeatherTool(),
        )
        issue_no_loc: IssueObject = {
            "id": "iss_002",
            "type": "road",
            "location": None,
            "description": "Unknown road issue",
            "media_refs": [],
            "original_language": None,
            "severity": None,
        }
        state = _make_state(issue=issue_no_loc)
        result = await node(state)
        assert result["validation"]["status"] == "low_confidence"
        assert result["validation"]["confidence_score"] == 0.0

    @pytest.mark.asyncio
    async def test_validation_result_always_has_all_required_keys(self):
        """ValidationResult must always contain all TypedDict keys."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(),
            maps_tool=_MockMapsTool(),
            weather_tool=_MockWeatherTool(),
        )
        state = _make_state()
        result = await node(state)
        validation = result["validation"]
        required_keys = {"duplicate", "confidence_score", "status", "location_verified", "failure_reason"}
        assert required_keys.issubset(set(validation.keys()))

    @pytest.mark.asyncio
    async def test_score_is_clamped_to_one(self):
        """Regardless of inputs, score must not exceed 1.0."""
        node = make_validation_node(
            firestore_tool=_MockFirestoreTool(nearby_issues=[{"id": "x"}]),
            maps_tool=_MockMapsTool(result={"lat": 18.52, "lng": 73.86, "address": "MG Road"}),
            weather_tool=_MockWeatherTool(
                weather={
                    "current": {"weather_description": "heavy rain"},
                    "rainfall_forecast_48h": 5.0,
                }
            ),
        )
        issue = _default_issue(
            issue_type="flood",
            media_refs=["gs://sampark-media/iss_001/image1.jpg"],
        )
        state = _make_state(issue=issue)
        result = await node(state)
        assert result["validation"]["confidence_score"] <= 1.0
