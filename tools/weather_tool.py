"""
tools/weather_tool.py — OpenWeatherMap weather tool for the Sampark AI Platform.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_OWM_ONE_CALL_URL = "https://api.openweathermap.org/data/3.0/onecall"
_TIMEOUT = 5.0

_ERROR_RESPONSE: dict[str, Any] = {
    "current": None,
    "hourly_48h": [],
    "rainfall_forecast_48h": 0.0,
}


class WeatherTool:
    """Async wrapper around the OpenWeatherMap One Call API 3.0.

    Args:
        api_key: OpenWeatherMap API key.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def get_current_and_forecast(
        self, lat: float, lng: float
    ) -> dict[str, Any]:
        """Fetch current weather and 48-hour hourly forecast.

        Args:
            lat: Latitude.
            lng: Longitude.

        Returns:
            Dict with keys:

            * ``current``: ``{temp, feels_like, humidity, weather_description,
              wind_speed, rain_1h}``
            * ``hourly_48h``: list of up to 48 hourly dicts ``{dt, temp,
              humidity, weather_description, rain_1h, pop}``
            * ``rainfall_forecast_48h``: total rainfall over the 48h window
              in mm (float)

            Returns ``{"current": None, "hourly_48h": [], "rainfall_forecast_48h": 0.0}``
            on any error.
        """
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    _OWM_ONE_CALL_URL,
                    params={
                        "lat": lat,
                        "lon": lng,
                        "appid": self._api_key,
                        "units": "metric",
                        "exclude": "minutely,alerts",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            current_raw = data.get("current", {})
            weather_list = current_raw.get("weather", [{}])
            current = {
                "temp": current_raw.get("temp"),
                "feels_like": current_raw.get("feels_like"),
                "humidity": current_raw.get("humidity"),
                "weather_description": weather_list[0].get("description") if weather_list else None,
                "wind_speed": current_raw.get("wind_speed"),
                "rain_1h": current_raw.get("rain", {}).get("1h", 0.0),
            }

            hourly_raw = data.get("hourly", [])[:48]
            hourly_48h: list[dict[str, Any]] = []
            total_rain = 0.0

            for h in hourly_raw:
                rain_1h = h.get("rain", {}).get("1h", 0.0)
                total_rain += rain_1h
                hw = h.get("weather", [{}])
                hourly_48h.append({
                    "dt": h.get("dt"),
                    "temp": h.get("temp"),
                    "humidity": h.get("humidity"),
                    "weather_description": hw[0].get("description") if hw else None,
                    "rain_1h": rain_1h,
                    "pop": h.get("pop", 0.0),
                })

            return {
                "current": current,
                "hourly_48h": hourly_48h,
                "rainfall_forecast_48h": round(total_rain, 2),
            }

        except Exception:
            logger.exception("get_current_and_forecast failed for (%s, %s)", lat, lng)
            return dict(_ERROR_RESPONSE)
