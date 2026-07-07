"""Unit tests for tools/weather_tool.py."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from tools.weather_tool import WeatherTool

API_KEY = "test-weather-key"

@pytest.fixture(autouse=True)
def _patch_app_mode():
    with patch("backend.config.settings.APP_MODE", "production"):
        yield


def _make_owm_response(hourly_count: int = 2) -> dict:
    hourly = []
    for i in range(hourly_count):
        hourly.append({
            "dt": 1700000000 + i * 3600,
            "temp": 28.0 + i,
            "humidity": 70,
            "weather": [{"description": "light rain"}],
            "rain": {"1h": 1.5},
            "pop": 0.8,
        })
    return {
        "current": {
            "temp": 30.0,
            "feels_like": 33.0,
            "humidity": 80,
            "weather": [{"description": "overcast clouds"}],
            "wind_speed": 5.2,
            "rain": {"1h": 0.5},
        },
        "hourly": hourly,
    }


@pytest.mark.asyncio
async def test_get_current_and_forecast_success():
    tool = WeatherTool(api_key=API_KEY)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _make_owm_response(hourly_count=2)

    with patch("tools.weather_tool.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await tool.get_current_and_forecast(18.52, 73.86)

    assert result["current"] is not None
    assert result["current"]["temp"] == 30.0
    assert result["current"]["weather_description"] == "overcast clouds"
    assert len(result["hourly_48h"]) == 2
    assert result["rainfall_forecast_48h"] == pytest.approx(3.0)  # 2 * 1.5


@pytest.mark.asyncio
async def test_get_current_and_forecast_http_error_returns_default():
    tool = WeatherTool(api_key=API_KEY)
    with patch("tools.weather_tool.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("timeout"))
        mock_client_cls.return_value = mock_client

        result = await tool.get_current_and_forecast(18.52, 73.86)

    assert result["current"] is None
    assert result["hourly_48h"] == []
    assert result["rainfall_forecast_48h"] == 0.0


@pytest.mark.asyncio
async def test_get_current_no_rain_field():
    """If 'rain' key is absent, rain_1h defaults to 0.0."""
    tool = WeatherTool(api_key=API_KEY)
    response = _make_owm_response(hourly_count=1)
    del response["current"]["rain"]
    response["hourly"][0].pop("rain", None)

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = response

    with patch("tools.weather_tool.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await tool.get_current_and_forecast(0.0, 0.0)

    assert result["current"]["rain_1h"] == 0.0
    assert result["rainfall_forecast_48h"] == 0.0


@pytest.mark.asyncio
async def test_hourly_capped_at_48():
    """Hourly list is capped at 48 entries even if API returns more."""
    tool = WeatherTool(api_key=API_KEY)
    response = _make_owm_response(hourly_count=60)  # 60 entries from API

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = response

    with patch("tools.weather_tool.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await tool.get_current_and_forecast(0.0, 0.0)

    assert len(result["hourly_48h"]) == 48
