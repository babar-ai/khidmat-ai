"""
Centralized LangGraph Orchestration Service for Khidmat AI.

Single point of control for:
  - Graph state machine definition and node implementations
  - Step 1: Intent Extraction Agent (OpenAI structured JSON)
  - Step 2: Matching Agent (PostgreSQL + distance & composite ranking)
  - Step 3: Booking Agent (Code generation + Booking & Trace persistence)
  - Error routing and edge decisions
  - Graph compilation, synchronous execution, and streaming
"""

import logging
import time
import uuid
from typing import Any

from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver       
from langgraph.graph import END, START, StateGraph

from agents.state import KhidmatState
from core.config import settings
from core.database import SessionLocal
from models.booking import Booking, BookingStatus
from models.provider import Provider, ServiceCategory
from models.trace import Trace
from services.openai_services import openai_service
from services.prompt_templates import (
    CONVERSATIONAL_SYSTEM_PROMPT,
    INTENT_EXTRACTION_SYSTEM_PROMPT,
)
from utils import generate_booking_code, geocode_address, haversine_km

logger = logging.getLogger(__name__)


VALID_CATEGORIES = [c.value for c in ServiceCategory]


# ── Node 1: Intent & Slot Extraction Agent ────────────────────────────────────
def intent_node(state: KhidmatState) -> dict[str, Any]:
    """
    Step 1: Uses OpenAI GPT-4o with structured JSON mode to parse user request
    and merge with previously extracted context from earlier conversation turns.
    """
    request_text = state.get("request_text", "")
    start_time = time.perf_counter()

    prev_intent = state.get("intent") or {}
    prev_service = prev_intent.get("service_type")
    prev_issue = prev_intent.get("issue_description")
    prev_location = prev_intent.get("location_text")
    prev_schedule = prev_intent.get("scheduled_text")
    prev_history = list(state.get("chat_history") or [])
    proposed_providers = list(state.get("proposed_providers") or [])

    # If providers were already proposed, check if the user is switching to a different category
    if proposed_providers:
        req_lower = request_text.lower()
        other_categories = [c for c in VALID_CATEGORIES if c != prev_service]
        switch_detected = any(
            cat.replace("_", " ") in req_lower or cat in req_lower
            for cat in other_categories
        )
        if not switch_detected:
            if "plumber" in req_lower and prev_service != "plumber":
                switch_detected = True
            elif "electric" in req_lower and prev_service != "electrician":
                switch_detected = True
            elif "carpenter" in req_lower and prev_service != "carpenter":
                switch_detected = True
            elif "clean" in req_lower and prev_service != "cleaner":
                switch_detected = True
            elif "paint" in req_lower and prev_service != "painter":
                switch_detected = True
            elif ("ac" in req_lower or "fridge" in req_lower) and prev_service != "ac_technician":
                switch_detected = True

        if not switch_detected:
            # User is having a post-recommendation conversation (objection, alternative, query, etc.)
            # Pass directly through to conversation_node without an expensive redundant slot-extraction call
            return {
                "request_text": request_text,
                "error": None,
            }
        else:
            # Service switched: clear previously proposed providers
            proposed_providers = []

    # Format previous context for the LLM
    context_lines = []
    if prev_service:
        context_lines.append(f"- Service: {prev_service}")
        
    if prev_issue:
        context_lines.append(f"- Issue: {prev_issue}")
    
    if prev_location:
        context_lines.append(f"- Location: {prev_location}")

    if prev_schedule:
        context_lines.append(f"- Schedule/Time: {prev_schedule}")

    if context_lines:
        context_str = "Prior Collected Context:\n" + "\n".join(context_lines)

    else:
        context_str = "No prior context (first turn)."

    user_prompt = f"{context_str}\n\nNew User Message: \"{request_text}\""

    try:
        extracted = openai_service.extract_structured_json(
            system_prompt=INTENT_EXTRACTION_SYSTEM_PROMPT,
            user_content=user_prompt,
            temperature=0.0,
        )
        print(f"🤖 [INTENT EXTRACTED] Prompt: '{request_text}' -> Result: {extracted}")

        # Slot merging logic
        is_greeting = bool(extracted.get("is_greeting"))
        new_service = extracted.get("service_type")
        if new_service and new_service not in VALID_CATEGORIES:
            print(f"⚠️ [INVALID CATEGORY] '{new_service}' not in {VALID_CATEGORIES}")
            new_service = None

        service_switched = bool(new_service and prev_service and new_service != prev_service)
        service_type = new_service or prev_service

        issue_description = extracted.get("issue_description") or (None if service_switched else prev_issue)
        location_text = extracted.get("location_text") or prev_location

        # Prevent stale schedule carry-over: if service switched or newly identified, do not inherit old timing
        if service_switched or (new_service and not prev_service):
            scheduled_text = extracted.get("scheduled_text")
        else:
            scheduled_text = extracted.get("scheduled_text") or prev_schedule

        language = extracted.get("language") or prev_intent.get("language") or "roman_ur"

        # Check location satisfaction: either typed location_text OR device GPS coordinates
        has_location = bool(location_text) or bool(state.get("user_lat") is not None and state.get("user_lng") is not None)
        has_timing = bool(scheduled_text and str(scheduled_text).strip())
        has_service = bool(service_type and service_type in VALID_CATEGORIES)

        # Slot completeness check
        missing_slots: list[str] = []
        if is_greeting:
            missing_slots = ["service", "location", "timing"]
        else:
            if not has_service:
                missing_slots.append("service")
            if not has_location:
                missing_slots.append("location")
            if not has_timing:
                missing_slots.append("timing")

        # STRICT PYTHON ENFORCEMENT: Never rely on LLM boolean alone!
        # Both LLM AND Python must confirm all 3 mandatory slots (service, location, timing) are satisfied
        is_ready = (
            has_service
            and has_location
            and has_timing
            and not is_greeting
            and len(missing_slots) == 0
            and bool(extracted.get("is_ready_to_book", True))
        )

        followup_question = extracted.get("followup_question")

        # Fallback question if missing slots but LLM didn't generate one
        if not is_ready and not followup_question:
            if "timing" in missing_slots:
                followup_question = "When would you like the service provider to visit? (e.g. urgent/now, today evening, or tomorrow)"
            elif "location" in missing_slots:
                followup_question = "Which sector or area in Islamabad are you located in? (e.g. G-13 or F-10)"
            elif "service" in missing_slots:
                followup_question = "Which service do you need? We provide AC & Fridge, Plumber, Electrician, Carpenter, Cleaner, and Painter."

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Update chat history
        updated_history = list(prev_history)
        updated_history.append({"role": "user", "content": request_text})
        if followup_question:
            updated_history.append({"role": "assistant", "content": followup_question})

        # Build consolidated intent
        consolidated_intent = {
            "is_greeting": is_greeting,
            "service_type": service_type,
            "issue_description": issue_description,
            "location_text": location_text,
            "scheduled_text": scheduled_text,
            "language": language,
            "confidence": extracted.get("confidence", 0.9 if is_ready else 0.5),
            "missing_slots": missing_slots,
            "is_ready_to_book": is_ready,
            "followup_question": followup_question,
            "reply_message": followup_question if is_greeting else None,
        }

        trace_step = {
            "step": 1,
            "agent": "IntentAgent",
            "action": "extract_intent_and_slots",
            "input_summary": f"Text: '{request_text[:60]}'",
            "output_summary": (
                f"service={service_type} | loc={location_text} | time={scheduled_text} | "
                f"ready={is_ready} | missing={missing_slots}"
            ),
            "duration_ms": duration_ms,
        }

        updated_trace = list(state.get("trace_steps") or [])
        updated_trace.append(trace_step)

        if not is_ready:
            prefix = "GREETING: " if is_greeting else "AWAITING_INPUT: "
            err = f"{prefix}{followup_question}"
            print(f"⏳ [AWAITING USER INPUT] {err}")
            return {
                "intent": consolidated_intent,
                "chat_history": updated_history,
                "missing_slots": missing_slots,
                "followup_question": followup_question,
                "is_ready_to_book": False,
                "trace_steps": updated_trace,
                "error": err,
            }

        return {
            "intent": consolidated_intent,
            "chat_history": updated_history,
            "missing_slots": [],
            "followup_question": None,
            "is_ready_to_book": True,
            "trace_steps": updated_trace,
            "error": None,
        }

    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception("IntentAgent execution failed: %s", str(e))

        trace_step = {
            "step": 1,
            "agent": "IntentAgent",
            "action": "extract_intent",
            "input_summary": f"Text ({len(request_text)} chars)",
            "output_summary": f"FAILED: {str(e)}",
            "duration_ms": duration_ms,
        }

        updated_trace = list(state.get("trace_steps") or [])
        updated_trace.append(trace_step)

        return {
            "intent": None,
            "trace_steps": updated_trace,
            "error": f"IntentAgent failed: {str(e)}",
        }



