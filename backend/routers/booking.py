"""
GET  /api/v1/booking/{id}          — fetch a booking by its integer ID
PATCH /api/v1/booking/{id}/status  — update booking status (confirmed/cancelled/completed)

"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models.booking import Booking
from schemas.booking import BookingRead, BookingStatusUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Bookings"])             #"Create a group of booking-related API endpoints, put /api/v1 before all their URLs, and display them under Bookings in the API documentation. name "api/v1" is not requried or reserved keyword 


@router.get("/bookings", response_model=list[BookingRead])
def list_bookings(
    user_id: str | None = None,
    session_id: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Fetch bookings, optionally filtered by user_id or session_id."""
    query = db.query(Booking)
    if user_id:
        query = query.filter(Booking.user_id == user_id)
    if session_id:
        query = query.filter(Booking.session_id == session_id)
    return query.order_by(Booking.created_at.desc()).limit(limit).all()


@router.get("/booking/{booking_id}", response_model=BookingRead)    # here response model tells FastAPI, whatever this function returns, make sure the API response follows the BookingRead schema
def get_booking(booking_id: int, db: Session = Depends(get_db)):

    booking = db.get(Booking, booking_id)

    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found.")

    return booking

 
 
@router.patch("/booking/{booking_id}/status", response_model=BookingRead)       # Used when you want to modify only part of an existing resource.
def update_booking_status(
    booking_id: int,                                                 # Path parameter: extract from the URL path
    body: BookingStatusUpdate,                                       # Request body: Pydantic model that validates the incoming JSON payload
    db: Session = Depends(get_db),                                   # Dependency injection: provide a database session that is automatically closed after the request
):
    """Update the status of a booking (e.g. confirmed → completed or cancelled)."""
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found.")

    booking.status = body.status
    db.commit()
    db.refresh(booking)

    logger.info("Booking %d status updated to '%s'", booking_id, body.status)
    return booking
