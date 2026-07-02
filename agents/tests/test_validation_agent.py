"""
Unit tests for agents.validation_agent — tasks 5.1–5.8.

Scenarios:
1. Duplicate found → validation.duplicate = True, score includes +0.3
2. Location invalid (geocode None) → location_verified = False
3. Low confidence (score < 0.4) → status = "low_confidence"
4. Valid path (score ≥ 0.4) → status = "valid"
5. Weather corroboration for flood issue
6. All tools return errors → still produces valid ValidationResult
7. No issue → low_confidence immediately
8. No location → low_confidence immediately
"""
from __future__ import annotations

import pytest
from agents.validation_agent import make_validation_node, _compute_confidence, _weather_corroborates
from agents.state import GraphState


# ---------------------------------------------------------------------------
# Fake tools
# ---------------------------------------------------------------------------

class _FS:
    def __init__(self, nearby=None):
        self._nearby = nearby or []
    async def geo_radius_query(self, **kw):
        return self._nearby

class _Maps:
    def __init__(self, result=None):
        self._result = result
    async def geocode(self, loc):
        return self._result

class _Weather:
    def __init__(self, data=None):
        self._data = data or {"current": None, "hourly_48h": [], "rainfall_forecast_48h": 0.0}
    async def get_current_and_forecast(self, lat, lng):
        return self._data


