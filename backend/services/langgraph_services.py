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

from datetime import datetime
import logging
import time
import uuid
from typing import Any

# pyrefly: ignore [missing-import]
from psycopg_pool import ConnectionPool
# pyrefly: ignore [missing-import]
from langgraph.checkpoint.postgres import PostgresSaver       
# pyrefly: ignore [missing-import]
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



    req_lower = request_text.lower()

    # If providers were already proposed, check if the user is switching to a different category
    if proposed_providers:
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
            elif "ac" in req_lower and prev_service != "ac_technician":
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

    user_prompt = (
        f"{context_str}\n\n"
        f"New User Message: \"{request_text}\"\n\n"
        f"REMINDER: Your followup_question MUST strictly match the language and script of 'New User Message' above (Roman Urdu, Urdu script, or English)!"
    )

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

        # STRICT PYTHON ENFORCEMENT:
        # All 3 mandatory slots (service, location, timing) are satisfied
        is_ready = (
            has_service
            and has_location
            and has_timing
            and not is_greeting
            and len(missing_slots) == 0
        )


        followup_question = extracted.get("followup_question")

        # Fallback question if missing slots but LLM didn't generate one (localized by language)
        if not is_ready and not followup_question:
            svc_name = (service_type or "service").replace("_", " ")
            if language == "ur":
                if "location" in missing_slots:
                    followup_question = f"ضرور! میں آپ کے لیے سروس کا بندوبست کرتا ہوں۔ آپ کی لوکیشن یا سیکٹر کون سا ہے؟"
                elif "timing" in missing_slots:
                    followup_question = "ٹیکنیشن کس وقت وزٹ کرے؟ (مثلاً ابھی، آج شام، یا کل)"
                elif "service" in missing_slots:
                    followup_question = "آپ کو کس سروس کی ضرورت ہے؟ ہمارے پاس اے سی، پلمبر، الیکٹریشن، کارپینٹر، کلینر اور پینٹر دستیاب ہیں۔"
            elif language == "roman_ur":
                if "location" in missing_slots:
                    followup_question = f"Zaroor! Main {svc_name} arrange kar deta hoon. Aap ki location ya sector konsa hai?"
                elif "timing" in missing_slots:
                    followup_question = "Technician kab visit kare? (maslan abhi/urgent, aaj shaam, ya kal subah?)"
                elif "service" in missing_slots:
                    followup_question = "Aap ko kis service ki zaroorat hai? Hamare paas AC Repair, Plumber, Electrician, Carpenter, Cleaner, aur Painter dastiyab hain."
            else:
                if "location" in missing_slots:
                    followup_question = f"Sure! I'll help you find a {svc_name}. What's your location?"
                elif "timing" in missing_slots:
                    followup_question = "When would you like the technician to visit? (e.g. urgent/now, today evening, or tomorrow)"
                elif "service" in missing_slots:
                    followup_question = "Which service do you need? We provide AC Repair, Plumber, Electrician, Carpenter, Cleaner, and Painter."

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
                "phone": p.phone,
                "whatsapp_number": p.whatsapp_number,
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
            "followup_question": "Here's the best matched provider based on distance, reviews, rating, and availability:",
            "booking_confirmation_pending": False,
            "is_ready_to_book": False,
            "booking": None,
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
            "scheduled_text": intent.get("scheduled_text") or "today",
            "scheduled_at": new_booking.scheduled_at.isoformat() if new_booking.scheduled_at else None,
            "booking_code": new_booking.booking_code,
            "status": new_booking.status.value,
            "created_at": new_booking.created_at.isoformat() if new_booking.created_at else None,
            "updated_at": new_booking.updated_at.isoformat() if new_booking.updated_at else None,
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
    intent = state.get("intent") or {}

    current_provider = (
        proposed_providers[active_idx]
        if 0 <= active_idx < len(proposed_providers)
        else (proposed_providers[0] if proposed_providers else None)
    )
 
    booking = state.get("booking")

    # Format current provider
    if current_provider:
        dist_str = f"{current_provider.get('distance_km')} km away" if current_provider.get('distance_km') is not None else "distance unknown"
        phone_str = current_provider.get('phone') or "Not provided"
        whatsapp_str = current_provider.get('whatsapp_number') or phone_str
        booking_status_str = f"CONFIRMED (Booking Code: {booking.get('booking_code')})" if booking else "Not yet booked"

        curr_str = (
            f"Name: {current_provider.get('name')}, Category: {current_provider.get('category')}, "
            f"Rating: {current_provider.get('rating')} stars, Distance: {dist_str}, "
            f"Phone: {phone_str}, WhatsApp: {whatsapp_str}, Booking Status: {booking_status_str}"
        )

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
        f"User Message: \"{request_text}\"\n\n"
        f"REMINDER: Your reply_message MUST strictly match the language and script of 'User Message' above (Roman Urdu, Urdu script, or English)!"
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

        # Explicit Affirmative words
        AFFIRMATIVE_WORDS = {
            "yes", "haan", "theek hai", "thek hai", "ok", "okay",
            "confirm", "confirmed", "book", "book him", "book them",
            "book kar do", "book kardo", "kar do", "kardo", "kar dein",
            "proceed", "sure", "yep", "yeah", "ji haan", "ji",
            "haan kardo", "chalo", "done", "perfect", "confirm booking",
        }
        clean_req = request_text.strip().lower().rstrip("!.,?")
        
        is_explicit_affirmative = (
            clean_req in AFFIRMATIVE_WORDS
            or any(clean_req.startswith(w) for w in ["yes", "haan", "theek hai", "ok", "confirm", "proceed", "ji "])
        )

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

        # Check if booking is already confirmed in this session
        has_existing_booking = bool(booking and isinstance(booking, dict) and booking.get("status") == "confirmed")

        # Check if human confirmation has already been requested
        was_confirmation_pending = bool(state.get("booking_confirmation_pending", False)) and not has_existing_booking

        is_explicit_confirm_cmd = (
            not has_existing_booking and (
                clean_req.startswith("confirm booking")
                or clean_req in {"confirm", "confirm it", "confirm please", "yes confirm", "haan confirm", "ji confirm", "confirmed"}
            )
        )
        is_cancellation = (
            dialogue_act == "booking_cancelled"
            or any(clean_req.startswith(w) for w in ["cancel", "rehne do", "nahi chahiye", "no", "nahi"])
            or clean_req in {"cancel", "no", "nah", "stop", "rehne do", "nahi chahiye"}
        )
        is_selection_or_book = (
            not has_existing_booking and (
                dialogue_act in {"booking_confirmed", "booking_intent"}
                or any(w in clean_req for w in ["fine", "book", "this one", "first technician", "second technician", "third technician", "send"])
            )
        )

        target_prov = (
            proposed_providers[new_active_idx]
            if 0 <= new_active_idx < len(proposed_providers)
            else (current_provider or (proposed_providers[0] if proposed_providers else None))
        )
        prov_name = target_prov["name"] if target_prov else "the technician"
        serv_name = (intent.get("service_type") or (target_prov.get("category") if target_prov else "service")).replace("_", " ").title()
        time_name = intent.get("scheduled_text") or "today"
        lang = intent.get("language") or "en"

        new_scheduled_text = conv_output.get("new_scheduled_text")
        is_reschedule_intent = (
            dialogue_act in ("reschedule_requested", "slot_modification")
            or bool(new_scheduled_text)
            or any(w in clean_req for w in ["change it to", "reschedule", "badal do", "tabdeel", "instead of", "new time"])
        )

        if is_cancellation:
            dialogue_act = "booking_cancelled"
            is_pending_confirmation = False
            if lang == "ur":
                reply_message = "بکنگ کینسل کر دی گئی ہے۔ اگر آپ کو کسی اور سروس یا وقت کی ضرورت ہو تو ضرور بتائیں۔"
            elif lang == "roman_ur":
                reply_message = "Booking cancel kar di gayi hai. Agar koi aur service ya waqt chahiye ho toh zaroor batayein."
            else:
                reply_message = "Booking cancelled. Feel free to request another service or time whenever you're ready."

        elif is_reschedule_intent:
            dialogue_act = "reschedule_requested"
            is_pending_confirmation = False
            effective_time = new_scheduled_text or time_name

            intent["scheduled_text"] = effective_time
            time_name = effective_time

            # Update PostgreSQL database if booking exists
            session_id = state.get("session_id")
            if booking and session_id:
                db = SessionLocal()
                try:
                    db_booking = (
                        db.query(Booking)
                        .filter(
                            Booking.session_id == session_id,
                            Booking.status == BookingStatus.CONFIRMED,
                        )
                        .first()
                    )
                    if db_booking:
                        db_booking.updated_at = datetime.utcnow()
                        db.commit()
                except Exception as e:
                    logger.warning("Reschedule DB commit error: %s", e)
                    db.rollback()
                finally:
                    db.close()

                booking["scheduled_text"] = effective_time

        elif is_explicit_confirm_cmd or (was_confirmation_pending and (is_explicit_affirmative or dialogue_act == "booking_confirmed")):
            # Human in the loop: Explicit user confirmation received!
            dialogue_act = "booking_confirmed"
            is_pending_confirmation = False
            if not any(w in reply_message.lower() for w in ["confirm", "rabta", "raabta", "booking", "کامیاب", "بکنگ"]):
                if lang == "ur":
                    reply_message = f"بہترین! {prov_name} کے ساتھ بکنگ کنفرم ہو گئی ہے۔ ٹیکنیشن جلد آپ سے رابطہ کرے گا۔"
                elif lang == "roman_ur":
                    reply_message = f"Zabardast! {prov_name} ke saath booking confirm ho gayi hai. Technician jald aap se rabta karega."
                else:
                    reply_message = f"Great! Booking confirmed with {prov_name}. The technician will contact you shortly."

        elif is_selection_or_book or was_confirmation_pending:
            # Human in the loop: Ask for confirmation before booking!
            dialogue_act = "confirmation_requested"
            is_pending_confirmation = True
            if lang == "ur":
                reply_message = f"آپ {prov_name} کو {serv_name} ({time_name}) کے لیے بک کرنے لگے ہیں۔ کیا میں یہ بکنگ کنفرم کر دوں؟"
            elif lang == "roman_ur":
                reply_message = f"Aap {prov_name} ko {serv_name} ({time_name}) ke liye book karne lage hain. Kya main yeh booking confirm kar doon?"
            else:
                reply_message = f"You're about to book {prov_name} for {serv_name} ({time_name}). Would you like me to confirm this booking?"

        else:
            is_pending_confirmation = False

        # Update history
        updated_history = list(chat_history)
        updated_history.append({"role": "user", "content": request_text})
        updated_history.append({"role": "assistant", "content": reply_message})

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
                "booking_confirmation_pending": False,
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
            "booking_confirmation_pending": is_pending_confirmation,
            "is_ready_to_book": False,
            "booking": booking,
            "new_scheduled_text": time_name if dialogue_act in ("reschedule_requested", "slot_modification") else None,
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
    if state.get("proposed_providers") or state.get("booking"):
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
    """Route: 'ok' -> END (proposes provider to user, awaits human confirmation), 'empty' -> error_node"""
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
            {"ok": END, "empty": "error_node"},
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

