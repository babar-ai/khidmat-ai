"""
utils/geocode.py — Converts a human-readable location name to lat/lng coordinates.

Uses OpenStreetMap Nominatim via geopy with resilient AI normalization fallback.
Handles:
- Standard names: "G-13, Islamabad", "F-10 Markaz"
- Phonetic / Roman Urdu spellings: "barakaw" -> "Bhara Kahu", "banigala" -> "Bani Gala"
- Compound Pakistani addresses: "barakaw banigala islamabad"
"""

import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from services.openai_services import openai_service

logger = logging.getLogger(__name__)

# Geocoder instance
_geocoder = Nominatim(user_agent="khidmat-ai-backend", timeout=5)

# Common Islamabad/Rawalpindi fast-lookup gazetteer
PAKISTAN_GAZETTEER: dict[str, tuple[float, float]] = {
    "barakaw": (33.7381, 73.1855),
    "barakahu": (33.7381, 73.1855),
    "bhara kahu": (33.7381, 73.1855),
    "bara kahu": (33.7381, 73.1855),
    "banigala": (33.7101, 73.1536),
    "bani gala": (33.7101, 73.1536),
    "taramri": (33.6558, 73.1491),
    "tramri": (33.6558, 73.1491),
    "lehtrar": (33.6280, 73.1950),
    "pims": (33.7087, 73.0531),
    "faizabad": (33.6631, 73.0845),
    "pirwadhai": (33.6322, 73.0425),
    "sadar": (33.5973, 73.0538),
    "saddar": (33.5973, 73.0538),
    "chandni chowk": (33.6191, 73.0722),
}


def _is_valid_pakistan_coords(lat: float, lng: float) -> bool:
    """Validates if coordinates fall roughly within Pakistan's geographical bounding box."""
    return 23.5 <= lat <= 37.5 and 60.0 <= lng <= 78.5


def geocode_location(location_name: str) -> tuple[float, float]:
    """
    Convert a location name to (latitude, longitude).

    Resilient multi-tier strategy:
      1. Direct Nominatim lookup ("{query}, Pakistan")
      2. Fast local gazetteer for common phonetic Roman Urdu names
      3. AI-powered geospatial normalization (GPT-4o) resolving phonetic/compound queries
         (e.g. 'barakaw banigala islamabad' -> Bhara Kahu / Bani Gala coordinates)
    """
    clean_query = location_name.strip()
    if not clean_query:
        raise ValueError("Location name cannot be empty.")

    lower_query = clean_query.lower()

    # ── Tier 1: Direct Nominatim lookup ──────────────────────────────────────
    try:
        loc = _geocoder.geocode(f"{clean_query}, Pakistan")
        if loc and _is_valid_pakistan_coords(loc.latitude, loc.longitude):
            logger.info("Geocoded '%s' via direct Nominatim: (%f, %f)", clean_query, loc.latitude, loc.longitude)
            return (loc.latitude, loc.longitude)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning("Nominatim direct lookup failed or timed out for '%s': %s", clean_query, e)

    # ── Tier 2: Check fast Pakistani gazetteer ────────────────────────────────
    for key, coords in PAKISTAN_GAZETTEER.items():
        if key in lower_query:
            logger.info("Geocoded '%s' via local gazetteer match '%s': %s", clean_query, key, coords)
            return coords

    # ── Tier 3: AI-Assisted Geospatial Normalization ──────────────────────────
    logger.info("Direct geocode failed for '%s'. Invoking AI normalizer...", clean_query)
    try:
        prompt = (
            "You are an expert Pakistani geospatial assistant for Islamabad, Rawalpindi, and Pakistan. "
            "The user provided an address or area name that failed strict map lookup, "
            "often because of phonetic Roman Urdu spelling (e.g. 'barakaw' for Bhara Kahu, 'banigala' for Bani Gala) "
            "or compound descriptions (e.g. 'barakaw banigala islamabad').\n"
            "Identify the primary intended locality in Pakistan and return valid JSON:\n"
            "{\n"
            '  "canonical_name": "Standard clean place name (e.g. Bhara Kahu, Islamabad)",\n'
            '  "latitude": float,\n'
            '  "longitude": float,\n'
            '  "found": true\n'
            "}"
        )
        ai_res = openai_service.extract_structured_json(prompt, clean_query)
        if ai_res.get("found"):
            canonical = ai_res.get("canonical_name", "").strip()

            # Try geocoding the AI's canonical clean name with Nominatim
            if canonical:
                try:
                    loc = _geocoder.geocode(f"{canonical}, Pakistan")
                    if loc and _is_valid_pakistan_coords(loc.latitude, loc.longitude):
                        logger.info("Geocoded '%s' via AI canonical name '%s': (%f, %f)", clean_query, canonical, loc.latitude, loc.longitude)
                        return (loc.latitude, loc.longitude)
                except Exception as ex:
                    logger.warning("Nominatim canonical lookup error: %s", ex)

            # If Nominatim is unavailable or misses the canonical name, use AI coordinates if valid
            lat = ai_res.get("latitude")
            lng = ai_res.get("longitude")
            if lat is not None and lng is not None and _is_valid_pakistan_coords(float(lat), float(lng)):
                logger.info("Geocoded '%s' using AI coordinates directly: (%f, %f)", clean_query, lat, lng)
                return (float(lat), float(lng))
    except Exception as err:
        logger.error("AI geocode normalization error for '%s': %s", clean_query, err)

    # ── Tier 4: Fallback failure ──────────────────────────────────────────────
    raise ValueError(
        f"Could not find '{clean_query}' on the map. "
        "Please provide a sector name (e.g. 'G-13, Islamabad', 'Bani Gala', 'F-10 Markaz') "
        "or enable GPS location."
    )