# ── Node 2: Matching Agent ────────────────────────────────────────────────────
def matching_node(state: KhidmatState) -> dict[str, Any]:
    """
    Step 2: Resolves effective user coordinates using 3-tier priority:
      Tier 1 — Geocode the extracted location_text via Nominatim (e.g. 'G-9/3 Street 4')
      Tier 2 — Fall back to device GPS (user_lat / user_lng) sent by the mobile app
      Tier 3 — No coordinates at all → city-wide search ranked by rating only.

    Then queries active providers from PostgreSQL, calculates Haversine distance,
    and ranks by composite score: 40% distance + 40% rating + 20% review count.
    """
    start_time = time.perf_counter()          #This records the starting time.
    intent = state.get("intent") or {}
    service_type = intent.get("service_type")
    location_text = intent.get("location_text")  # Extracted by IntentAgent (e.g. "G-9/3")
    device_lat = state.get("user_lat")            # GPS from mobile phone
    device_lng = state.get("user_lng")

    # ── Tier 1: Resolve from extracted text address via Nominatim ─────────────
    effective_lat: float | None = None
    effective_lng: float | None = None
    location_source = "none"

    if location_text:
        geocoded = geocode_address(location_text)
        if geocoded:
            effective_lat, effective_lng = geocoded
            location_source = f"geocoded: '{location_text}'"
            logger.info("MatchingAgent: Using geocoded location '%s' → (%.5f, %.5f)",
                        location_text, effective_lat, effective_lng)

    # ── Tier 2: Fall back to device GPS if geocoding failed/not available ─────
    if effective_lat is None and device_lat is not None and device_lng is not None:
        effective_lat, effective_lng = device_lat, device_lng
        location_source = f"device GPS: ({device_lat:.5f}, {device_lng:.5f})"
        logger.info("MatchingAgent: Using device GPS (%.5f, %.5f)", effective_lat, effective_lng)

    # ── Tier 3: No coordinates → city-wide search by rating only ─────────────
    if effective_lat is None:
        location_source = "none (city-wide fallback)"
        logger.warning("MatchingAgent: No coordinates available, ranking by rating only.")

    db = SessionLocal()                                    # This creates a SQLAlchemy database session.

    try:
        category_enum = ServiceCategory(service_type)

        providers = (                                      #SQLAlchemy's query builder to fetch only active
            db.query(Provider)                            #provider is sql table in postgray db that contains provider info
            .filter(
                Provider.category == category_enum,
                Provider.is_active.is_(True),
            )
            .all()
        )

        logger.info("MatchingAgent: Found %d providers for category '%s'", len(providers), service_type)
        logger.info("providers: %s", providers)

        rejected_ids = set(state.get("rejected_provider_ids") or [])

        ranked = []
        for p in providers:
            if p.id in rejected_ids:
                continue

            if effective_lat is not None and effective_lng is not None:                        # user location coordinates
                dist_km = haversine_km(effective_lat, effective_lng, p.latitude, p.longitude)  # p.latitude and p.longitude are provider location coordinates
                
                dist_score = (1.0 / (1.0 + (dist_km / 5.0))) * 0.40          #Convert distance into a score                  
                
                display_dist = round(dist_km, 2)
            
            else:
                dist_score = 0.20  # Neutral distance weight when no coordinates
                display_dist = None

            rating_score = (p.rating / 5.0) * 0.40
            reviews_score = (min(p.reviews_count, 100) / 100.0) * 0.20

            composite_score = dist_score + rating_score + reviews_score
 
            ranked.append({
                "id": p.id,
                "name": p.name,
                "city": p.city,
                "category": p.category.value,
                "rating": p.rating,
                "distance_km": display_dist,
                "_score": composite_score,
            })
 
        ranked.sort(key=lambda item: item["_score"], reverse=True)
        for item in ranked:
            del item["_score"]

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        top_name = ranked[0]["name"] if ranked else "None"

        trace_step = {
            "step": 2,
            "agent": "MatchingAgent",
            "action": "find_and_rank_providers",
            "input_summary": f"category={service_type}, location_source={location_source}",
            "output_summary": f"Found {len(ranked)} active providers. Top match: {top_name}",
            "duration_ms": duration_ms,
        }

        updated_trace = list(state.get("trace_steps") or [])
        updated_trace.append(trace_step)

        if not ranked:
            return {
                "providers": [],
                "proposed_providers": [],
                "active_provider_index": 0,
                "trace_steps": updated_trace,
                "error": f"No active {service_type} providers found in the system",
            }

        return {
            "providers": ranked,
            "proposed_providers": ranked,
            "active_provider_index": 0,
            "trace_steps": updated_trace,
            "error": None,
        }

    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception("MatchingAgent execution failed: %s", str(e))

        trace_step = {
            "step": 2,
            "agent": "MatchingAgent",
            "action": "find_and_rank_providers",
            "input_summary": f"category={service_type}, location_source={location_source}",
            "output_summary": f"FAILED: {str(e)}",
            "duration_ms": duration_ms,
        }

        updated_trace = list(state.get("trace_steps") or [])
        updated_trace.append(trace_step)

        return {
            "providers": [],
            "trace_steps": updated_trace,
            "error": f"MatchingAgent failed: {str(e)}",
        }
    finally:
        db.close()


