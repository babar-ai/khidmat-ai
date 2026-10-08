"""
POST /api/v1/request — Main pipeline endpoint.

Receives a natural language service request from the mobile app,
runs it through the LangGraph agent pipeline (Intent → Matching → Booking),
and returns the full result.

The client sends a service request → FastAPI validates it → LangGraph processes
 it → agents find a provider and create a booking → FastAPI returns a structured response.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from schemas.request import ServiceRequest
from schemas.response import IntentResult, ServiceResponse, ErrorResponse
from schemas.provider import ProviderSummary
from schemas.booking import BookingRead
from schemas.trace import TraceStep
from services.langgraph_services import langgraph_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Request"])


@router.post(
    "/request",
    response_model=ServiceResponse,
    responses={400: {"model": ErrorResponse}},
)
def handle_request(body: ServiceRequest):
    """
    Main entry point — runs the conversational LangGraph agent pipeline.

    1. Chatting / Clarification: If the user sends a greeting or missing details,
       the agent returns a follow-up question.
    2. Booking Confirmation: Once all required details (service, location, time)
       are collected, the agent matches the best provider and creates the booking.
    """
    print(f"📥 [REQUEST] User: '{body.user_id}' | Text: '{body.text}'")

    # 1. Run the LangGraph agent pipeline (State persisted in PostgreSQL)
    result = langgraph_service.run_pipeline(
        request_text=body.text,
        user_id=body.user_id,
        user_lat=body.user_lat,
        user_lng=body.user_lng,
        session_id=body.session_id,
    )

    session_id = result.get("session_id") or body.session_id
    intent_data = result.get("intent") or {}
    proposed_providers = result.get("proposed_providers") or result.get("providers") or []
    active_idx = result.get("active_provider_index", 0)
    top_provider = (
        proposed_providers[active_idx]
        if 0 <= active_idx < len(proposed_providers)
        else (proposed_providers[0] if proposed_providers else None)
    )
    booking = result.get("booking")
    dialogue_act = result.get("dialogue_act")

    # 1. Case A: Initial slot collection (missing slots, greeting, or error without providers)
    if (not top_provider and not booking) or result.get("error"):
        question = (
            result.get("followup_question")
            or intent_data.get("followup_question")
            or result.get("error")
            or "Could you please provide a few more details so I can match you with the right provider?"
        )
        for prefix in ("AWAITING_INPUT: ", "GREETING: ", "CONVERSATION: "):
            if str(question).startswith(prefix):
                question = str(question)[len(prefix):]

        is_greeting = intent_data.get("is_greeting", False)
        error_type = "conversation" if dialogue_act else ("greeting" if is_greeting else "awaiting_input")

        detail_payload = {
            "message": question,
            "session_id": session_id,
            "partial_intent": intent_data,
            "missing_slots": intent_data.get("missing_slots", []),
            "is_greeting": is_greeting,
            "dialogue_act": dialogue_act,
            "booking_confirmation_pending": bool(result.get("booking_confirmation_pending", False)),
            "error": error_type,
            "proposed_providers": proposed_providers,
            "active_provider_index": active_idx,
        }
        if top_provider:
            detail_payload["provider"] = top_provider
        if result.get("booking"):
            detail_payload["booking"] = result["booking"]
        if result.get("new_scheduled_text"):
            detail_payload["new_scheduled_text"] = result["new_scheduled_text"]

        print(f"💬 [CLARIFICATION / DIALOGUE] '{question}' (act: {dialogue_act}, session: {session_id})")
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(detail_payload),
        )

    # 2. Case B: Provider matched and proposed (awaiting explicit human confirmation)
    if top_provider and not booking:
        recommendation_msg = (
            result.get("followup_question")
            or "Here's the best matched provider based on distance, reviews, rating, and availability:"
        )
        for prefix in ("CONVERSATION: ",):
            if str(recommendation_msg).startswith(prefix):
                recommendation_msg = str(recommendation_msg)[len(prefix):]

        print(f"🎯 [PROVIDER PROPOSED] {top_provider['name']} (session: {session_id})")
        return ServiceResponse(
            session_id=session_id,
            intent=IntentResult(**intent_data),
            provider=ProviderSummary(**top_provider),
            booking=None,
            trace=[TraceStep(**s) for s in (result.get("trace_steps") or [])],
            message=recommendation_msg,
            booking_confirmation_pending=bool(result.get("booking_confirmation_pending", False)),
        )

    # 3. Case C: Explicit human confirmation received -> Booking is created!
    if booking and top_provider:
        print(f"✅ [BOOKED] Provider: {top_provider['name']} | Code: {booking['booking_code']}")

        lang = intent_data.get("language") or "roman_ur"
        reply_msg = result.get("followup_question")
        if reply_msg and any(w in reply_msg.lower() for w in ["booking", "confirm", "rabta", "raabta", "shukriya", "zabardast", "کامیاب", "بکنگ"]):
            confirmation_msg = f"{reply_msg}\nBooking Code: {booking['booking_code']}"
        elif lang == "ur":
            confirmation_msg = (
                f"✅ بکنگ کنفرم ہو گئی ہے! {top_provider['name']} جلد آپ کے پاس پہنچے گا۔ "
                f"آپ کا بکنگ کوڈ ہے: {booking['booking_code']}۔"
            )
        elif lang == "roman_ur":
            confirmation_msg = (
                f"✅ Booking confirm ho gayi! {top_provider['name']} jald aap se rabta karega. "
                f"Aap ka booking code hai: {booking['booking_code']}."
            )
        else:
            confirmation_msg = (
                f"✅ Booking confirmed! {top_provider['name']} will be with you soon. "
                f"Your booking code is {booking['booking_code']}."
            )

        return ServiceResponse(
            session_id=session_id,
            intent=IntentResult(**intent_data),
            provider=ProviderSummary(**top_provider),
            booking=BookingRead(**booking),
            trace=[TraceStep(**s) for s in (result.get("trace_steps") or [])],
            message=confirmation_msg,
        )

