# Khidmat AI — Agentic Service Orchestrator

> Find and book local service providers (plumbers, electricians, AC technicians, and more) using natural language — in **Urdu, Roman Urdu, or English**.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docs.docker.com/compose)
[![Expo](https://img.shields.io/badge/Expo-React%20Native-000020?logo=expo)](https://expo.dev)

---

## What is Khidmat?

**Khidmat** (خدمت — "service" in Urdu) is an AI-powered backend that takes a user's natural language request and runs it through three intelligent agents to find and book the right service provider nearby.

**Example request:**
> *"Mujhe kal subah G-13 mein AC technician chahiye"*
> *(I need an AC technician in G-13 tomorrow morning)*

The system understands the intent, finds the best-rated nearby provider, and creates a confirmed booking — all automatically.

---

## Architecture Overview

```
User Request (Urdu / Roman Urdu / English)
        |
        v
  [IntentAgent]     -- GPT-4o extracts: service type, location, time, language
        |
        v
  [MatchingAgent]   -- PostgreSQL: geocode + fetch providers + rank by score
        |
        v
  [BookingAgent]    -- PostgreSQL: create booking + persist agent trace
        |
        v
  HTTP Response     -- intent + provider + booking + trace returned to client
```

---

## Project Structure

```
khidmat-ai/
├── backend/
│   ├── app/main.py                  # FastAPI entrypoint, lifespan, routers
│   ├── core/
│   │   ├── config.py                # Pydantic Settings (reads .env)
│   │   └── database.py              # SQLAlchemy engine, SessionLocal, Base
│   ├── models/
│   │   ├── provider.py              # Provider ORM + ServiceCategory enum
│   │   ├── booking.py               # Booking ORM + BookingStatus enum
│   │   └── trace.py                 # Trace ORM (stores agent steps as JSON)
│   ├── schemas/
│   │   ├── request.py               # ServiceRequest — validates incoming HTTP body
│   │   ├── response.py              # ServiceResponse, IntentResult, ErrorResponse
│   │   ├── provider.py              # ProviderSummary
│   │   ├── booking.py               # BookingRead, BookingStatusUpdate
│   │   └── trace.py                 # TraceStep, TraceRead
│   ├── agents/
│   │   └── state.py                 # KhidmatState TypedDict (shared pipeline state)
│   ├── services/
│   │   ├── langgraph_services.py    # All 3 agent nodes + graph wiring
│   │   ├── openai_services.py       # OpenAI wrapper (JSON mode)
│   │   └── prompt_templates.py      # System prompts for LLM
│   ├── utils/                       # haversine_km, generate_booking_code, geocode_address
│   ├── routers/                     # Phase 5: /request, /booking, /trace
│   ├── alembic/                     # DB migrations
│   └── requirements.txt
├── khidmat-mobile-app/              # Expo React Native (TypeScript + NativeWind)
└── docker-compose.yml               # PostgreSQL/PostGIS + FastAPI
```

---

## Getting Started

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js](https://nodejs.org/) (for the mobile app)

### 1. Clone the repo
```bash
git clone https://github.com/babar-ai/khidmat-ai.git
cd khidmat-ai
```

### 2. Configure environment
```bash
cp backend/.env.example backend/.env
# Fill in: DATABASE_URL, OPENAI_API_KEY, APP_ENV
```

### 3. Start the backend
```bash
docker compose up
# PostgreSQL + PostGIS on :5432, FastAPI on :8000 with hot-reload
```

### 4. Verify
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```
API docs: **http://localhost:8000/docs**

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Health check |
| `POST` | `/api/v1/request` | Main pipeline — full agent orchestration |
| `GET`  | `/api/v1/booking/{id}` | Get booking details |
| `PATCH`| `/api/v1/booking/{id}/status` | Update booking status |
| `GET`  | `/api/v1/trace/{session_id}` | Full agent reasoning trace |

### Example Request
```bash
curl -X POST http://localhost:8000/api/v1/request \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Mujhe kal subah G-13 mein AC technician chahiye",
    "user_id": "user_123",
    "user_lat": 33.6844,
    "user_lng": 73.0479
  }'
```

### Example Response
```json
{
  "session_id": "a3f2c1d0-...",
  "intent": {
    "service_type": "ac_technician",
    "location_text": "G-13, Islamabad",
    "scheduled_text": "kal subah",
    "language": "roman_ur",
    "confidence": 0.95
  },
  "provider": { "id": 7, "name": "Ali AC Services", "rating": 4.7, "distance_km": 1.2 },
  "booking": { "booking_code": "XY4F9K2A", "status": "confirmed" },
  "trace": [
    {"step": 1, "agent": "IntentAgent",   "duration_ms": 312},
    {"step": 2, "agent": "MatchingAgent", "duration_ms": 87},
    {"step": 3, "agent": "BookingAgent",  "duration_ms": 45}
  ]
}
```

---

## How the Agent Pipeline Works

The backend uses **LangGraph** — a state machine where each node is a Python function that reads/writes a shared `KhidmatState` TypedDict. Edges between nodes can be conditional (branch on success vs failure).

```
START --> [intent_node] --> [matching_node] --> [booking_node] --> END
               |                  |
          (fail/null)      (no providers)
               v                  v
          [error_node] <--- [error_node] --> END
```

---

### Node 1 — IntentAgent

**Goal:** Turn raw natural language into a structured JSON object.

**How it works:**
- Calls `openai_service.extract_structured_json()` which sends the user's text to GPT-4o with `response_format: json_object`
- The system prompt (in `prompt_templates.py`) instructs the LLM to return exactly these keys:

```json
{
  "service_type": "ac_technician",   // one of 6 valid categories or null
  "location_text": "G-13",           // raw location string or null
  "scheduled_text": "kal subah",     // raw time string or null
  "language": "roman_ur",            // ur | roman_ur | en
  "confidence": 0.95                 // 0.0 to 1.0
}
```

- Result is stored as `state["intent"]` (plain Python dict — no Pydantic at this step)

**Routing:**
- `service_type` in valid categories → `matching_node`
- `service_type` is null/unrecognized → `error_node`

---

### Node 2 — MatchingAgent

**Goal:** Find and rank active providers from the database for the detected service type.

**Step 1 — Resolve location (3-tier priority):**

| Tier | Source | Example |
|------|--------|---------|
| 1st | Nominatim geocodes `location_text` from intent | "G-13" → (33.647, 72.951) |
| 2nd | Device GPS sent by the mobile app (`user_lat`, `user_lng`) | Falls back if geocoding fails |
| 3rd | No coordinates available | City-wide search, ranked by rating only |

**Step 2 — Query PostgreSQL:**
Fetches all rows from `providers` where `category = service_type AND is_active = True`.

**Step 3 — Score and rank every provider:**

Each provider gets a composite score from 3 independent components:

```
composite_score = dist_score + rating_score + reviews_score
```

| Component | Formula | Weight | Design Decision |
|-----------|---------|--------|-----------------|
| `dist_score` | `(1 / (1 + dist_km / 5)) × 0.40` | 40% | Smooth decay: provider 5 km away gets half the max distance score. Not binary. |
| `rating_score` | `(rating / 5.0) × 0.40` | 40% | 5 stars = 0.40, 4 stars = 0.32 |
| `reviews_score` | `(min(reviews, 100) / 100) × 0.20` | 20% | Capped at 100 so a provider with 500 reviews doesn't dominate |

**Worked example** — 2 km away, 4.7 stars, 89 reviews:
```
dist_score    = 1 / (1 + 2/5)  × 0.40  =  0.714 × 0.40  =  0.286
rating_score  = (4.7 / 5.0)    × 0.40  =  0.940 × 0.40  =  0.376
reviews_score = (89 / 100)     × 0.20  =  0.890 × 0.20  =  0.178
                                                             ───────
                                           composite_score =  0.840
```

Providers are sorted descending by `composite_score`. The internal `_score` key is deleted before the list is returned — it's never exposed to the API consumer.

**Routing:**
- Providers found → `booking_node`
- Empty list → `error_node`

---

### Node 3 — BookingAgent

**Goal:** Create the confirmed booking record and save the full pipeline trace.

**Steps:**
1. Takes `state["providers"][0]` — the top-ranked provider from MatchingAgent
2. Generates an 8-character booking code (`XY4F9K2A`) using `secrets.choice()` — cryptographically random (not `random.choice`)
3. Inserts a `Booking` row into PostgreSQL with `status = confirmed`
4. Calls `db.flush()` to get the auto-generated `booking.id` **without committing yet**
5. Inserts a `Trace` row with all 3 agent steps serialized as a JSON array — the full audit log
6. `db.commit()` — booking and trace are committed atomically in one transaction

**Output:** Returns a `booking_dict` with all booking fields, stored in `state["booking"]`.

---

### Error Node

Terminal fallback. Any node can set `state["error"]` to a string; routing will redirect to this node.
It logs the failure and passes the error message back in the HTTP response as `ErrorResponse`.

---

### Why LangGraph?

| Feature | Benefit |
|---------|---------|
| Shared `KhidmatState` | All nodes read/write one dict — no argument passing between functions |
| Conditional edges | Route to different nodes based on state (e.g. empty providers → error path) |
| RetryPolicy | Auto-retry individual nodes on transient failures (OpenAI timeout, DB flakiness) |
| PostgresSaver (future) | Checkpoint state to DB so interrupted pipelines can be resumed |
| Streaming (future) | Stream intermediate agent events to the mobile app in real-time |

---

## Database Schema

### `providers`
| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `name` | VARCHAR(150) | Provider's business name |
| `category` | ENUM | ac_technician, plumber, electrician, carpenter, cleaner, painter |
| `latitude / longitude` | Float | Used for Haversine distance in MatchingAgent |
| `rating` | Float (0–5) | Average customer rating |
| `reviews_count` | Integer | Capped at 100 in scoring formula |
| `is_active` | Boolean | Only `True` providers are ever matched |

### `bookings`
| Column | Type | Notes |
|--------|------|-------|
| `booking_code` | VARCHAR(20) | e.g. `XY4F9K2A` — shown to user |
| `session_id` | UUID | Links booking to its trace |
| `status` | ENUM | pending → confirmed → completed / cancelled |

### `traces`
| Column | Type | Notes |
|--------|------|-------|
| `session_id` | UUID UNIQUE | One trace per pipeline run |
| `steps` | JSON | List of TraceStep dicts from all 3 agents |

---

## Mobile App (Expo React Native)

```bash
cd khidmat-mobile-app
npm install
npx expo start
# W = open in browser, A = Android emulator
```

Set `EXPO_PUBLIC_API_BASE_URL` in `khidmat-mobile-app/.env`:
- Web / iOS simulator: `http://localhost:8000`
- Android emulator: `http://10.0.2.2:8000`
- Physical device: `http://<your-PC-LAN-IP>:8000`

---

## Implementation Roadmap

- [x] Phase 1 — Foundation (`config`, `database`, `main.py`)
- [x] Phase 2 — ORM Models (`Provider`, `Booking`, `Trace`)
- [x] Phase 3 — Pydantic Schemas (request/response shapes)
- [x] Phase 4.0 — Alembic migrations (tables created in PostgreSQL)
- [x] Phase 4.1 — `KhidmatState` TypedDict (`agents/state.py`)
- [x] Phase 4.2 — IntentNode (GPT-4o structured JSON extraction)
- [x] Phase 4.3 — MatchingNode (geocoding + composite scoring)
- [x] Phase 4.4 — BookingNode (booking + trace persistence)
- [x] Phase 4.5 — LangGraph compiled (`services/langgraph_services.py`)
- [ ] Phase 5 — Routes (`/api/v1/request`, `/booking`, `/trace`)
- [ ] Phase 6 — Seed Data (mock providers in Islamabad)
- [ ] Phase 7 — End-to-end test (`curl` full pipeline)
- [ ] Phase 8 — Mobile App integration (wire to real API)

---

## License

MIT