# ── Node 3: Booking Agent ─────────────────────────────────────────────────────
def booking_node(state: KhidmatState) -> dict[str, Any]:
    """
    Step 3: Creates the booking record and persists the audit trace in PostgreSQL.
    """
    start_time = time.perf_counter()
    providers = state.get("proposed_providers") or state.get("providers") or []
    if not providers:
        return {"booking": None, "error": "Cannot book without matched providers"}

    active_idx = state.get("active_provider_index", 0)
    top_provider = (
        providers[active_idx]
        if 0 <= active_idx < len(providers)
        else providers[0]
    )
    intent = state.get("intent") or {}
    session_id = state.get("session_id")
    user_id = state.get("user_id")

    db = SessionLocal()
    try:
        # If an earlier provider was confirmed for this session, cancel it before re-booking
        existing_booking = (
            db.query(Booking)
            .filter(
                Booking.session_id == session_id,
                Booking.status == BookingStatus.CONFIRMED,
            )
            .first()
        )
        if existing_booking:
            existing_booking.status = BookingStatus.CANCELLED
            db.flush()

        booking_code = generate_booking_code()
        new_booking = Booking(
            session_id=session_id,
            user_id=user_id,
            provider_id=top_provider["id"],
            service_type=intent.get("service_type") or top_provider["category"],
            location_text=intent.get("location_text"),
            booking_code=booking_code,
            status=BookingStatus.CONFIRMED,
        )
        db.add(new_booking)
        db.flush()  # Populates new_booking.id without committing transaction yet

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        trace_step = {
            "step": 3,
            "agent": "BookingAgent",
            "action": "create_booking",
            "input_summary": f"provider_id={top_provider['id']}, user_id={user_id}",
            "output_summary": f"Booking {booking_code} created (ID: {new_booking.id}) with provider: {top_provider['name']}",
            "duration_ms": duration_ms,
        }

        all_steps = list(state.get("trace_steps") or [])
        all_steps.append(trace_step)

        # Persist full trace record in database
        trace_record = Trace(
            session_id=session_id,
            steps=all_steps,
            final_service_type=new_booking.service_type,
            final_provider_name=top_provider["name"],
        )
        db.add(trace_record)
        db.commit()
        db.refresh(new_booking)

        booking_dict = {
            "id": new_booking.id,
            "session_id": new_booking.session_id,
            "user_id": new_booking.user_id,
            "provider_id": new_booking.provider_id,
            "service_type": new_booking.service_type,
            "location_text": new_booking.location_text,
            "scheduled_at": new_booking.scheduled_at,
            "booking_code": new_booking.booking_code,
            "status": new_booking.status.value,
            "created_at": new_booking.created_at,
            "updated_at": new_booking.updated_at,
        }

        return {
            "booking": booking_dict,
            "trace_steps": all_steps,
            "error": None,
        }

    except Exception as e:
        db.rollback()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception("BookingAgent execution failed: %s", str(e))

        trace_step = {
            "step": 3,
            "agent": "BookingAgent",
            "action": "create_booking",
            "input_summary": f"provider_id={top_provider.get('id')}",
            "output_summary": f"FAILED: {str(e)}",
            "duration_ms": duration_ms,
        }

        updated_trace = list(state.get("trace_steps") or [])
        updated_trace.append(trace_step)

        return {
            "booking": None,
            "trace_steps": updated_trace,
            "error": f"BookingAgent failed: {str(e)}",
        }
    finally:
        db.close()


