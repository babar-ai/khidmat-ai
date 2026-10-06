"""
routers/provider.py — Provider self-registration and profile endpoints.

Like InDrive's driver signup:
  - A service provider fills in a form (POST /api/v1/provider/register)
  - They become immediately active and can start receiving orders
  - Their profile can be fetched or listed at any time
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from models.provider import Provider, ServiceCategory
from schemas.provider import ProviderRegister, ProviderRead
from utils.geocode import geocode_location

router = APIRouter(prefix="/api/v1", tags=["Providers"])


# ── POST /api/v1/provider/register ────────────────────────────────────────────
# Public endpoint — any service provider can self-register.
# No auth required at this phase (auth will be added in Phase 8).
@router.post(
    "/provider/register",
    response_model=ProviderRead,
    status_code=201,
    summary="Register as a service provider",
    description="""
Self-registration form for service providers (e.g. AC technicians, plumbers).

**Location — pick one method:**
- **Easy**: provide `location_name` (e.g. `"G-13, Islamabad"`) — we geocode it automatically
- **Precise**: provide both `latitude` and `longitude` directly

**Required fields:** `name`, `phone`, `city`, `category`, `cnic`, and one location method.

**Optional fields:** `whatsapp_number`, `description`, `business_reg_number`.

Newly registered providers are **immediately active** and eligible to receive bookings.
""",
)
def register_provider(body: ProviderRegister, db: Session = Depends(get_db)):
    # ── Step 1: Resolve location ──────────────────────────────────────────────
    # If the provider gave a location name, geocode it to lat/lng.
    # If they gave raw coordinates, use those directly.
    if body.latitude is not None and body.longitude is not None:
        # Precise coordinates provided — use as-is
        lat, lng = body.latitude, body.longitude
    else:
        # location_name provided — geocode it (schema validator guarantees one must exist)
        try:
            lat, lng = geocode_location(body.location_name)  # type: ignore[arg-type]
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # ── Step 2: Duplicate CNIC check ──────────────────────────────────────────
    # One registration per person — CNIC is the unique identity
    existing = db.query(Provider).filter(Provider.cnic == body.cnic).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A provider with CNIC '{body.cnic}' is already registered. "
                   "Contact support if you believe this is an error.",
        )

    # ── Step 3: Create provider record ────────────────────────────────────────
    # rating and reviews_count always start at 0 — not set by the provider
    provider = Provider(
        name=body.name,
        phone=body.phone,
        whatsapp_number=body.whatsapp_number,
        city=body.city,
        category=body.category,
        latitude=lat,
        longitude=lng,
        description=body.description,
        cnic=body.cnic,
        business_reg_number=body.business_reg_number,
        rating=0.0,
        reviews_count=0,
        is_active=True,  # active immediately — no approval needed
    )

    db.add(provider)
    db.commit()
    db.refresh(provider)  # reload from DB so `id` and `created_at` are populated

    return ProviderRead.model_validate(provider)


# ── GET /api/v1/provider/{id} ─────────────────────────────────────────────────
# Fetch a single provider's full profile by their ID.
@router.get(
    "/provider/{provider_id}",
    response_model=ProviderRead,
    summary="Get a provider profile by ID",
)
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider with id={provider_id} not found.")
    return ProviderRead.model_validate(provider)


# ── GET /api/v1/providers ─────────────────────────────────────────────────────
# List all active providers, with an optional filter by service category.
# Useful for browsing or for admin dashboards.
@router.get(
    "/providers",
    response_model=list[ProviderRead],
    summary="List all registered providers",
    description="Returns all active providers. Filter by `category` to narrow results.",
)
def list_providers(
    category: ServiceCategory | None = Query(
        None,
        description="Filter by service category (e.g. plumber, electrician)",
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Provider).filter(Provider.is_active == True)  # noqa: E712

    if category:
        query = query.filter(Provider.category == category)

    providers = query.order_by(Provider.rating.desc()).all()
    return [ProviderRead.model_validate(p) for p in providers]


# ── PATCH /api/v1/provider/{id}/status ────────────────────────────────────────
# Admin-only endpoint to activate or deactivate a provider.
# A deactivated provider won't appear in matching results.
@router.patch(
    "/provider/{provider_id}/status",
    response_model=ProviderRead,
    summary="Activate or deactivate a provider (admin)",
    description="Sets `is_active` to true or false. Inactive providers are excluded from booking matches.",
)
def update_provider_status(
    provider_id: int,
    is_active: bool = Query(..., description="True to activate, False to deactivate"),
    db: Session = Depends(get_db),
):
    provider = db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider with id={provider_id} not found.")

    provider.is_active = is_active
    db.commit()
    db.refresh(provider)

    status_label = "activated" if is_active else "deactivated"
    # Return updated profile — response includes the new is_active state
    return ProviderRead.model_validate(provider)
