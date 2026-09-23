from datetime import datetime

from sqlalchemy import String, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


# ── Trace Model ───────────────────────────────────────────────────────────────
# One trace = the full reasoning log for one user request pipeline.
# It stores an array of step objects (IntentAgent, MatchingAgent, BookingAgent).
#
# Example of what `steps` JSON looks like:
# [
#   {"step": 1, "agent": "IntentAgent",   "action": "extract_intent",         "duration_ms": 312},
#   {"step": 2, "agent": "MatchingAgent", "action": "find_and_rank_providers", "duration_ms": 87},
#   {"step": 3, "agent": "BookingAgent",  "action": "create_booking",          "duration_ms": 45}
# ]
class Trace(Base):

    __tablename__ = "traces"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ── Session ID ────────────────────────────────────────────────────────────
    # Links this trace to a booking (same session_id is shared across both).
    # Exposed in the /api/v1/trace/{session_id} endpoint.
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, unique=True)

    # ── Agent Steps (JSON) ────────────────────────────────────────────────────
    # JSON column stores arbitrary nested Python dicts/lists directly in PostgreSQL.
    # SQLAlchemy serializes the Python list to JSON on write and deserializes on read.
    # No need to define a separate TraceStep table — the structure is flexible enough
    # that a JSON column is simpler and more appropriate here.
    steps: Mapped[list] = mapped_column(JSON, default=list)

    # ── Summary Snapshot ──────────────────────────────────────────────────────
    # A quick human-readable summary stored separately for fast retrieval
    # without parsing the full JSON steps array.
    final_service_type: Mapped[str] = mapped_column(String(100), nullable=True)
    final_provider_name: Mapped[str] = mapped_column(String(150), nullable=True)

    # ── Timestamp ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Trace session={self.session_id!r} steps={len(self.steps or [])}>"

