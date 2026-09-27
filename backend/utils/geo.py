"""
Geospatial utilities for Khidmat AI.

Provides:
  - Haversine great-circle distance calculator
  - Nominatim geocoder (free, no API key, OpenStreetMap-based)
"""

import logging
import math

import httpx

logger = logging.getLogger(__name__)

# Nominatim usage policy: must set a meaningful User-Agent header
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "KhidmatAI/1.0 (github.com/babar-ai/khidmat-ai)"}
NOMINATIM_TIMEOUT = 5.0  # seconds


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the Great Circle distance in kilometers between two GPS coordinates
    using the Haversine formula.
    """
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def geocode_address(location_text: str) -> tuple[float, float] | None:
    """
    Converts a free-text address or area name into GPS coordinates using the
    OpenStreetMap Nominatim API (100% free, no API key, no billing required).

    Bias strategy:
      - Appends 'Pakistan' to the query to avoid ambiguous global matches.
      - Restricts results to countrycodes=pk (Pakistan only).

    Returns:
      (latitude, longitude) tuple on success, or None if not found / on error.

    Usage examples:
      geocode_address("G-9/3 Street 4")          → (33.6988, 73.0163)
      geocode_address("Bani Gala near Malik House") → (33.7025, 73.1584)
      geocode_address("DHA Phase 6, Lahore")      → (31.4667, 74.4169)

    Note:
      Nominatim has a 1 request/second rate limit per its Usage Policy.
      For MVP scale this is fine. For production, migrate to Google Maps API.
    """
    if not location_text or not location_text.strip():
        return None

    query = f"{location_text.strip()}, Pakistan"

    try:
        with httpx.Client(timeout=NOMINATIM_TIMEOUT) as client:
            resp = client.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "pk",
                    "addressdetails": 0,
                },
                headers=NOMINATIM_HEADERS,
            )
            resp.raise_for_status()
            results = resp.json()

        if results:
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            logger.info(
                "Geocoded '%s' → (%.5f, %.5f) via Nominatim",
                location_text,
                lat,
                lon,
            )
            return lat, lon

        logger.warning("Nominatim returned no results for: '%s'", location_text)
        return None

    except httpx.TimeoutException:
        logger.warning("Nominatim geocoding timed out for: '%s'", location_text)
        return None
    except Exception as e:
        logger.error("Geocoding error for '%s': %s", location_text, str(e))
        return None
