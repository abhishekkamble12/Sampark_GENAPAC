"""
tools/maps_tool.py — Google Maps tool for geocoding, traffic context,
and boundary validation.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
_TIMEOUT = 5.0


class MapsTool:
    """Async wrapper around Google Maps APIs.

    Args:
        api_key:  Google Maps Platform API key.
        boundary: Optional ``{min_lat, max_lat, min_lng, max_lng}`` dict that
                  defines the valid geographic boundary for location validation.
    """

    def __init__(self, api_key: str, boundary: dict[str, float] | None = None) -> None:
        self._api_key = api_key
        self._boundary = boundary

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def geocode(self, location_str: str) -> dict[str, Any] | None:
        """Geocode a free-text location string to lat/lng coordinates.

        Args:
            location_str: Human-readable address or place name.

        Returns:
            Dict ``{lat, lng, address, ward_id}`` or ``None`` on failure /
            no results.  ``ward_id`` is extracted from address components
            if available, otherwise set to ``None``.
        """
        from backend.config import settings
        if not self._api_key or settings.APP_MODE == "local":
            return {"lat": 18.5204, "lng": 73.8567, "address": "MG Road, Ward 1", "ward_id": "w1"}

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    _GEOCODE_URL,
                    params={"address": location_str, "key": self._api_key},
                )
                resp.raise_for_status()
                data = resp.json()

            if data.get("status") != "OK" or not data.get("results"):
                logger.warning("Geocode returned no results for %r", location_str)
                return None

            result = data["results"][0]
            loc = result["geometry"]["location"]
            lat, lng = loc["lat"], loc["lng"]
            address = result.get("formatted_address", "")

            # Boundary check
            if not self.is_within_boundary(lat, lng):
                logger.warning(
                    "Geocoded location (%s, %s) is outside configured boundary", lat, lng
                )
                return None

            # Try to extract a ward/sublocality from address components
            ward_id: str | None = None
            for component in result.get("address_components", []):
                if "sublocality" in component.get("types", []):
                    ward_id = component.get("short_name")
                    break

            return {"lat": lat, "lng": lng, "address": address, "ward_id": ward_id}

        except Exception:
            logger.exception("geocode failed for %r", location_str)
            return None

    async def get_traffic_context(self, lat: float, lng: float) -> dict[str, Any]:
        """Retrieve traffic density and nearby facilities for a location.

        Calls the Google Places Nearby Search API to identify nearby POIs
        and infer road context.

        Args:
            lat: Latitude.
            lng: Longitude.

        Returns:
            Dict with ``traffic_density`` (low/medium/high/None),
            ``road_classification`` (string or None), and
            ``nearby_facilities`` (list of strings).
        """
        from backend.config import settings
        if not self._api_key or settings.APP_MODE == "local":
            return {
                "traffic_density": "high",
                "road_classification": "urban",
                "nearby_facilities": ["MG Road School (school)", "MG Road Market (store)"],
            }

        default: dict[str, Any] = {
            "traffic_density": None,
            "road_classification": None,
            "nearby_facilities": [],
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    _PLACES_URL,
                    params={
                        "location": f"{lat},{lng}",
                        "radius": 500,
                        "key": self._api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                return default

            facilities: list[str] = []
            for place in data.get("results", [])[:10]:
                name = place.get("name", "")
                types = place.get("types", [])
                if name:
                    facilities.append(f"{name} ({', '.join(types[:2])})")

            # Infer traffic density from number of nearby places as a proxy
            place_count = len(data.get("results", []))
            if place_count > 15:
                density = "high"
            elif place_count > 5:
                density = "medium"
            else:
                density = "low"

            return {
                "traffic_density": density,
                "road_classification": "urban" if place_count > 5 else "suburban",
                "nearby_facilities": facilities,
            }

        except Exception:
            logger.exception("get_traffic_context failed for (%s, %s)", lat, lng)
            return default

    def is_within_boundary(self, lat: float, lng: float) -> bool:
        """Check whether (lat, lng) falls within the configured boundary.

        Returns ``True`` if no boundary is configured.

        Args:
            lat: Latitude to check.
            lng: Longitude to check.
        """
        if self._boundary is None:
            return True
        b = self._boundary
        return (
            b["min_lat"] <= lat <= b["max_lat"]
            and b["min_lng"] <= lng <= b["max_lng"]
        )
