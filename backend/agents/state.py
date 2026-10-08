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

    # ── Conversational Context & Slot Filling (Persisted in Postgres) ────────
    chat_history: list[dict[str, str]]
    """Cumulative message turns for this thread: [{'role': 'user'|'assistant', 'content': '...'}]"""

    missing_slots: list[str]
    """Slots still needed before booking can proceed (e.g. ['location', 'timing'])."""

    followup_question: str | None
    """Targeted question to ask the user if missing_slots is not empty."""

    is_ready_to_book: bool
    """True when all necessary slots (service, location, timing) are satisfied."""

    # ── Post-Recommendation Conversational State ──────────────────────────────
    dialogue_act: str | None
    """
    Classifies what the user is doing in a post-recommendation turn:
      - 'slot_filling'         — still collecting service / location / timing
      - 'objection_distance'   — "too far away", "door hai"
      - 'objection_price'      — "too expensive", "mehenga hai"
      - 'request_alternative'  — "show someone else", "koi aur dikhao"
      - 'general_query'        — asking a question about the provider / service
      - 'booking_confirmed'    — "yes book him", "theek hai", "confirm kar do"
      - 'booking_cancelled'    — "no cancel", "rehne do"
      - 'reschedule_requested' — "change date to 9 oct", "reschedule to 5 pm"
    """

    booking_confirmation_pending: bool
    """
    True when a provider is selected/proposed and human confirmation is required
    before booking_node is allowed to execute the database mutation.
    """

    new_scheduled_text: str | None
    """Holds the updated schedule text when a user reschedules an existing booking."""

    proposed_providers: list[dict[str, Any]]
    """
    Full ranked list of providers returned by MatchingAgent for the current
    booking intent. Persisted so objection turns can serve the next provider
    without re-querying the database.
    """

    active_provider_index: int
    """
    Index into proposed_providers currently being presented to the user.
    Starts at 0 (top recommendation), increments on 'request_alternative'.
    """

    rejected_provider_ids: list[int]
    """
    Provider IDs the user has explicitly rejected in this session.
    MatchingAgent filters these out when running a fresh search.
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

