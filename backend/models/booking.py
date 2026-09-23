import enum
import uuid
from datetime import datetime

# pyrefly: ignore [missing-import]
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


# ── Booking Status Enum ───────────────────────────────────────────────────────
class BookingStatus(str, enum.Enum):
    PENDING   = "pending"    # created but not yet confirmed
    CONFIRMED = "confirmed"  # provider accepted
    COMPLETED = "completed"  # service was delivered
    CANCELLED = "cancelled"  # user or provider cancelled


# ── Booking Model ─────────────────────────────────────────────────────────────
class Booking(Base):

    __tablename__ = "bookings"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ── Session & User IDs ────────────────────────────────────────────────────
    # session_id ties a booking to a full agent trace (one pipeline run = one session)
    # We generate it as a UUID string so it's globally unique and safe to expose in URLs
    session_id: Mapped[str] = mapped_column(
        String(36),
        default=lambda: str(uuid.uuid4()),  # auto-generate on Python side
        index=True,
    )

    # user_id comes from the mobile app (we don't have a users table yet — plain string for now)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # ── Foreign Key ───────────────────────────────────────────────────────────
    # ForeignKey("providers.id") tells PostgreSQL:
    #   "this column MUST match an existing id in the providers table"
    # If you try to create a booking for a provider that doesn't exist → DB rejects it
    # If you try to delete a provider that has bookings → DB rejects it (referential integrity)
    provider_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("providers.id"),
        nullable=False,
    )

    # ── Relationship (ORM-level, not a DB column) ─────────────────────────────
    # `relationship` lets you do: booking.provider.name instead of a second query
    # It's a Python-only concept — no extra column is created in the DB
    # "back_populates" would go on Provider side if we add provider.bookings later
    provider: Mapped["Provider"] = relationship("Provider")  # type: ignore[name-defined]

    # ── Request Details ───────────────────────────────────────────────────────
    service_type:  Mapped[str] = mapped_column(String(100), nullable=False)
    location_text: Mapped[str] = mapped_column(String(255), nullable=True)  # e.g. "G-13, Islamabad"
    scheduled_at:  Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # ── Booking Code ──────────────────────────────────────────────────────────
    # A short human-readable code shown to the user (e.g. "XY4F9K2A")
    booking_code: Mapped[str] = mapped_column(String(20), nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="bookingstatus"),
        default=BookingStatus.PENDING,
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),  # auto-updates whenever this row is modified
    )

    def __repr__(self) -> str:
        return f"<Booking id={self.id} code={self.booking_code!r} status={self.status}>"
