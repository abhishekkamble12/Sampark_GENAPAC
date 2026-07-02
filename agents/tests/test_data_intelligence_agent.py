"""Unit tests for agents.data_intelligence_agent — tasks 6.1–6.6."""
from __future__ import annotations

import asyncio
import pytest
from agents.data_intelligence_agent import make_data_intelligence_node
from agents.state import GraphState

_CONTEXT_KEYS = {"historical_issues", "weather", "traffic"}


def _make_state(issue=None) -> GraphState:
    if issue is None:
        issue = {
            "id": "iss_1", "type": "road",
            "location": {"lat": 18.52, "lng": 73.86, "address": "MG Road", "ward_id": "w1"},
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


class _BQ:
    def __init__(self, rows=None): self._rows = rows or []
    async def query_historical_issues(self, **kw): return self._rows

class _Weather:
    def __init__(self, data=None):
        self._data = data or {"current": None, "hourly_48h": [], "rainfall_forecast_48h": 0.0}
    async def get_current_and_forecast(self, lat, lng): return self._data

class _Maps:
    def __init__(self, data=None):
        self._data = data or {"traffic_density": "low", "road_classification": "urban", "nearby_facilities": []}
    async def get_traffic_context(self, lat, lng): return self._data


@pytest.mark.asyncio
async def test_all_sources_succeed():
    bq_rows = [{"issue_id": "x", "type": "road"}]
    weather = {"current": {"temp": 28.0}, "hourly_48h": [], "rainfall_forecast_48h": 0.0}
    traffic = {"traffic_density": "medium", "road_classification": "urban", "nearby_facilities": []}

    node = make_data_intelligence_node(_BQ(bq_rows), _Weather(weather), _Maps(traffic))
    result = await node(_make_state())

    ctx = result["context"]
    assert ctx is not None
    assert ctx["historical_issues"] == bq_rows
    assert ctx["weather"] == weather
    assert ctx["traffic"] == traffic


@pytest.mark.asyncio
async def test_context_always_has_all_keys_when_all_fail():
    class _Fail:
        async def query_historical_issues(self, **kw): raise Exception("down")
        async def get_current_and_forecast(self, lat, lng): raise Exception("down")
        async def get_traffic_context(self, lat, lng): raise Exception("down")

    f = _Fail()
    node = make_data_intelligence_node(f, f, f)
    result = await node(_make_state())

    ctx = result["context"]
    assert set(ctx.keys()) == _CONTEXT_KEYS
    assert ctx["historical_issues"] is None
    assert ctx["weather"] is None
    assert ctx["traffic"] is None


@pytest.mark.asyncio
async def test_one_source_times_out_others_succeed():
    bq_rows = [{"issue_id": "y"}]

    class _SlowWeather:
        async def get_current_and_forecast(self, lat, lng):
            await asyncio.sleep(10)  # will be cancelled by timeout
            return {}

    node = make_data_intelligence_node(_BQ(bq_rows), _SlowWeather(), _Maps())
    result = await node(_make_state())

    ctx = result["context"]
    assert ctx["historical_issues"] == bq_rows
    assert ctx["weather"] is None  # timed out
    assert ctx["traffic"] is not None


@pytest.mark.asyncio
async def test_no_issue_returns_null_context():
    state = _make_state()
    state["issue"] = None
    node = make_data_intelligence_node(_BQ(), _Weather(), _Maps())
    result = await node(state)
    ctx = result["context"]
    assert set(ctx.keys()) == _CONTEXT_KEYS
    for v in ctx.values():
        assert v is None


@pytest.mark.asyncio
async def test_no_lat_lng_skips_weather_and_maps():
    issue = {
        "id": "iss_2", "type": "road",
        "location": {"ward_id": "w1"},  # no lat/lng
        "description": "test", "media_refs": [],
        "original_language": None, "severity": None,
    }
    node = make_data_intelligence_node(_BQ([{"x": 1}]), _Weather(), _Maps())
    result = await node(_make_state(issue=issue))
    ctx = result["context"]
    # BQ works (uses ward_id), weather/maps need lat/lng → None
    assert ctx["weather"] is None
    assert ctx["traffic"] is None


from hypothesis import given, settings
from hypothesis import strategies as st

@given(
    bq_fails=st.booleans(),
    weather_fails=st.booleans(),
    maps_fails=st.booleans(),
)
@settings(max_examples=50)
def test_context_always_has_expected_keys(bq_fails, weather_fails, maps_fails):
    """context always has all keys regardless of which sources fail (PBT)."""

    async def _run():
        class _MaybeFail:
            def __init__(self, fails, data):
                self._fails = fails
                self._data = data
            async def query_historical_issues(self, **kw):
                if self._fails: raise Exception("fail")
                return self._data
            async def get_current_and_forecast(self, lat, lng):
                if self._fails: raise Exception("fail")
                return self._data
            async def get_traffic_context(self, lat, lng):
                if self._fails: raise Exception("fail")
                return self._data

        bq = _MaybeFail(bq_fails, [])
        weather = _MaybeFail(weather_fails, {"current": None, "hourly_48h": [], "rainfall_forecast_48h": 0.0})
        maps = _MaybeFail(maps_fails, {"traffic_density": None, "road_classification": None, "nearby_facilities": []})
        node = make_data_intelligence_node(bq, weather, maps)
        result = await node(_make_state())
        ctx = result["context"]
        assert set(ctx.keys()) == _CONTEXT_KEYS

    asyncio.run(_run())