def _make_state(issue=None) -> GraphState:
    if issue is None:
        issue = {
            "id": "iss_1", "type": "road",
            "location": {"lat": 18.52, "lng": 73.86, "address": "MG Road"},
            "description": "pothole", "media_refs": [],
            "original_language": None, "severity": None,
        }
    return {
        "query": "test", "user": {}, "issue": issue,
        "validation": None, "context": None, "analytics": None,
        "prediction": None, "rag_chunks": None, "recommendation": None,
        "workflow": None, "response": None, "intake_error": None,
        "translation_error": False, "extraction_error": False,
        "no_policy_context": False,
        "execution": {"session_id": "s1", "status": "running", "retry_count": 0, "node_checkpoints": []},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_found_sets_flag_and_adds_score():
    node = make_validation_node(
        firestore_tool=_FS(nearby=[{"id": "existing"}]),
        maps_tool=_Maps(result={"lat": 18.52, "lng": 73.86, "address": "MG Road", "ward_id": "w1"}),
        weather_tool=_Weather(),
    )
    result = await node(_make_state())
    v = result["validation"]
    assert v["duplicate"] is True
    assert v["confidence_score"] >= 0.3


@pytest.mark.asyncio
async def test_no_duplicate_found():
    node = make_validation_node(
        firestore_tool=_FS(nearby=[]),
        maps_tool=_Maps(result={"lat": 18.52, "lng": 73.86, "address": "MG Road", "ward_id": None}),
        weather_tool=_Weather(),
    )
    result = await node(_make_state())
    assert result["validation"]["duplicate"] is False


@pytest.mark.asyncio
async def test_location_invalid_geocode_none():
    node = make_validation_node(
        firestore_tool=_FS(),
        maps_tool=_Maps(result=None),
        weather_tool=_Weather(),
    )
    result = await node(_make_state())
    v = result["validation"]
    assert v["location_verified"] is False
    assert v["failure_reason"] == "geocode_no_result"


@pytest.mark.asyncio
async def test_low_confidence_when_all_evidence_absent():
    node = make_validation_node(
        firestore_tool=_FS(nearby=[]),
        maps_tool=_Maps(result=None),
        weather_tool=_Weather(),
    )
    result = await node(_make_state())
    v = result["validation"]
    assert v["confidence_score"] < 0.4
    assert v["status"] == "low_confidence"


@pytest.mark.asyncio
async def test_valid_status_when_location_and_duplicate():
    node = make_validation_node(
        firestore_tool=_FS(nearby=[{"id": "x"}]),
        maps_tool=_Maps(result={"lat": 18.52, "lng": 73.86, "address": "MG Road", "ward_id": None}),
        weather_tool=_Weather(),
    )
    result = await node(_make_state())
    v = result["validation"]
    assert v["confidence_score"] >= 0.4
    assert v["status"] == "valid"


@pytest.mark.asyncio
async def test_weather_corroboration_for_flood():
    issue = {
        "id": "iss_2", "type": "flood",
        "location": {"lat": 18.52, "lng": 73.86, "address": "Station Road"},
        "description": "flooding", "media_refs": [],
        "original_language": None, "severity": None,
    }
    node = make_validation_node(
        firestore_tool=_FS(nearby=[]),
        maps_tool=_Maps(result=None),
        weather_tool=_Weather(data={
            "current": {"weather_description": "heavy rain", "temp": 25.0, "feels_like": 27.0,
                        "humidity": 95, "wind_speed": 10.0, "rain_1h": 5.0},
            "hourly_48h": [],
            "rainfall_forecast_48h": 30.0,
        }),
    )
    result = await node(_make_state(issue=issue))
    v = result["validation"]
    assert v["confidence_score"] >= 0.2  # at least weather component


@pytest.mark.asyncio
async def test_media_evidence_adds_score():
    issue = {
        "id": "iss_3", "type": "road",
        "location": {"lat": 18.52, "lng": 73.86, "address": "MG Road"},
        "description": "pothole", "media_refs": ["gs://bucket/iss_3/img.jpg"],
        "original_language": None, "severity": None,
    }
    node = make_validation_node(
        firestore_tool=_FS(),
        maps_tool=_Maps(result=None),
        weather_tool=_Weather(),
    )
    result = await node(_make_state(issue=issue))
    v = result["validation"]
    assert v["confidence_score"] >= 0.2  # media adds 0.2


@pytest.mark.asyncio
async def test_all_tools_raise_returns_low_confidence():
    class _BrokenFS:
        async def geo_radius_query(self, **kw):
            raise Exception("FS down")

    class _BrokenMaps:
        async def geocode(self, loc):
            raise Exception("Maps down")

    class _BrokenWeather:
        async def get_current_and_forecast(self, lat, lng):
            raise Exception("Weather down")

    node = make_validation_node(
        firestore_tool=_BrokenFS(),
        maps_tool=_BrokenMaps(),
        weather_tool=_BrokenWeather(),
    )
    result = await node(_make_state())
    v = result["validation"]
    assert v is not None
    assert v["status"] == "low_confidence"
    assert 0.0 <= v["confidence_score"] <= 1.0


@pytest.mark.asyncio
async def test_no_issue_returns_low_confidence():
    state = _make_state()
    state["issue"] = None
    node = make_validation_node(firestore_tool=_FS(), maps_tool=_Maps(), weather_tool=_Weather())
    result = await node(state)
    assert result["validation"]["status"] == "low_confidence"


@pytest.mark.asyncio
async def test_no_location_returns_low_confidence():
    issue = {
        "id": "iss_4", "type": "road", "location": None,
        "description": "pothole", "media_refs": [],
        "original_language": None, "severity": None,
    }
    node = make_validation_node(firestore_tool=_FS(), maps_tool=_Maps(), weather_tool=_Weather())
    result = await node(_make_state(issue=issue))
    assert result["validation"]["status"] == "low_confidence"


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------

def test_compute_confidence_all_true():
    assert _compute_confidence(True, True, True, True) == 1.0

def test_compute_confidence_all_false():
    assert _compute_confidence(False, False, False, False) == 0.0

def test_compute_confidence_partial():
    assert _compute_confidence(True, True, False, False) == pytest.approx(0.6)

def test_compute_confidence_clamps_to_1():
    # Even with all True the max is 1.0
    assert _compute_confidence(True, True, True, True) <= 1.0

def test_weather_corroborates_flood_rain():
    w = {"current": {"weather_description": "heavy rain"}, "rainfall_forecast_48h": 10.0}
    assert _weather_corroborates("flood", w) is True

def test_weather_corroborates_electricity_rain():
    w = {"current": {"weather_description": "heavy rain"}, "rainfall_forecast_48h": 10.0}
    assert _weather_corroborates("electricity", w) is False  # not in corroborate types

def test_weather_corroborates_no_rain():
    w = {"current": {"weather_description": "clear sky"}, "rainfall_forecast_48h": 0.0}
    assert _weather_corroborates("flood", w) is False
