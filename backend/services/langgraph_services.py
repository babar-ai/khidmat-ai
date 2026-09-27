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

from langgraph.graph import END, START, StateGraph

from agents.state import KhidmatState
from core.database import SessionLocal
from models.booking import Booking, BookingStatus
from models.provider import Provider, ServiceCategory
from models.trace import Trace
from services.openai_services import openai_service
from services.prompt_templates import INTENT_EXTRACTION_SYSTEM_PROMPT
from utils import generate_booking_code, geocode_address, haversine_km

logger = logging.getLogger(__name__)

VALID_CATEGORIES = [c.value for c in ServiceCategory]


# ── Node 1: Intent Agent ──────────────────────────────────────────────────────
def intent_node(state: KhidmatState) -> dict[str, Any]:

    """
    Step 1: Uses OpenAI GPT-4o with structured JSON mode to parse user request.
    """
    request_text = state.get("request_text", "")
    start_time = time.perf_counter()

    try:
        intent_data = openai_service.extract_structured_json(
            system_prompt=INTENT_EXTRACTION_SYSTEM_PROMPT,
            user_content=request_text,
            temperature=0.0,
        )

        service_type = intent_data.get("service_type")
        if service_type and service_type not in VALID_CATEGORIES:
            logger.warning("Unrecognized service_type '%s'", service_type)
            intent_data["service_type"] = None
            intent_data["confidence"] = 0.0

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        input_preview = request_text[:60] + ("..." if len(request_text) > 60 else "")

        trace_step = {
            "step": 1,
            "agent": "IntentAgent",
            "action": "extract_intent",
            "input_summary": f"Text ({len(request_text)} chars): '{input_preview}'", 
            "output_summary": (
                f"service={intent_data.get('service_type')} | "
                f"loc={intent_data.get('location_text')} | "
                f"lang={intent_data.get('language')} | "
                f"conf={intent_data.get('confidence')}"
            ),
            "duration_ms": duration_ms,
        }

        updated_trace = list(state.get("trace_steps") or [])
        updated_trace.append(trace_step)

        if not intent_data.get("service_type"):
            return {
                "intent": intent_data,
                "trace_steps": updated_trace,
                "error": "Could not identify a supported service type from the request",
            }

        return {
            "intent": intent_data,
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
      Tier 3 — No coordinates at all → city-wide search ranked by rating only

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

        ranked = []
        for p in providers:
            
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
                "trace_steps": updated_trace,
                "error": f"No active {service_type} providers found in the system",
            }

        return {
            "providers": ranked,
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
    providers = state.get("providers") or []
    if not providers:
        return {"booking": None, "error": "Cannot book without matched providers"}

    top_provider = providers[0]
    intent = state.get("intent") or {}
    session_id = state.get("session_id")
    user_id = state.get("user_id")

    db = SessionLocal()
    try:
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


# ── Conditional Routing Functions ─────────────────────────────────────────────
def route_after_intent(state: KhidmatState) -> str:
    """Route: 'ok' -> matching_node, 'error' -> error_node"""
    if state.get("error"):
        return "error"
    intent = state.get("intent")
    if intent and intent.get("service_type") in VALID_CATEGORIES:
        return "ok"
    return "error"


def route_after_matching(state: KhidmatState) -> str:
    """Route: 'ok' -> booking_node, 'empty' -> error_node"""
    if state.get("error") or not state.get("providers"):
        return "empty"
    return "ok"


# ── LangGraph Service Class ───────────────────────────────────────────────────
class LangGraphService:
    """
    Central coordinator service for LangGraph workflow execution.
    Manages graph compilation and provides clean execution methods.
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(KhidmatState)

        # Register nodes
        builder.add_node("intent_node", intent_node)
        builder.add_node("matching_node", matching_node)
        builder.add_node("booking_node", booking_node)
        builder.add_node("error_node", error_node)

        # Flow edges
        builder.add_edge(START, "intent_node")

        builder.add_conditional_edges(
            "intent_node",
            route_after_intent,
            {"ok": "matching_node", "error": "error_node"},
        )

        builder.add_conditional_edges(
            "matching_node",
            route_after_matching,
            {"ok": "booking_node", "empty": "error_node"},
        )

        builder.add_edge("booking_node", END)
        builder.add_edge("error_node", END)

        return builder.compile()

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
        High-level execution helper initializing default state and running the graph.
        """
        sid = session_id or str(uuid.uuid4())
        initial_state: KhidmatState = {
            "request_text": request_text,
            "user_id": user_id,
            "user_lat": user_lat,
            "user_lng": user_lng,
            "session_id": sid,
            "intent": None,
            "providers": [],
            "booking": None,
            "trace_steps": [],
            "error": None,
        }
        return self.graph.invoke(initial_state)


# Shared singleton instance
langgraph_service = LangGraphService()