# ── Node 4: Error Node ────────────────────────────────────────────────────────
def error_node(state: KhidmatState) -> dict[str, Any]:
    """Terminal failure node: cleans state and ensures error is explicitly captured."""
    error_msg = state.get("error") or "Pipeline execution aborted due to unresolved errors."
    logger.warning("Pipeline reached error_node: %s", error_msg)
    return {"error": error_msg}


# ── Node 5: Conversational Dialogue Agent ─────────────────────────────────────
def conversation_node(state: KhidmatState) -> dict[str, Any]:
    """
    Handles post-recommendation dialogue (objections on distance/price,
    alternatives, questions, confirmations) using GPT-4o and CONVERSATIONAL_SYSTEM_PROMPT.
    """
    start_time = time.perf_counter()
    request_text = state.get("request_text", "")
    proposed_providers = list(state.get("proposed_providers") or [])
    active_idx = state.get("active_provider_index", 0)
    rejected_ids = list(state.get("rejected_provider_ids") or [])
    chat_history = list(state.get("chat_history") or [])

    current_provider = (
        proposed_providers[active_idx]
        if 0 <= active_idx < len(proposed_providers)
        else (proposed_providers[0] if proposed_providers else None)
    )

    # Format current provider
    if current_provider:
        dist_str = f"{current_provider.get('distance_km')} km away" if current_provider.get('distance_km') is not None else "distance unknown"
        curr_str = f"Name: {current_provider.get('name')}, Category: {current_provider.get('category')}, Rating: {current_provider.get('rating')} stars, Distance: {dist_str}"
    else:
        curr_str = "None"

    # Format other available alternatives
    alt_lines = []
    for i, p in enumerate(proposed_providers):
        if i != active_idx and p.get("id") not in rejected_ids:
            p_dist = f"{p.get('distance_km')} km away" if p.get('distance_km') is not None else "distance unknown"
            alt_lines.append(f"- Option {i + 1}: {p.get('name')} (Rating: {p.get('rating')}, {p_dist})")
    alt_str = "\n".join(alt_lines) if alt_lines else "No other providers available in this category."

    # Format recent chat history (last 6 messages)
    history_lines = [
        f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
        for msg in chat_history[-6:]
    ]
    history_str = "\n".join(history_lines) if history_lines else "No previous chat."

    prompt_user_content = (
        f"Recent Conversation:\n{history_str}\n\n"
        f"Currently Recommended Provider:\n{curr_str}\n\n"
        f"Other Available Providers in System:\n{alt_str}\n\n"
        f"User Message: \"{request_text}\""
    )

    try:
        conv_output = openai_service.extract_structured_json(
            system_prompt=CONVERSATIONAL_SYSTEM_PROMPT,
            user_content=prompt_user_content,
            temperature=0.3,
        )
        print(f"💬 [CONVERSATION AGENT] Output: {conv_output}")

        dialogue_act = conv_output.get("dialogue_act") or "other"
        reply_message = conv_output.get("reply_message") or "I understand. How would you like to proceed?"
        advance_provider = bool(conv_output.get("advance_provider"))

        # Update history
        updated_history = list(chat_history)
        updated_history.append({"role": "user", "content": request_text})
        updated_history.append({"role": "assistant", "content": reply_message})

        new_active_idx = active_idx
        updated_rejected = list(rejected_ids)

        if dialogue_act == "request_alternative" or advance_provider:
            if current_provider and current_provider.get("id"):
                if current_provider["id"] not in updated_rejected:
                    updated_rejected.append(current_provider["id"])

            # Find next provider that isn't rejected
            for next_idx in range(len(proposed_providers)):
                cand = proposed_providers[next_idx]
                if cand.get("id") not in updated_rejected:
                    new_active_idx = next_idx
                    break
            else:
                if active_idx + 1 < len(proposed_providers):
                    new_active_idx = active_idx + 1

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        trace_step = {
            "step": 2,
            "agent": "ConversationAgent",
            "action": f"handle_{dialogue_act}",
            "input_summary": f"Text: '{request_text[:60]}'",
            "output_summary": f"act={dialogue_act} | active_idx={new_active_idx} | reply='{reply_message[:50]}...'",
            "duration_ms": duration_ms,
        }

        updated_trace = list(state.get("trace_steps") or [])
        updated_trace.append(trace_step)

        if dialogue_act == "booking_confirmed":
            return {
                "dialogue_act": dialogue_act,
                "followup_question": reply_message,
                "chat_history": updated_history,
                "active_provider_index": new_active_idx,
                "rejected_provider_ids": updated_rejected,
                "is_ready_to_book": True,
                "trace_steps": updated_trace,
                "error": None,
            }

        return {
            "dialogue_act": dialogue_act,
            "followup_question": reply_message,
            "chat_history": updated_history,
            "active_provider_index": new_active_idx,
            "rejected_provider_ids": updated_rejected,
            "is_ready_to_book": False,
            "booking": None,
            "trace_steps": updated_trace,
            "error": f"CONVERSATION: {reply_message}",
        }

    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception("ConversationAgent failed: %s", str(e))
        trace_step = {
            "step": 2,
            "agent": "ConversationAgent",
            "action": "handle_dialogue",
            "input_summary": f"Text: '{request_text[:60]}'",
            "output_summary": f"FAILED: {str(e)}",
            "duration_ms": duration_ms,
        }
        updated_trace = list(state.get("trace_steps") or [])
        updated_trace.append(trace_step)
        return {
            "dialogue_act": "other",
            "followup_question": "Sorry, could you please repeat that?",
            "is_ready_to_book": False,
            "trace_steps": updated_trace,
            "error": f"ConversationAgent error: {str(e)}",
        }


