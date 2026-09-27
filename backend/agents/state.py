"""
State definition for the Khidmat AI multi-agent LangGraph workflow.

The KhidmatState TypedDict serves as the single source of truth passed
between nodes in the LangGraph execution graph:
  - Input fields populated by the API endpoint before invocation
  - Intermediate fields populated by individual agent nodes
  - Trace steps accumulated throughout the pipeline run
  - Error fields populated if validation or execution fails
"""

from typing import Any, TypedDict


class KhidmatState(TypedDict):
    """
    Central state dictionary flowing through the LangGraph pipeline.

    Nodes read from and return updates to this state.
    """

    # ── Initial Request Inputs (Set by POST /api/v1/request) ─────────────────
    request_text: str
    """Raw natural language text provided by the user (Urdu, Roman Urdu, English)."""

    user_id: str
    """Unique identifier for the user initiating the request."""

    user_lat: float | None
    """Latitude coordinates of the user for proximity ranking, if available."""

    user_lng: float | None
    """Longitude coordinates of the user for proximity ranking, if available."""

    session_id: str
    """UUID4 string uniquely identifying this request lifecycle and trace log."""

    # ── Agent Node Outputs ───────────────────────────────────────────────────
    intent: dict[str, Any] | None
    """
    Output from IntentAgent (intent_node).
    Matches the shape of schemas.response.IntentResult:
      - service_type: str (e.g., 'ac_technician')
      - location_text: str | None
      - scheduled_text: str | None
      - language: str ('ur', 'roman_ur', 'en')
      - confidence: float (0.0 - 1.0)
    """

    providers: list[dict[str, Any]]
    """
    Output from MatchingAgent (matching_node).
    Ranked list of matching providers, each following schemas.provider.ProviderSummary:
      - id: int
      - name: str
      - city: str
      - category: str
      - rating: float
      - distance_km: float | None
    """

    booking: dict[str, Any] | None
    """
    Output from BookingAgent (booking_node).
    Matches schemas.booking.BookingRead:
      - id: int
      - session_id: str
      - user_id: str
      - provider_id: int
      - service_type: str
      - location_text: str | None
      - booking_code: str
      - status: str
      - created_at: str | datetime
      - updated_at: str | datetime
    """

    # ── Reasoning Audit & Error Handling ─────────────────────────────────────
    trace_steps: list[dict[str, Any]]
    """
    Accumulated audit trace steps representing each agent node's execution.
    Each item conforms to schemas.trace.TraceStep:
      - step: int
      - agent: str
      - action: str
      - input_summary: str | None
      - output_summary: str | None
      - duration_ms: int | None
    """

    error: str | None
    """Error message or code if pipeline routing or execution encounters a failure."""
