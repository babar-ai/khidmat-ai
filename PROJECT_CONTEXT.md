# Khidmat AI — Complete Project Handoff Document

> **Purpose**: Full context for continuing development.
> Last updated: 2026-09-23. Phases 1-4.0 are complete.
> GitHub: https://github.com/babar-ai/khidmat-ai

---

## 1. What is Khidmat?

**Khidmat** is an AI-powered service booking platform for Pakistan.
A user types in Urdu, Roman Urdu, or English:
"Mujhe kal subah G-13 mein AC technician chahiye"

The backend:
1. Understands the intent (service, location, time, language) via LLM
2. Finds the best nearby provider via DB query + distance ranking
3. Creates a booking and returns confirmation with full agent trace

---

## 2. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | FastAPI | 0.115.0 |
| Database | PostgreSQL + PostGIS | 16 + 3.4 |
| ORM | SQLAlchemy | 2.0.35 |
| Migrations | Alembic | 1.13.3 |
| DB Driver | psycopg2-binary | 2.9.9 |
| Validation | Pydantic | 2.9.2 |
| Config | pydantic-settings | 2.5.2 |
| LLM | OpenAI GPT-4o | openai 1.52.0 |
| Agent Graph | LangGraph | 0.2.28 |
| LangChain+OpenAI | langchain-openai | 0.2.3 |
| State Persistence | langgraph-checkpoint-postgres | latest |
| Containers | Docker Compose | - |
| Mobile | Expo React Native | TypeScript + NativeWind |

---

## 3. Project Structure

```
d:\project ideas\kidmat project\
├── backend/
│   ├── app/
│   │   ├── __init__.py               (empty)
│   │   └── main.py                   DONE - lifespan, health endpoint
│   ├── core/
│   │   ├── __init__.py               (empty)
│   │   ├── config.py                 DONE - Pydantic Settings reads .env
│   │   └── database.py               DONE - engine, SessionLocal, Base, get_db
│   ├── models/
│   │   ├── __init__.py               DONE - imports all models
│   │   ├── provider.py               DONE - Provider ORM + ServiceCategory enum
│   │   ├── booking.py                DONE - Booking ORM + BookingStatus enum + FK
│   │   └── trace.py                  DONE - Trace ORM with JSON steps column
│   ├── schemas/
│   │   ├── __init__.py               DONE - re-exports all schemas
│   │   ├── provider.py               DONE - ProviderCreate, ProviderRead, ProviderSummary
│   │   ├── booking.py                DONE - BookingCreate, BookingRead, BookingStatusUpdate
│   │   ├── trace.py                  DONE - TraceStep, TraceRead
│   │   ├── request.py                DONE - ServiceRequest (POST body)
│   │   └── response.py               DONE - IntentResult, ServiceResponse, ErrorResponse
│   ├── agents/                       DONE (Phase 4)
│   │   ├── __init__.py               DONE - exports KhidmatState
│   │   └── state.py                  DONE - central KhidmatState TypedDict (input, trace, outputs)
│   ├── routers/                      NEXT - Phase 5
│   │   (empty)
│   ├── services/                     DONE
│   │   ├── __init__.py               DONE - exports OpenAIService, LangGraphService, prompt templates
│   │   ├── openai_services.py        DONE - centralized OpenAI wrapper (single point of control)
│   │   ├── langgraph_services.py     DONE - centralized LangGraph workflow orchestrator
│   │   └── prompt_templates.py       DONE - centralized prompt repository
│   ├── utils/                        DONE
│   │   ├── __init__.py               DONE - exports haversine_km, generate_booking_code
│   │   ├── geo.py                    DONE - Haversine distance calculator
│   │   └── code_generator.py         DONE - 8-char booking confirmation code generator
│   ├── alembic/                      DONE
│   │   ├── env.py                    configured with Base + PostGIS filter
│   │   ├── versions/
│   │   │   └── c0df21784762_initial_tables.py  APPLIED
│   │   └── script.py.mako
│   ├── alembic.ini                   DONE
│   ├── .env                          real secrets, NOT committed
│   ├── .env.example                  template, committed
│   ├── Dockerfile                    Python 3.12-slim
│   └── requirements.txt              DONE - all packages including langgraph
├── khidmat-mobile-app/               Expo React Native (monorepo)
├── docker-compose.yml                DONE
├── .gitignore                        DONE
└── README.md                         DONE
```

