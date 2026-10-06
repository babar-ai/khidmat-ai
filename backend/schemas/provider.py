from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.provider import ServiceCategory  # re-use the same enum


# ── Why multiple schema classes per model? ────────────────────────────────────
# Different endpoints need different "shapes" of the same data:
#   - ProviderRegister → public self-registration form (what provider fills in)
#   - ProviderCreate   → internal use by seed scripts (includes rating etc.)
#   - ProviderRead     → what the API returns (full profile)
#   - ProviderSummary  → minimal view embedded in booking responses


class ProviderRegister(BaseModel):
    """
    Public self-registration form filled by a service provider (like InDrive driver signup).

    **Location — two options (at least one required):**
    - Easy: provide `location_name` (e.g. "G-13, Islamabad") — we geocode it automatically
    - Precise: provide `latitude` + `longitude` directly

    Required fields: name, phone, city, category, CNIC, and location (name OR coords).
    Optional fields: whatsapp, description, business registration number.
    """

    # ── Business Identity ─────────────────────────────────────────────────────
    name:                str = Field(..., min_length=2, max_length=150,
                                     description="Shop or company name, e.g. 'Ali AC Services'")
    phone:               str = Field(..., min_length=7, max_length=20,
                                     description="Primary contact number")
    whatsapp_number:     str | None = Field(None, max_length=20,
                                     description="WhatsApp number (optional)")

    # ── Location — choose ONE method ──────────────────────────────────────────
    # Option A (Easy): just type the area name — we'll convert it to coordinates
    location_name:       str | None = Field(
                             None, max_length=200,
                             description="Human-readable location, e.g. 'G-13, Islamabad' or 'F-10 Markaz'. "
                                         "We will automatically convert this to coordinates.",
                             examples=["G-13, Islamabad", "F-10 Markaz", "Blue Area, Islamabad"],
                         )
    # Option B (Precise): provide exact GPS coordinates
    latitude:            float | None = Field(
                             None, ge=-90.0, le=90.0,
                             description="GPS latitude (optional if location_name is provided)",
                         )
    longitude:           float | None = Field(
                             None, ge=-180.0, le=180.0,
                             description="GPS longitude (optional if location_name is provided)",
                         )

    # ── Service ───────────────────────────────────────────────────────────────
    city:                str = Field(..., min_length=2, max_length=100,
                                     description="City where services are offered, e.g. 'Islamabad'")
    category:            ServiceCategory = Field(...,
                                     description="Service type: ac_technician, plumber, electrician, carpenter, cleaner, painter")
    description:         str | None = Field(None, max_length=500,
                                     description="Short description of experience / service area (optional)")

    # ── Verification ──────────────────────────────────────────────────────────
    cnic:                str = Field(..., min_length=13, max_length=15,
                                     description="CNIC number for identity verification, e.g. '61101-1234567-1'")
    business_reg_number: str | None = Field(None, max_length=50,
                                     description="Business registration number (optional)")

    @model_validator(mode="after")
    def check_location_provided(self) -> "ProviderRegister":
        """Ensure at least one location method is given."""
        has_coords = self.latitude is not None and self.longitude is not None
        has_name   = self.location_name is not None and self.location_name.strip() != ""

        if not has_coords and not has_name:
            raise ValueError(
                "Location is required. Provide either 'location_name' (e.g. 'G-13, Islamabad') "
                "or both 'latitude' and 'longitude'."
            )
        return self



class ProviderCreate(BaseModel):
    """Shape of data required to create a new provider (used internally by seeding scripts)."""

    name:                str
    phone:               str | None = None
    whatsapp_number:     str | None = None
    city:                str
    category:            ServiceCategory
    latitude:            float
    longitude:           float
    description:         str | None = None
    cnic:                str | None = None
    business_reg_number: str | None = None
    rating:              float = 0.0
    reviews_count:       int   = 0


class ProviderRead(BaseModel):
    """Shape returned to the API consumer when a provider is fetched."""

    id:                  int
    name:                str
    phone:               str | None
    whatsapp_number:     str | None
    city:                str
    category:            ServiceCategory
    latitude:            float
    longitude:           float
    description:         str | None
    business_reg_number: str | None
    rating:              float
    reviews_count:       int
    is_active:           bool

    # ── from_attributes ───────────────────────────────────────────────────────
    # By default Pydantic only reads from plain dicts.
    # `from_attributes=True` tells Pydantic: "also accept SQLAlchemy ORM objects"
    # This lets you do:  ProviderRead.model_validate(provider_orm_object)
    # Without this, you'd have to manually convert every ORM object to a dict first.
    model_config = ConfigDict(from_attributes=True)


class ProviderSummary(BaseModel):
    """Minimal provider info — used inside booking/response objects to avoid nesting too much."""

    id:          int
    name:        str
    city:        str
    category:    ServiceCategory
    rating:      float
    distance_km: float | None = None  # calculated by MatchingAgent, not stored in DB

    model_config = ConfigDict(from_attributes=True)

