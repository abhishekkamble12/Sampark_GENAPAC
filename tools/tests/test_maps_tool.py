"""Unit tests for tools/maps_tool.py."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from tools.maps_tool import MapsTool

@pytest.fixture(autouse=True)
def _patch_app_mode():
    with patch("backend.config.settings.APP_MODE", "production"):
        yield


def _make_geocode_response(lat=18.52, lng=73.86, address="MG Road, Pune") -> dict:
    return {
        "status": "OK",
        "results": [{
            "geometry": {"location": {"lat": lat, "lng": lng}},
            "formatted_address": address,
            "address_components": [
                {"types": ["sublocality"], "short_name": "ward_5"},
            ],
        }],
    }


def _mock_async_client(json_response: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = json_response
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=mock_resp)
    return mock_client


@pytest.mark.asyncio
async def test_geocode_returns_location():
    tool = MapsTool(api_key="key")
    with patch("tools.maps_tool.httpx.AsyncClient", return_value=_mock_async_client(_make_geocode_response())):
        result = await tool.geocode("MG Road, Pune")
    assert result is not None
    assert result["lat"] == 18.52
    assert result["lng"] == 73.86
    assert result["ward_id"] == "ward_5"


@pytest.mark.asyncio
async def test_geocode_returns_none_when_no_results():
    tool = MapsTool(api_key="key")
    with patch("tools.maps_tool.httpx.AsyncClient", return_value=_mock_async_client({"status": "ZERO_RESULTS", "results": []})):
        result = await tool.geocode("nonexistent place xyz")
    assert result is None


@pytest.mark.asyncio
async def test_geocode_returns_none_outside_boundary():
    tool = MapsTool(
        api_key="key",
        boundary={"min_lat": 18.0, "max_lat": 18.6, "min_lng": 73.5, "max_lng": 74.0}
    )
    # Location outside boundary
    with patch("tools.maps_tool.httpx.AsyncClient", return_value=_mock_async_client(
        _make_geocode_response(lat=20.0, lng=80.0)
    )):
        result = await tool.geocode("Mumbai")
    assert result is None


@pytest.mark.asyncio
async def test_geocode_returns_none_on_exception():
    tool = MapsTool(api_key="key")
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=httpx.RequestError("network error"))
    with patch("tools.maps_tool.httpx.AsyncClient", return_value=mock_client):
        result = await tool.geocode("anywhere")
    assert result is None


@pytest.mark.asyncio
async def test_get_traffic_context_returns_dict():
    tool = MapsTool(api_key="key")
    places_response = {
        "status": "OK",
        "results": [{"name": "Hospital", "types": ["hospital"]}] * 8,
    }
    with patch("tools.maps_tool.httpx.AsyncClient", return_value=_mock_async_client(places_response)):
        result = await tool.get_traffic_context(18.52, 73.86)
    assert result["traffic_density"] == "medium"
    assert result["road_classification"] == "urban"
    assert isinstance(result["nearby_facilities"], list)


@pytest.mark.asyncio
async def test_get_traffic_context_returns_default_on_error():
    tool = MapsTool(api_key="key")
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=Exception("API down"))
    with patch("tools.maps_tool.httpx.AsyncClient", return_value=mock_client):
        result = await tool.get_traffic_context(0.0, 0.0)
    assert result["traffic_density"] is None
    assert result["nearby_facilities"] == []


def test_is_within_boundary_true():
    tool = MapsTool(api_key="k", boundary={"min_lat": 18.0, "max_lat": 19.0, "min_lng": 73.0, "max_lng": 74.0})
    assert tool.is_within_boundary(18.5, 73.5) is True


def test_is_within_boundary_false():
    tool = MapsTool(api_key="k", boundary={"min_lat": 18.0, "max_lat": 19.0, "min_lng": 73.0, "max_lng": 74.0})
    assert tool.is_within_boundary(20.0, 80.0) is False


def test_is_within_boundary_no_boundary_always_true():
    tool = MapsTool(api_key="k")
    assert tool.is_within_boundary(0.0, 0.0) is True
    assert tool.is_within_boundary(90.0, 180.0) is True