---

## 4. Environment Variables (backend/.env)

```
DATABASE_URL=postgresql+psycopg2://kidmat_user:kidmat_pass@db:5432/kidmat_db
OPENAI_API_KEY=sk-proj-...  (real key in .env, not committed)
APP_ENV=development
```

IMPORTANT: In Docker the DB host is "db" (service name), NOT "localhost".

---

## 5. How to Run

```bash
docker compose up                    # start DB + backend with hot-reload
docker compose up --build            # rebuild after requirements.txt changes
docker compose down                  # stop containers

docker exec kidmat_backend alembic upgrade head
docker exec kidmat_backend alembic revision --autogenerate -m "description"
docker exec kidmat_backend alembic current

curl http://localhost:8000/health    # should return {"status":"ok"}
# API docs at: http://localhost:8000/docs
```

---

## 6. Database Tables (all CREATED and APPLIED)

Migration c0df21784762_initial_tables is applied.

### providers
- id INTEGER PK
- name VARCHAR(150) NOT NULL
- phone VARCHAR(20) nullable
- city VARCHAR(100) NOT NULL
- category ENUM (ac_technician, plumber, electrician, carpenter, cleaner, painter)
- latitude FLOAT NOT NULL
- longitude FLOAT NOT NULL
- rating FLOAT default 0.0
- reviews_count INTEGER default 0
- is_active BOOLEAN default true
- created_at DATETIME server_default=now()

### bookings
- id INTEGER PK
- session_id VARCHAR(36) UUID indexed
- user_id VARCHAR(100)
- provider_id INTEGER FK -> providers.id
- service_type VARCHAR(100)
- location_text VARCHAR(255) nullable
- scheduled_at DATETIME nullable
- booking_code VARCHAR(20)  e.g. "XY4F9K2A"
- status ENUM (pending, confirmed, completed, cancelled)
- created_at DATETIME server_default=now()
- updated_at DATETIME onupdate=now()

### traces
- id INTEGER PK
- session_id VARCHAR(36) UNIQUE indexed
- steps JSON  list of TraceStep dicts
- final_service_type VARCHAR(100) nullable
- final_provider_name VARCHAR(150) nullable
- created_at DATETIME server_default=now()

---

## 7. Key Code Patterns

### Pydantic Settings (core/config.py)
```python
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    APP_ENV: str = "development"
    class Config:
        env_file = ".env"
settings = Settings()  # single shared instance imported everywhere
```

### SQLAlchemy 2.0 ORM style
```python
class Provider(Base):
    __tablename__ = "providers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
```

### get_db dependency
```python
def get_db():
    db = SessionLocal()
    try:
        yield db       # hands session to route function
    finally:
        db.close()     # always closes, even on crash
```

### FastAPI lifespan
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))  # verify DB on startup
    yield
    engine.dispose()  # clean shutdown

app = FastAPI(lifespan=lifespan)
```

### Alembic PostGIS filter (CRITICAL - without this Alembic drops PostGIS tables)
```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and reflected and compare_to is None:
        return False  # skip PostGIS internal tables
    return True

