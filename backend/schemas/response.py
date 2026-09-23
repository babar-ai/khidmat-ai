from pydantic import BaseModel

from schemas.provider import ProviderSummary
from schemas.booking  import BookingRead
from schemas.trace    import TraceStep


class IntentResult(BaseModel):
    """
    Output of IntentAgent — the structured data extracted from the user's raw text.
    The MatchingAgent reads this to know what service to search for.
    """
    service_type:   str          # e.g. "ac_technician"
    location_text:  str | None   # e.g. "G-13, Islamabad"
    scheduled_text: str | None   # e.g. "kal subah" (raw, not parsed to datetime yet)
    language:       str          # e.g. "roman_ur", "ur", "en"
    confidence:     float        # 0.0 – 1.0, how confident the LLM was


class ServiceResponse(BaseModel):
    """
    The full response returned by POST /api/v1/request.

    Contains everything the mobile app needs to show the user:
      - What intent was detected
      - Which provider was matched
      - The created booking details
      - The full agent reasoning trace
      - The session ID to retrieve the trace later

    This is a NESTED schema — it composes the smaller schemas together.
    FastAPI serializes this entire object to JSON automatically.
    """
    session_id: str                          # unique ID for this pipeline run
    intent:     IntentResult                 # what the AI understood
    provider:   ProviderSummary             # the top matched provider
    booking:    BookingRead                  # the created booking
    trace:      list[TraceStep]             # step-by-step agent reasoning log
    message:    str                          # human-readable confirmation message


class ErrorResponse(BaseModel):
    """
    Standardized error shape returned on failures.
    Having a consistent error format makes it easier for the mobile app to handle errors.
    """
    error:   str        # machine-readable error code e.g. "no_providers_found"
    detail:  str        # human-readable message
    session_id: str | None = None  # included if the pipeline partially ran
