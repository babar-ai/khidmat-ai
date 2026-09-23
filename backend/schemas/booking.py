from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.booking import BookingStatus


class BookingCreate(BaseModel):
    """
    Data needed to create a booking.
    Called internally by BookingAgent — not exposed as a user-facing endpoint body.
    """
    session_id:    str
    user_id:       str
    provider_id:   int
    service_type:  str
    location_text: str | None = None
    scheduled_at:  datetime | None = None
    booking_code:  str | None = None


class BookingRead(BaseModel):
    """
    Full booking details returned by GET /api/v1/booking/{id}.
    Includes all fields including timestamps.
    """
    id:            int
    session_id:    str
    user_id:       str
    provider_id:   int
    service_type:  str
    location_text: str | None
    scheduled_at:  datetime | None
    booking_code:  str | None
    status:        BookingStatus
    created_at:    datetime
    updated_at:    datetime

    model_config = ConfigDict(from_attributes=True)


class BookingStatusUpdate(BaseModel):
    """
    Body for PATCH /api/v1/booking/{id}/status.
    The user (or provider) can only change the status field — nothing else.
    Having a dedicated schema prevents accidentally updating other fields.
    """
    status: BookingStatus
