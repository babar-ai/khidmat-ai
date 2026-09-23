from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TraceStep(BaseModel):
    """
    Represents one agent's execution log within a pipeline run.
    This is NOT a DB model — it's a Python object that gets serialized
    into the JSON `steps` column of the Trace table.

    Example:
        TraceStep(
            step=1,
            agent="IntentAgent",
            action="extract_intent",
            input_summary="Raw text (42 chars)",
            output_summary="service=plumber | location=F-7 | lang=roman_ur",
            duration_ms=312,
        )
    """
    step:           int
    agent:          str               # e.g. "IntentAgent"
    action:         str               # e.g. "extract_intent"
    input_summary:  str | None = None
    output_summary: str | None = None
    duration_ms:    int | None = None  # how long this agent took


class TraceRead(BaseModel):
    """
    Returned by GET /api/v1/trace/{session_id}.
    Contains the full list of TraceStep objects for one pipeline run.
    """
    session_id:          str
    steps:               list[TraceStep]  # Pydantic parses the raw JSON list into TraceStep objects
    final_service_type:  str | None
    final_provider_name: str | None
    created_at:          datetime

    model_config = ConfigDict(from_attributes=True)
