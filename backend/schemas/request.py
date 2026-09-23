from pydantic import BaseModel, Field


class ServiceRequest(BaseModel):
    """
    The body of POST /api/v1/request — the app's main entry point.

    The mobile app sends this when a user types a natural language request.
    FastAPI automatically:
      1. Reads the JSON body
      2. Validates it against this schema
      3. Raises HTTP 422 if required fields are missing or wrong type
      4. Passes the validated object to the route function

    Example JSON body:
        {
            "text": "Mujhe kal subah G-13 mein AC technician chahiye",
            "user_id": "user_abc123",
            "user_lat": 33.6844,
            "user_lng": 73.0479
        }
    """

    # The raw user message — Urdu, Roman Urdu, or English
    # Field(min_length=3) → FastAPI rejects requests shorter than 3 chars with a 422 error
    text: str = Field(..., min_length=3, max_length=500, description="User's natural language request")

    # Identifies who is making the request (from the mobile app session)
    user_id: str = Field(..., description="Unique user identifier from the mobile app")

    # Optional — user's current GPS location for distance-based provider ranking
    # If not provided, the MatchingAgent falls back to city-only matching
    user_lat: float | None = Field(None, ge=-90,  le=90,  description="User latitude")
    user_lng: float | None = Field(None, ge=-180, le=180, description="User longitude")