# passed to context.configure(include_object=include_object)
```

---

## 8. WHERE TO CONTINUE: Phase 4.1 - LangGraph Agents

Nothing in Phase 4.1+ has been started yet. Start with agents/state.py.

### Why LangGraph (user's explicit choice)
- Stateful: TypedDict state flows between all agent nodes
- Retries: RetryPolicy for OpenAI timeouts, DB errors
- Branching: conditional edges for "no providers found" path
- Persistence: PostgresSaver checkpoints to our existing PostgreSQL DB
- Streaming: can stream progress updates to mobile app

### Graph Design
```
START -> [intent_node] -> route_after_intent
                              |
                    ok -> [matching_node] -> route_after_matching
                    |                             |
                 error -> [error_node]    ok -> [booking_node] -> END
                                          |
                                       empty -> [error_node] -> END
```

### Step 4.1: agents/state.py (START HERE)
```python
from typing import TypedDict, Any

class KhidmatState(TypedDict):
    # INPUT - set by route before graph starts
    request_text: str
    user_id:      str
    user_lat:     float | None
    user_lng:     float | None
    session_id:   str

    # SET BY intent_node
    intent:       dict | None  # matches IntentResult schema

    # SET BY matching_node
    providers:    list[dict]   # list of ProviderSummary dicts

    # SET BY booking_node
    booking:      dict | None  # matches BookingRead schema

    # ACCUMULATED by all nodes
    trace_steps:  list[dict]   # list of TraceStep dicts

    # SET on any failure
    error:        str | None
