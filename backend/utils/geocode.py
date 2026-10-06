"""
utils/geocode.py — Converts a human-readable location name to lat/lng coordinates.

Uses OpenStreetMap Nominatim via the geopy library.
- FREE — no API key required
- Works well for Pakistani cities and sector names (e.g. "G-13, Islamabad")
- Rate limit: 1 request/second (fine for registration flow)
"""

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


# ── Geocoder instance ─────────────────────────────────────────────────────────
# user_agent is required by Nominatim's usage policy — identify your app.
_geocoder = Nominatim(user_agent="khidmat-ai-backend", timeout=5)


def geocode_location(location_name: str) -> tuple[float, float]:
    """
    Convert a location name to (latitude, longitude).

    Examples:
        geocode_location("G-13, Islamabad")     → (33.6920, 73.0570)
        geocode_location("F-10 Markaz")         → (33.7040, 73.0261)
        geocode_location("Blue Area Islamabad") → (33.7215, 73.0433)

    Raises:
        ValueError: if the location cannot be found or the service is unavailable.
    """
    # Append ", Pakistan" to bias results toward Pakistan
    # This prevents "G-13" from resolving to a random place in another country.
    query = f"{location_name}, Pakistan"

    try:
        location = _geocoder.geocode(query)
    except GeocoderTimedOut:
        raise ValueError(
            f"Geocoding timed out for '{location_name}'. Please try again or enter coordinates manually."
        )
    except GeocoderServiceError as e:
        raise ValueError(
            f"Geocoding service unavailable: {e}. Please try again later."
        )

    if location is None:
        raise ValueError(
            f"Could not find '{location_name}' on the map. "
            "Please be more specific (e.g. 'G-13, Islamabad' or 'F-10 Markaz, Islamabad')."
        )

    return (location.latitude, location.longitude)