# ── Conditional Routing Functions ─────────────────────────────────────────────
def route_after_intent(state: KhidmatState) -> str:
    """Route: 'conversational' -> conversation_node, 'ok' -> matching_node, 'error' -> error_node"""
    if state.get("proposed_providers"):
        return "conversational"

    if state.get("error") or not state.get("is_ready_to_book"):
        return "error"

    intent = state.get("intent")
    if intent and intent.get("service_type") in VALID_CATEGORIES:
        return "ok"

    return "error"


def route_after_conversation(state: KhidmatState) -> str:
    """Route: 'booking' -> booking_node, 'end' -> END"""
    if state.get("dialogue_act") == "booking_confirmed":
        return "booking"
    return "end"


def route_after_matching(state: KhidmatState) -> str:
    """Route: 'ok' -> booking_node, 'empty' -> error_node"""
    if state.get("error") or not state.get("providers"):
        return "empty"

    return "ok"


# ── LangGraph Service Class with PostgreSQL Checkpoint Persistence ─────────────
class LangGraphService:
    """
    Central coordinator service for LangGraph workflow execution.
    Manages graph compilation and persistent state checkpointer via PostgreSQL.
    """

    def __init__(self):
        # Configure connection pool for LangGraph PostgresSaver
        conn_str = settings.DATABASE_URL.replace("+psycopg2", "")
        self.pool = ConnectionPool(conn_str, max_size=10, kwargs={"autocommit": True})
        self.checkpointer = PostgresSaver(self.pool)
        self.checkpointer.setup()  # ensures checkpoint tables exist in kidmat_db
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(KhidmatState)

        # Register nodes
        builder.add_node("intent_node", intent_node)
        builder.add_node("conversation_node", conversation_node)
        builder.add_node("matching_node", matching_node)
        builder.add_node("booking_node", booking_node)
        builder.add_node("error_node", error_node)

        # Flow edges
        builder.add_edge(START, "intent_node")

        builder.add_conditional_edges(
            "intent_node",
            route_after_intent,
            {
                "conversational": "conversation_node",
                "ok": "matching_node",
                "error": "error_node",
            },
        )

        builder.add_conditional_edges(
            "conversation_node",
            route_after_conversation,
            {
                "booking": "booking_node",
                "end": END,
            },
        )

        builder.add_conditional_edges(
            "matching_node",
            route_after_matching,
            {"ok": "booking_node", "empty": "error_node"},
        )

        builder.add_edge("booking_node", END)
        builder.add_edge("error_node", END)

        # Compile with persistent PostgreSQL checkpointer
        return builder.compile(checkpointer=self.checkpointer)

    def run(self, state: KhidmatState) -> KhidmatState:
        """Executes the state machine synchronously to completion."""
        return self.graph.invoke(state)

    def run_pipeline(
        self,
        request_text: str,
        user_id: str,
        user_lat: float | None = None,
        user_lng: float | None = None,
        session_id: str | None = None,
    ) -> KhidmatState:
        """
        Runs the conversational agent pipeline for a user message.
        State (accumulated slots, prior context) is automatically retrieved from
        and persisted to PostgreSQL under thread_id = session_id.
        """
        sid = session_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": sid}}

        update_payload = {
            "request_text": request_text,
            "user_id": user_id,
            "user_lat": user_lat,
            "user_lng": user_lng,
            "session_id": sid,
        }
        return self.graph.invoke(update_payload, config=config)


# Shared singleton instance
langgraph_service = LangGraphService()