```

### Step 4.2: agents/intent_node.py
```python
import json, time
from openai import OpenAI
from core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are an intent extraction assistant for a Pakistani service booking app.
Extract structured data from user message (Urdu, Roman Urdu, or English).
Return ONLY valid JSON:
{
  "service_type": one of [ac_technician,plumber,electrician,carpenter,cleaner,painter],
  "location_text": string or null,
  "scheduled_text": string or null,
  "language": one of [ur, roman_ur, en],
  "confidence": float 0.0-1.0
}
"""

def intent_node(state: KhidmatState) -> dict:
    start = time.time()
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": state["request_text"]},
        ]
    )
    data = json.loads(response.choices[0].message.content)
    duration_ms = int((time.time() - start) * 1000)

    trace_step = {
        "step": 1, "agent": "IntentAgent", "action": "extract_intent",
        "input_summary": f"Text ({len(state['request_text'])} chars)",
        "output_summary": f"service={data['service_type']} | loc={data['location_text']} | lang={data['language']} | conf={data['confidence']}",
        "duration_ms": duration_ms
    }
    return {
        "intent": data,
        "trace_steps": state.get("trace_steps", []) + [trace_step]
    }

def route_after_intent(state: KhidmatState) -> str:
    if state.get("intent") and state["intent"].get("service_type"):
        return "ok"
    return "error"
```

### Step 4.3: agents/matching_node.py
```python
import math, time
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.provider import Provider, ServiceCategory

def haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def matching_node(state: KhidmatState) -> dict:
    start = time.time()
    intent = state["intent"]
    db: Session = SessionLocal()
    try:
        category = ServiceCategory(intent["service_type"])
        providers = db.query(Provider).filter(
            Provider.category == category,
            Provider.is_active == True
        ).all()

        user_lat = state.get("user_lat")
        user_lng = state.get("user_lng")

        ranked = []
        for p in providers:
            dist = haversine_km(user_lat, user_lng, p.latitude, p.longitude) if user_lat and user_lng else 999
            score = (1/max(dist,0.1))*0.40 + (p.rating/5)*0.40 + (min(p.reviews_count,100)/100)*0.20
            ranked.append({"id": p.id, "name": p.name, "city": p.city, "category": p.category.value,
                           "rating": p.rating, "distance_km": round(dist,2), "_score": score})

        ranked.sort(key=lambda x: x["_score"], reverse=True)
        for p in ranked: del p["_score"]

        duration_ms = int((time.time() - start) * 1000)
        trace_step = {
            "step": 2, "agent": "MatchingAgent", "action": "find_and_rank_providers",
            "output_summary": f"Found {len(ranked)} providers. Top: {ranked[0]['name'] if ranked else 'none'}",
            "duration_ms": duration_ms
        }
        return {"providers": ranked, "trace_steps": state.get("trace_steps", []) + [trace_step]}
    finally:
        db.close()

def route_after_matching(state: KhidmatState) -> str:
    return "ok" if state.get("providers") else "empty"
```

### Step 4.4: agents/booking_node.py
```python
import secrets, string, uuid, time
from core.database import SessionLocal
from models.booking import Booking, BookingStatus
from models.trace import Trace

def generate_booking_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))

def booking_node(state: KhidmatState) -> dict:
    start = time.time()
    top_provider = state["providers"][0]
    intent = state["intent"]
    db = SessionLocal()
    try:
        booking_code = generate_booking_code()
        booking = Booking(
            session_id=state["session_id"],
            user_id=state["user_id"],
            provider_id=top_provider["id"],
            service_type=intent["service_type"],
            location_text=intent.get("location_text"),
            booking_code=booking_code,
            status=BookingStatus.CONFIRMED,
        )
        db.add(booking)
        db.flush()  # get booking.id without committing

        duration_ms = int((time.time() - start) * 1000)
        trace_step = {
            "step": 3, "agent": "BookingAgent", "action": "create_booking",
            "output_summary": f"Booking {booking_code} created | provider: {top_provider['name']} | status: confirmed",
            "duration_ms": duration_ms
        }
        all_steps = state.get("trace_steps", []) + [trace_step]

        trace = Trace(
            session_id=state["session_id"],
            steps=all_steps,
            final_service_type=intent["service_type"],
            final_provider_name=top_provider["name"],
        )
        db.add(trace)
        db.commit()
        db.refresh(booking)

        booking_dict = {
            "id": booking.id, "session_id": booking.session_id,
            "user_id": booking.user_id, "provider_id": booking.provider_id,
            "service_type": booking.service_type, "location_text": booking.location_text,
            "booking_code": booking.booking_code, "status": booking.status.value,
            "created_at": str(booking.created_at), "updated_at": str(booking.updated_at),
        }
        return {"booking": booking_dict, "trace_steps": all_steps}
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()
```

### Step 4.5: agents/graph.py
```python
from langgraph.graph import StateGraph, START, END
from agents.state import KhidmatState
from agents.intent_node import intent_node, route_after_intent
from agents.matching_node import matching_node, route_after_matching
from agents.booking_node import booking_node

def error_node(state: KhidmatState) -> dict:
    return {"error": state.get("error") or "Pipeline failed"}

def build_graph():
    graph = StateGraph(KhidmatState)
    graph.add_node("intent_node",   intent_node)
    graph.add_node("matching_node", matching_node)
    graph.add_node("booking_node",  booking_node)
    graph.add_node("error_node",    error_node)

    graph.add_edge(START, "intent_node")
    graph.add_conditional_edges("intent_node", route_after_intent, {
        "ok": "matching_node", "error": "error_node"
    })
    graph.add_conditional_edges("matching_node", route_after_matching, {
        "ok": "booking_node", "empty": "error_node"
    })
    graph.add_edge("booking_node", END)
    graph.add_edge("error_node",   END)

    return graph.compile()  # add checkpointer later

khidmat_graph = build_graph()
```

---

## 9. Phase 5 - Routes (after agents done)

```python
# routers/request.py
@router.post("/api/v1/request", response_model=ServiceResponse)
async def handle_request(body: ServiceRequest):
    session_id = str(uuid.uuid4())
    initial_state = {
        "request_text": body.text, "user_id": body.user_id,
        "user_lat": body.user_lat, "user_lng": body.user_lng,
        "session_id": session_id, "intent": None, "providers": [],
        "booking": None, "trace_steps": [], "error": None,
    }
    result = khidmat_graph.invoke(initial_state)
    # build and return ServiceResponse from result

# routers/booking.py
GET  /api/v1/booking/{id}            -> BookingRead
PATCH /api/v1/booking/{id}/status    -> BookingRead (body: BookingStatusUpdate)

# routers/trace.py
GET /api/v1/trace/{session_id}       -> TraceRead
```

Register all routers in app/main.py:
```python
from routers import request, booking, trace
app.include_router(request.router)
app.include_router(booking.router)
app.include_router(trace.router)
```

---

## 10. Phase 6 - Seed Data (mock Islamabad providers)

```python
# utils/seed.py
MOCK_PROVIDERS = [
    {"name": "Ali AC Services",    "category": "ac_technician", "city": "Islamabad", "latitude": 33.6895, "longitude": 73.0551, "rating": 4.7, "reviews_count": 89},
    {"name": "Rehman Plumbing",    "category": "plumber",       "city": "Islamabad", "latitude": 33.7215, "longitude": 73.0433, "rating": 4.5, "reviews_count": 62},
    {"name": "Karimi Electricals", "category": "electrician",   "city": "Islamabad", "latitude": 33.6754, "longitude": 73.0667, "rating": 4.8, "reviews_count": 134},
    {"name": "Hassan Carpentry",   "category": "carpenter",     "city": "Islamabad", "latitude": 33.6981, "longitude": 73.0311, "rating": 4.3, "reviews_count": 47},
    {"name": "CleanPro Islamabad", "category": "cleaner",       "city": "Islamabad", "latitude": 33.7102, "longitude": 73.0789, "rating": 4.6, "reviews_count": 201},
]
```

---

## 11. Phase Checklist

```
DONE  Phase 1   Foundation      (config, database, lifespan, health)
DONE  Phase 2   Models          (Provider, Booking, Trace ORM)
DONE  Phase 3   Schemas         (all Pydantic request/response shapes)
DONE  Phase 4.0 Alembic         (tables created in PostgreSQL)
DONE  Phase 4.1 KhidmatState    agents/state.py
DONE  Phase 4.2 IntentNode      agents/intent_node.py
DONE  Phase 4.3 MatchingNode    agents/matching_node.py
DONE  Phase 4.4 BookingNode     agents/booking_node.py
DONE  Phase 4.5 Graph           agents/graph.py + services/langgraph_services.py
NEXT  Phase 5   Routes          POST /request, GET /booking, GET /trace
TODO  Phase 6   Seed Data       mock providers in Islamabad
TODO  Phase 7   End-to-end test curl full pipeline
TODO  Phase 8   Mobile connect  wire khidmat-mobile-app to real API
```

---

## 12. Key Decisions Made

| Decision | Choice | Reason |
|---|---|---|
| Agent framework | LangGraph | Retries, branching, state persistence, streaming |
| LLM | OpenAI GPT-4o | User switched from Gemini to OpenAI |
| Location storage | Float lat/lng columns | Simpler than PostGIS geometry for MVP |
| Trace storage | JSON column in traces table | Flexible, no extra table |
| DB URL | From settings.DATABASE_URL | Not hardcoded in alembic.ini |
| PostGIS tables | Filtered in env.py include_object | Prevents Alembic dropping PostGIS internals |
| Mobile folder | khidmat-mobile-app | Renamed from khidmat-mobile |
| Repo structure | Monorepo frontend+backend | User's choice |

---

## 13. Commands Cheatsheet

```bash
# Start
docker compose up
docker compose up --build

# Migrations
docker exec kidmat_backend alembic upgrade head
docker exec kidmat_backend alembic revision --autogenerate -m "msg"
docker exec kidmat_backend alembic current
docker exec kidmat_backend alembic downgrade -1

# DB inspection
docker exec kidmat_db psql -U kidmat_user -d kidmat_db -c "\dt"
docker exec kidmat_db psql -U kidmat_user -d kidmat_db -c "SELECT * FROM providers;"

# Logs
docker logs kidmat_backend --tail 30

# Git
git add .; git commit -m "message"; git push
```
