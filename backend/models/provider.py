import enum
from datetime import datetime

# pyrefly: ignore [missing-import]
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Enum as SAEnum, func
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


# ── Category Enum ─────────────────────────────────────────────────────────────
# An Enum restricts a column to a fixed set of allowed values.
# SQLAlchemy stores this as a VARCHAR with a CHECK constraint in PostgreSQL.
# Using an enum (instead of a plain string) prevents typos like "Ac_tech" vs "ac_technician".

class ServiceCategory(str, enum.Enum):
    AC_TECHNICIAN   = "ac_technician"
    PLUMBER         = "plumber"
    ELECTRICIAN     = "electrician"
    CARPENTER       = "carpenter"
    CLEANER         = "cleaner"
    PAINTER         = "painter"


# ── Provider Model ────────────────────────────────────────────────────────────
# Inheriting from Base registers this class with SQLAlchemy's metadata.
# Alembic reads Base.metadata to discover which tables to create/migrate.
class Provider(Base):

    __tablename__ = "providers"   # the actual table name in PostgreSQL

    # ── Primary Key ───────────────────────────────────────────────────────────
    # `Mapped[int]` is the modern SQLAlchemy 2.0 style for declaring column types.
    # It tells Python's type checker the column holds an int.
    # `primary_key=True` → auto-increments, unique, never null
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ── Basic Info ────────────────────────────────────────────────────────────
    # String(100) = VARCHAR(100) in SQL — max 100 characters
    # nullable=False means this column cannot be empty in the DB
    name:  Mapped[str]  = mapped_column(String(150), nullable=False)
    phone: Mapped[str] =  mapped_column(String(20),  nullable=True)
    city:  Mapped[str]  = mapped_column(String(100), nullable=False)

    # ── Service Category ──────────────────────────────────────────────────────
    # SAEnum wraps our Python enum so PostgreSQL enforces the allowed values
    category: Mapped[ServiceCategory] = mapped_column(
        SAEnum(ServiceCategory, name="servicecategory"),
        nullable=False,
        index=True,   # we'll filter by category often → index speeds that up
    )

    # ── Location ──────────────────────────────────────────────────────────────
    # We store lat/lng as plain floats for simplicity.
    # PostGIS spatial queries (ST_DWithin etc.) can be added later via raw SQL.
    latitude:  Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Ranking Signals ───────────────────────────────────────────────────────
    # Used by the MatchingAgent to score providers:
    # final_score = (distance * 0.40) + (rating * 0.40) + (reviews * 0.20)
    rating:        Mapped[float] = mapped_column(Float, default=0.0)
    reviews_count: Mapped[int]   = mapped_column(Integer, default=0)

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    # func.now() calls PostgreSQL's NOW() — the DB sets this, not Python.
    # This is safer than datetime.utcnow() because it uses the DB server's clock.
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Provider id={self.id} name={self.name!r} category={self.category}>"
