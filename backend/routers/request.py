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

    # 2. Case A: Still chatting (Greeting, question, missing slots, or conversational objection/query)
    if not result.get("is_ready_to_book") or not result.get("booking"):

        question = ( 
            result.get("followup_question")
            or intent_data.get("followup_question")
            or result.get("error")
            or "Could you please provide a few more details so I can match you with the right provider?"
        )
        # Strip internal debug prefixes if present
        for prefix in ("AWAITING_INPUT: ", "GREETING: ", "CONVERSATION: "):

            if str(question).startswith(prefix):
                question = str(question)[len(prefix):]

        dialogue_act = result.get("dialogue_act")
        is_greeting = intent_data.get("is_greeting", False)

        error_type = ( "conversation" if dialogue_act else ("greeting" if is_greeting else "awaiting_input"))

        proposed_providers = result.get("proposed_providers") or []
        active_idx = result.get("active_provider_index", 0)

        current_provider = (
            proposed_providers[active_idx]
            if 0 <= active_idx < len(proposed_providers)
            else None
        )

        detail_payload = {
            "message": question,
            "session_id": session_id,
            "missing_slots": intent_data.get("missing_slots", []),
            "is_greeting": is_greeting,
            "dialogue_act": dialogue_act,
            "error": error_type,
            "proposed_providers": proposed_providers,
            "active_provider_index": active_idx,
        }
        if current_provider:
            detail_payload["provider"] = current_provider

        print(f"💬 [CLARIFICATION / DIALOGUE] '{question}' (act: {dialogue_act}, session: {session_id})")
        raise HTTPException(
            status_code=400,
            detail=detail_payload,
        )

    # 3. Case B: All details provided -> Booking is confirmed!
    providers = result.get("proposed_providers") or result.get("providers") or []
    active_idx = result.get("active_provider_index", 0)
    top_provider = (
        providers[active_idx]
        if 0 <= active_idx < len(providers)
        else providers[0]
    )
    booking = result["booking"]

    print(f"✅ [BOOKED] Provider: {top_provider['name']} | Code: {booking['booking_code']}")

    return ServiceResponse(
        session_id=session_id,
        intent=IntentResult(**intent_data),
        provider=ProviderSummary(**top_provider),
        booking=BookingRead(**booking),
        trace=[TraceStep(**s) for s in (result.get("trace_steps") or [])],
        message=(
            f"✅ Booking confirmed! {top_provider['name']} will be with you soon. "
            f"Your booking code is {booking['booking_code']}."
        ),
    )

