from pydantic import BaseModel, ConfigDict

from models.provider import ServiceCategory  # re-use the same enum


# ── Why multiple schema classes per model? ────────────────────────────────────
# Different endpoints need different "shapes" of the same data:
#   - ProviderCreate  → what you send to CREATE a provider (no id, no created_at)
#   - ProviderRead    → what you GET back (includes id, created_at)
#
# Keeping them separate = you never accidentally expose or accept wrong fields.


class ProviderCreate(BaseModel):
    """Shape of data required to create a new provider (used internally by seeding scripts)."""

    name:          str
    phone:         str | None = None
    city:          str
    category:      ServiceCategory
    latitude:      float
    longitude:     float
    rating:        float = 0.0
    reviews_count: int   = 0


class ProviderRead(BaseModel):
    """Shape returned to the API consumer when a provider is fetched."""

    id:            int
    name:          str
    phone:         str | None
    city:          str
    category:      ServiceCategory
    latitude:      float
    longitude:     float
    rating:        float
    reviews_count: int
    is_active:     bool

    # ── from_attributes ───────────────────────────────────────────────────────
    # By default Pydantic only reads from plain dicts.
    # `from_attributes=True` tells Pydantic: "also accept SQLAlchemy ORM objects"
    # This lets you do:  ProviderRead.model_validate(provider_orm_object)
    # Without this, you'd have to manually convert every ORM object to a dict first.
    model_config = ConfigDict(from_attributes=True)


class ProviderSummary(BaseModel):
    """Minimal provider info — used inside booking/response objects to avoid nesting too much."""

    id:       int
    name:     str
    city:     str
    category: ServiceCategory
    rating:   float
    distance_km: float | None = None  # calculated by MatchingAgent, not stored in DB

    model_config = ConfigDict(from_attributes=True)
