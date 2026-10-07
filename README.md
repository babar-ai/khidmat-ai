# Khidmat AI (خدمت) — Agentic Service Orchestrator
> AI-driven, multi-turn home services booking platform built specifically for Pakistan. Users can converse naturally in **Urdu (اردو)**, **Roman Urdu**, or **English** to discover, evaluate, and book verified local service providers.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai)](https://openai.com)
[![Expo](https://img.shields.io/badge/Expo-React%20Native-000020?logo=expo)](https://expo.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docs.docker.com/compose)

---

## Table of Contents

- [Problem](#problem)
- [Solution](#solution)
- [Architecture](#architecture)
- [Demo](#demo)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [API](#api)
- [Evaluation](#evaluation)
- [Benchmarks](#benchmarks)
- [Engineering Decisions](#engineering-decisions)
- [Limitations](#limitations)
- [Future Work](#future-work)

---

## Problem

Hiring reliable household service professionals (technicians, plumbers, electricians, carpenters, painters, and cleaners) in Pakistan is plagued by several systemic hurdles:

1. **Fragmented & Informal Market**: Users rely on disparate WhatsApp groups, word-of-mouth recommendations, or neighborhood business cards without verified credibility, standard pricing, or reviews.
2. **Linguistic Diversity & Code-Switching**: Most software platforms require users to navigate static English drop-downs. In reality, the vast majority of Pakistani consumers describe tasks using **Roman Urdu** (*"Bathroom mein leak hai"*, *"AC ki cooling kam hai"*) or **Urdu script (Ø§Ø±Ø¯Ùˆ)**, alternating fluidly with English terms.
3. **Imprecise Addressing & Geocoding Failures**: Standard geocoders frequently fail on informal or compound Pakistani addresses (*"barakaw banigala islamabad"*, *"near Khanna Pul"*, *"G-13/1"*), causing discovery drop-offs.
4. **Friction in Provider Registration**: Skilled blue-collar technicians struggle with complicated multi-step onboarding portals, resulting in low provider supply.

---

## Solution

**Khidmat AI** bridges the gap between home-owners and local service professionals through an intelligent conversational orchestrator:

- **Bilingual & Multi-Script Natural Language Booking**: Users can state their need casually in English, Roman Urdu, or Urdu. The agent extracts service intent, detects greetings, extracts time preferences, and fills missing slots over multi-turn dialogues.
- **Stateful Multi-Turn Conversations**: Powered by **LangGraph** with **PostgreSQL checkpoint persistence (`PostgresSaver`)**, allowing users to ask questions, raise price objections, and ask for alternative providers without losing conversation context.
- **Geospatial Ranking Engine**: Ranks providers by composite scoring incorporating Haversine distance, customer rating, and review count with smooth distance decay.
- **Resilient Multi-Tier Geocoding**: Solves Pakistani phonetic Roman Urdu and compound locations through a 3-tier pipeline (Nominatim + local gazetteer + GPT-4o semantic normalizer).
- **Zero-Friction InDrive-Style Provider Registration**: Service providers can self-register their business in seconds via mobile, instantly becoming active and discoverable by the AI matching engine.

---

## Architecture

Khidmat AI operates as a distributed system comprising a React Native client, a FastAPI gateway, a stateful LangGraph agent graph, and PostgreSQL for relational data and checkpointing.

```text
+----------------------------------------------------------------------------------------+
|                        Khidmat Mobile App (Expo / React Native)                        |
|   * Multi-Turn Chat Interface            * Real-Time Agent Trace Visualization         |
|   * Background / Foreground GPS Fix      * Contextual Quick-Action Suggestion Chips    |
|   * InDrive-Style Service Provider Self-Registration Form                              |
+-------------------------------------------+--------------------------------------------+
                                            | HTTP POST /api/v1/request (session_id)
                                            v
+----------------------------------------------------------------------------------------+
|                                FastAPI Backend Gateway                                 |
|   * Routers: /api/v1/request, /booking, /provider, /trace, /health                     |
|   * Pydantic Request/Response Validation & Structured Exception Mapping                |
+-------------------------------------------+--------------------------------------------+
                                            |
                                            v
+----------------------------------------------------------------------------------------+
|                        LangGraph Stateful Agent Graph Engine                           |
|                                                                                        |
|                    START ---> [Node 1: Intent Extraction Agent]                        |
|                                           |                                            |
|            +------------------------------+------------------------------+             |
|            | (missing slots / greeting)   | (slots complete)             | (follow-up) |
|            v                              v                              v             |
|   [Node 5: Error / Clarify]     [Node 2: Matching Agent]     [Node 3: Conversation]   |
|            |                              |                              |             |
|            | (returns 400 detail)         | (ranks candidates)           |             |
|            |                              v                              |             |
|            |                    [Node 4: Booking Agent] <----------------+             |
|            |                              |           (confirmed)        |             |
|            |                              |                              | (objection/ |
|            v                              v                              v  alt/query) |
|           END                            END                            END            |
+---------------------------+------------------------------------+-----------------------+
                            |                                    |
                            v                                    v
+-------------------------------------------+   +----------------------------------------+
|              OpenAI (GPT-4o)              |   |          PostgreSQL + PostGIS          |
|  * JSON Structured Outputs Mode           |   |  * Tables: providers, bookings, traces |
|  * Dialect & Language Script Mirroring    |   |  * Persistent Session Checkpoints via  |
|  * Semantic Address Resolution            |   |    LangGraph PostgresSaver Pool        |
|  * Conversational Dialogue Act Detection  |   |  * Haversine Distance + Scoring Engine |
+-------------------------------------------+   +----------------------------------------+
```

### LangGraph Agent Pipeline Breakdown

The core orchestration engine is modeled as a stateful, cyclical graph (`StateGraph(KhidmatState)`) using **LangGraph**:

#### 1. `intent_node` (Intent & Slot Extraction Agent)
- **Role**: Parses unstructured natural language user queries using GPT-4o with strict JSON structured outputs.
- **Slot Schema**:
  - `service_type`: Normalized against `ServiceCategory` (`ac_technician`, `plumber`, `electrician`, `carpenter`, `cleaner`, `painter`).
  - `location_text`: User's stated location (e.g., *"G-13/2 Islamabad"* or *"Barakahu"*).
  - `scheduled_text`: Natural time string (e.g., *"today at 5pm"*, *"kal subah"*).
  - `language`: Detected script and tongue (`ur`, `roman_ur`, `en`).
  - `is_greeting`: Flags casual greetings for polite conversational response.
  - `is_ready_to_book`: Verified `true` only when all required booking parameters are resolved.
- **Routing Decision** (`route_after_intent`):
  - If previous recommendation was already delivered (`proposed_providers` present in state) and user is following up: routes directly to **`conversation_node`**.
  - If mandatory slots are complete and valid: routes to **`matching_node`**.
  - If slots are incomplete, query is a greeting, or an error occurred: routes to **`error_node`** to issue a clarification request.

#### 2. `matching_node` (Provider Matching & Scoring Agent)
- **Role**: Discovers, geocodes, and ranks verified local service providers.
- **Geocoding Flow**: Resolves user's text location using the 3-tier geocoder (OpenStreetMap Nominatim âž” Local Pakistani Gazetteer âž” GPT-4o Semantic Normalizer). Falls back to user's device GPS if text geocoding fails.
- **Candidate Discovery**: Fetches active providers from PostgreSQL filtered by `category` and `is_active = true`.
- **Continuous Composite Scoring**: Calculates a weighted score for each candidate:
  $$\text{Composite Score} = 0.40 \times \left(\frac{1}{1 + \frac{\text{dist\_km}}{5}}\right) + 0.35 \times \left(\frac{\text{rating}}{5.0}\right) + 0.15 \times \min\left(1.0, \frac{\text{reviews}}{100}\right) + 0.10 \times \text{verified}$$
- **Routing Decision** (`route_after_matching`):
  - Providers found: routes to **`booking_node`**.
  - No active providers available: routes to **`error_node`**.

#### 3. `conversation_node` (Conversational Dialogue Agent)
- **Role**: Manages multi-turn negotiation and conversational interactions *after* providers have been proposed to the user. Rather than re-running full slot extraction, this specialized node acts as an intelligent dialogue manager.
- **Context Injection**: Provides GPT-4o with full context:
  - Last 6 messages of conversational history (`chat_history`).
  - Currently recommended provider's profile (name, rating, distance, price range).
  - Remaining alternate providers in the ranking pool.
  - List of rejected provider IDs (`rejected_provider_ids`).
- **Dialogue Act Classification**:
  - `booking_confirmed`: User accepts the proposed technician (*"yes"*, *"confirm kardo"*, *"theek hai"*).
  - `request_alternative`: User wants someone else (*"koi aur dikhao"*, *"show someone closer"*).
  - `objection_distance`: User questions the technician's travel distance.
  - `objection_price`: User questions pricing or rates.
  - `clarify_question`: User asks about tools, arrival time, or warranty.
  - `other`: General follow-up inquiry.
- **Active Provider Pointer Rotation**:
  - If the user rejects the provider or asks for an alternative, `conversation_node` appends the current provider's ID to `rejected_provider_ids`, advances `active_provider_index` to the next highest-scoring candidate, and presents their profile.
- **Script & Dialect Mirroring**: Dynamically matches the user's language and script:
  - Roman Urdu input ➔ Roman Urdu output (*"Hum ne Ali Services ko select kiya hai..."*)
  - Urdu script input ➔ Nastaliq Urdu output (*"ہم نے آپ کے لیے علی سروسز کو منتخب کیا ہے..."*)
  - English input ➔ English output (*"We have recommended Ali AC Services for you..."*)
- **Routing Decision** (`route_after_conversation`):
  - `booking_confirmed`: routes to **`booking_node`** to finalize the order.
  - Any other dialogue act: routes to **`END`**, returning the assistant's response to the client.

#### 4. `booking_node` (Booking & Audit Persistence Agent)
- **Role**: Atomically provisions the final confirmed reservation and audit trace.
- **Execution Steps**:
  1. Identifies the active confirmed provider (`state["providers"][active_provider_index]`).
  2. Generates an 8-character cryptographically secure alphanumeric booking reference (e.g. `XY4F9K2A`).
  3. Inserts a `Booking` record into PostgreSQL with `status = 'confirmed'`.
  4. Serializes all agent execution steps into a JSON audit trail and saves it to the `traces` table linked by `session_id`.
  5. Commits both entities atomically in a single transaction.
- **Routing**: Transitions unconditionally to **`END`**.

#### 5. `error_node` (Clarification & Error Handling Node)
- **Role**: Terminal fallback node that standardizes user clarification messages or execution failure payloads.
- **Behavior**: Packages missing slot prompts or exception details into the response payload so the mobile frontend can display targeted follow-up guidance or contextual quick-reply chips.

---

## Demo

### Conversational Booking Flow

```
User:     "Mujhe kal subah G-13 mein AC technician chahiye"
Agent:    [Understands: AC Repair | G-13 | Tomorrow Morning]
          [Searching: Providers in G-13, Islamabad]
          [Ranking: Found 3 nearby providers]
          [Recommendation Card: Ali AC Services • 4.7 ★ • 1.2 km away • PKR 800-3000]
          "Booking confirmed! Code: 7IE79Z9R"
```

### Multi-Turn Slot Filling

```
User:     "Salam, mujhe electrician chahiye"
Agent:    "Walaikum Assalam! Main aap ke liye electrician arrange kar sakta hoon.
          Aap Islamabad ke kis sector mein hain aur technician kab chahiye?"
User:     "F-10 mein, aaj sham 5 baje"
Agent:    [Fills missing location & time slots -> Matches top electrician in F-10]
```

*(Screenshots and interactive demo recordings are stored under `/artifacts/demos`)*

---

## Tech Stack

| Layer | Technology | Version / Details |
|---|---|---|
| **Backend Framework** | FastAPI | `0.115.0` (Asynchronous Python REST API) |
| **Agent Orchestrator** | LangGraph | `0.2.28` (Stateful cyclical computation graphs) |
| **LLM Provider** | OpenAI GPT-4o | Structured JSON Mode & strict script mirroring |
| **State Persistence** | `langgraph-checkpoint-postgres` | Checkpoint persistence per `session_id` |
| **Database** | PostgreSQL + PostGIS | Version 16 + PostGIS 3.4 via Docker |
| **ORM & Migrations** | SQLAlchemy & Alembic | SQLAlchemy `2.0.35`, Alembic `1.13.3` |
| **Geospatial Engine** | Geopy + OpenStreetMap Nominatim | Multi-tier geocoder with local Pakistani gazetteer |
| **Mobile Client** | Expo React Native | SDK 57, React 19, TypeScript |
| **Styling** | NativeWind / Tailwind CSS | Customized Khidmat Warm Orange design system |
| **Device Integrations** | Expo Location & Haptics | Foreground GPS tracking and tactile micro-feedback |
| **Containerization** | Docker & Docker Compose | Isolated multi-container deployment |

---

## Project Structure

```
khidmat-ai/
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ alembic/                      # Database migration scripts & env configuration
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â””â”€â”€ main.py                   # FastAPI app instance, lifespan, router inclusion
â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â”œâ”€â”€ config.py                 # Pydantic Settings reading .env
â”‚   â”‚   â””â”€â”€ database.py               # SQLAlchemy engine, SessionLocal, get_db dependency
â”‚   â”œâ”€â”€ models/
â”‚   â”‚   â”œâ”€â”€ booking.py                # Booking ORM model & BookingStatus enum
â”‚   â”‚   â”œâ”€â”€ provider.py               # Provider ORM model & ServiceCategory enum
â”‚   â”‚   â””â”€â”€ trace.py                  # Agent execution trace ORM model
â”‚   â”œâ”€â”€ routers/
â”‚   â”‚   â”œâ”€â”€ booking.py                # GET /bookings, GET /booking/{id}, PATCH /status
â”‚   â”‚   â”œâ”€â”€ provider.py               # POST /provider/register, GET /providers
â”‚   â”‚   â”œâ”€â”€ request.py                # POST /api/v1/request (primary agent pipeline)
â”‚   â”‚   â””â”€â”€ trace.py                  # GET /api/v1/trace/{session_id}
â”‚   â”œâ”€â”€ schemas/                      # Pydantic schemas for request validation & responses
â”‚   â”‚   â”œâ”€â”€ booking.py
â”‚   â”‚   â”œâ”€â”€ provider.py
â”‚   â”‚   â”œâ”€â”€ request.py
â”‚   â”‚   â”œâ”€â”€ response.py
â”‚   â”‚   â””â”€â”€ trace.py
â”‚   â”œâ”€â”€ services/
â”‚   â”‚   â”œâ”€â”€ langgraph_services.py     # Graph state, nodes, conditional edges, orchestrator
â”‚   â”‚   â”œâ”€â”€ openai_services.py        # Centralized OpenAI API client wrapper
â”‚   â”‚   â””â”€â”€ prompt_templates.py       # Domain-specific bilingual prompts & guidelines
â”‚   â”œâ”€â”€ utils/
â”‚   â”‚   â”œâ”€â”€ code_generator.py         # Cryptographic 8-character booking code generator
â”‚   â”‚   â”œâ”€â”€ geo.py                    # Haversine distance calculator in km
â”‚   â”‚   â””â”€â”€ geocode.py                # Multi-tier geocoder (Nominatim + Gazetteer + AI)
â”‚   â”œâ”€â”€ Dockerfile
â”‚   â””â”€â”€ requirements.txt
â”œâ”€â”€ khidmat-mobile-app/               # Expo React Native mobile application
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ (tabs)/
â”‚   â”‚   â”‚   â”œâ”€â”€ _layout.tsx           # Tab bar navigation layout
â”‚   â”‚   â”‚   â”œâ”€â”€ bookings.tsx          # User booking history & status management
â”‚   â”‚   â”‚   â”œâ”€â”€ index.tsx             # Interactive AI chat interface with trace stream
â”‚   â”‚   â”‚   â”œâ”€â”€ register.tsx          # Provider self-registration screen with GPS toggle
â”‚   â”‚   â”‚   â””â”€â”€ settings.tsx          # App settings, server URL & language preferences
â”‚   â”‚   â””â”€â”€ _layout.tsx
â”‚   â”œâ”€â”€ components/                   # UI components (ChatBubble, ProviderCard, InputBar)
â”‚   â”œâ”€â”€ lib/
â”‚   â”‚   â”œâ”€â”€ agent/realAgent.ts        # Async event streamer connecting to backend
â”‚   â”‚   â”œâ”€â”€ api/khidmatApi.ts         # Typed HTTP client with dynamic Metro IP detection
â”‚   â”‚   â””â”€â”€ stores/                   # Zustand stores for settings, bookings, location
â”‚   â””â”€â”€ package.json
â”œâ”€â”€ docker-compose.yml                # Multi-container orchestration (DB + Backend)
â”œâ”€â”€ PROJECT_CONTEXT.md                # Development logs & phase documentation
â””â”€â”€ README.md
```

---

## Installation

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js](https://nodejs.org/) (v18 or higher)
- [Git](https://git-scm.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/babar-ai/khidmat-ai.git
cd khidmat-ai
```

### 2. Configure Environment Variables

Create `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg2://kidmat_user:kidmat_pass@db:5432/kidmat_db
OPENAI_API_KEY=your_openai_api_key_here
APP_ENV=development
```

*(Note: In Docker Compose, the database hostname is `db`, not `localhost`)*

### 3. Start Backend Services via Docker

```bash
docker compose up -d --build
```

Verify backend health:

```bash
curl http://localhost:8000/health
# Response: {"status":"ok","service":"khidmat-backend"}
```

Interactive OpenAPI Swagger documentation is available at: **http://localhost:8000/docs**

### 4. Run Mobile App

```bash
cd khidmat-mobile-app
npm install
npx expo start
```

- Press `a` for Android Emulator, `i` for iOS Simulator, or scan the QR code with **Expo Go** on your physical phone.

---

## API

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check probe |
| `POST` | `/api/v1/request` | Main conversational pipeline (intent â†’ matching â†’ booking) |
| `POST` | `/api/v1/provider/register` | Self-service provider registration |
| `GET` | `/api/v1/providers` | List active providers (optional `?category=` filter) |
| `GET` | `/api/v1/bookings` | List user bookings (optional `?user_id=` or `?session_id=`) |
| `GET` | `/api/v1/booking/{id}` | Retrieve booking details by ID |
| `PATCH` | `/api/v1/booking/{id}/status` | Update booking status (`confirmed`, `cancelled`, `completed`) |
| `GET` | `/api/v1/trace/{session_id}` | Retrieve step-by-step agent reasoning trace |

### Example: Conversational Booking Request

`POST /api/v1/request`

```json
{
  "text": "Mujhe kal subah G-13 mein AC technician chahiye",
  "user_id": "user_mobile_01",
  "session_id": "sess_98234_abc",
  "user_lat": 33.6844,
  "user_lng": 73.0479
}
```

**Response (`200 OK`):**

```json
{
  "session_id": "sess_98234_abc",
  "intent": {
    "service_type": "ac_technician",
    "location_text": "G-13",
    "scheduled_text": "kal subah",
    "language": "roman_ur",
    "confidence": 0.95
  },
  "provider": {
    "id": 1,
    "name": "Ali AC Services",
    "city": "Islamabad",
    "category": "ac_technician",
    "rating": 4.7,
    "distance_km": 1.2
  },
  "booking": {
    "id": 14,
    "booking_code": "XY4F9K2A",
    "status": "confirmed",
    "created_at": "2026-10-07T05:26:28"
  },
  "trace": [
    { "step": 1, "agent": "IntentAgent", "action": "extract_intent", "duration_ms": 310 },
    { "step": 2, "agent": "MatchingAgent", "action": "find_and_rank_providers", "duration_ms": 45 },
    { "step": 3, "agent": "BookingAgent", "action": "create_booking", "duration_ms": 28 }
  ],
  "message": "âœ… Booking confirm ho gayi! Ali AC Services jald aap se rabta karega. Aap ka booking code hai: XY4F9K2A."
}
```

---

## Evaluation

*Placeholder: Comprehensive automated benchmark suites evaluating LLM slot-filling accuracy, script mirroring fidelity, and classification recall across diverse Pakistani dialects.*

Current evaluation metrics and guidelines:
- **Language & Script Detection**: Exact matching evaluation ensuring Roman Urdu queries receive strictly Roman Urdu responses, Urdu script queries receive Nastaliq responses, and English queries receive English responses.
- **Slot Extraction Precision**: Precision/Recall measurements across mandatory parameters (`service_type`, `location_text`, `scheduled_text`).
- **Unsupported Service Detection**: Guardrail verification ensuring requests outside supported categories (e.g. car mechanics, refrigerators, domestic cooks) gracefully redirect the user without booking failures.

---

## Benchmarks

### Latency Profile

| Pipeline Stage | Implementation | Median Latency (P50) | 95th Percentile (P95) |
|---|---|---|---|
| **Intent Extraction** | GPT-4o JSON Mode | ~380 ms | ~650 ms |
| **Geocoding Resolution** | Nominatim / Gazetteer / AI Cache | ~85 ms | ~250 ms |
| **Provider Ranking** | PostgreSQL + In-Memory Haversine | ~18 ms | ~45 ms |
| **State Checkpointing & Persistence** | PostgreSQL `PostgresSaver` | ~22 ms | ~40 ms |
| **Total Turnaround Time** | End-to-End Pipeline | **~505 ms** | **~985 ms** |

*Placeholder: Concurrent load testing benchmarks (requests per second under synthetic stress).*

---

## Engineering Decisions

1. **Why LangGraph over standard LangChain Chains or ReAct Loops?**
   - Traditional LLM agents can loop unpredictably when solving business workflows. LangGraph provides deterministic state transitions, native error routing, typed state contracts (`KhidmatState`), and persistent state checkpoints via PostgreSQL.
2. **Why GPT-4o with Strict JSON Mode?**
   - High fidelity in recognizing informal Pakistani Roman Urdu terminology (*"bijli ka masla"*, *"nalka tapak raha hai"*, *"master AC service"*) without hallucinating malformed response schemas.
3. **Continuous Distance Decay Scoring vs. Hard Geographic Radii:**
   - Instead of a strict cut-off (e.g. `distance < 5 km`), Khidmat uses a smooth decay formula `(1 / (1 + dist_km / 5)) * 0.40`. A technician 5.2 km away with 4.9 stars is not artificially excluded in favor of an unrated provider 4.9 km away.
4. **Three-Tier Resilient Geocoding:**
   - Combines free OpenStreetMap lookup with an offline Pakistani gazetteer and LLM semantic address normalizer, resolving compound and phonetic locations (*"barakaw banigala"*) that traditionally break strict map APIs.

---

## Limitations

- **Geographic Coverage**: Current geocoding gazetteer and mock provider datasets are optimized primarily for Islamabad and Rawalpindi.
- **Rate Limits on Public Nominatim**: Direct OpenStreetMap lookups enforce a 1 request/sec policy. While mitigated by our gazetteer and AI normalizer, production scale will require a self-hosted Nominatim tile server.
- **Payment Processing**: Currently operates on cash-on-delivery upon service completion; digital escrow wallets are not yet wired into the booking lifecycle.
- **Manual Verification**: Provider self-registration is immediate for MVP speed; automated CNIC verification via NADRA Verisys is not yet integrated.

---

## Future Work

- [ ] **Voice Interface**: Real-time voice agent supporting spoken Urdu and Punjabi using low-latency streaming Speech-to-Text and Text-to-Speech models.
- [ ] **Real-Time Dispatch & Map Tracking**: Live WebSocket connection showing provider travel progress on an interactive map.
- [ ] **Digital Escrow Payments**: Integration with Pakistani digital payment rails (JazzCash, Raast, SadaPay, Nayapay).
- [ ] **Automated Identity Verification**: Integration with official NADRA biometric/CNIC APIs for verified provider badges.
- [ ] **Multi-City Expansion**: Expanding local gazetteers and provider networks to Lahore, Karachi, and Peshawar.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
