# 🛠️ Khidmat AI — Agentic Service Orchestrator

> Find and book local service providers (plumbers, electricians, AC technicians, and more) using natural language — in **Urdu, Roman Urdu, or English**.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-4CAF50)](https://postgis.net)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docs.docker.com/compose)
[![Expo](https://img.shields.io/badge/Expo-React%20Native-000020?logo=expo)](https://expo.dev)

---

## 📖 What is Khidmat?

**Khidmat** (خدمت — meaning "service" in Urdu) is an AI-powered backend that takes a user's natural language request and orchestrates three intelligent agents to find and book the right service provider nearby.

**Example request:**
> *"Mujhe kal subah G-13 mein AC technician chahiye"*
> *(I need an AC technician in G-13 tomorrow morning)*

The system understands the intent, finds the best-rated nearby provider, and creates a booking — all automatically.

---

## 🏗️ Architecture

```
User Request (Urdu / Roman Urdu / English)
        │
        ▼
  IntentAgent          ← LLM (extracts intent from natural language)
  - Detects: service type, location, time, language
        │
        ▼
  MatchingAgent        ← PostgreSQL + PostGIS
  - Geocodes location
  - Fetches providers by category
  - Ranks by: distance (40%) + rating (40%) + reviews (20%)
        │
        ▼
  BookingAgent         ← PostgreSQL
  - Creates booking record
  - Generates confirmation code
  - Schedules reminder
        │
        ▼
  Response + Trace     ← Full reasoning log returned to client
```

---

## 🗂️ Project Structure

```
khidmat-ai/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   └── main.py             # FastAPI entrypoint, lifespan, routers
│   ├── core/
│   │   ├── config.py           # Pydantic Settings — reads .env
│   │   └── database.py         # SQLAlchemy engine, session, Base
│   ├── models/
│   │   ├── provider.py         # Provider ORM model + ServiceCategory enum
│   │   ├── booking.py          # Booking ORM model + BookingStatus enum
│   │   └── trace.py            # Trace ORM model (agent reasoning log)
│   ├── schemas/
│   │   ├── provider.py         # ProviderCreate, ProviderRead, ProviderSummary
│   │   ├── booking.py          # BookingCreate, BookingRead, BookingStatusUpdate
│   │   ├── trace.py            # TraceStep, TraceRead
│   │   ├── request.py          # ServiceRequest (POST body)
│   │   └── response.py         # ServiceResponse, IntentResult, ErrorResponse
│   ├── agents/                 # (Phase 4) IntentAgent, MatchingAgent, BookingAgent
│   ├── routers/                # (Phase 5) API route handlers
│   ├── services/               # (Phase 5) Business logic layer
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── khidmat-mobile/             # Expo React Native mobile app
├── docker-compose.yml          # PostgreSQL (PostGIS) + FastAPI
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js](https://nodejs.org/) (for the mobile app)

### 1. Clone the repo

```bash
git clone https://github.com/babar-ai/khidmat-ai.git
cd khidmat-ai
```

### 2. Configure environment variables

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and fill in:

```env
DATABASE_URL=postgresql+psycopg2://kidmat_user:kidmat_pass@db:5432/kidmat_db
OPENAI_API_KEY=your_openai_api_key_here
APP_ENV=development
```

### 3. Start the backend (Docker)

```bash
docker compose up
```

This starts:
- **PostgreSQL + PostGIS** on port `5432`
- **FastAPI backend** on port `8000` with hot-reload

### 4. Verify it's running

```bash
curl http://localhost:8000/health
# → {"status": "ok", "service": "khidmat-backend"}
```

Interactive API docs: **http://localhost:8000/docs**

---

## 📡 API Endpoints

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
  "provider": {
    "id": 7,
    "name": "Ali AC Services",
    "city": "Islamabad",
    "rating": 4.7,
    "distance_km": 1.2
  },
  "booking": {
    "booking_code": "XY4F9K2A",
    "status": "confirmed"
  },
  "trace": [
    {"step": 1, "agent": "IntentAgent",   "duration_ms": 312},
    {"step": 2, "agent": "MatchingAgent", "duration_ms": 87},
    {"step": 3, "agent": "BookingAgent",  "duration_ms": 45}
  ]
}
```

---

## 🗄️ Database: PostgreSQL + PostGIS

This project uses **PostGIS** — a spatial extension for PostgreSQL — to enable location-based provider search.

| | PostgreSQL | PostGIS |
|---|---|---|
| **What it is** | Relational database | Extension on top of PostgreSQL |
| **Adds** | Tables, SQL, indexes | Geometry types, spatial functions |
| **Used for** | All data storage | `ST_DWithin()`, `ST_Distance()` queries |

**Why PostGIS?** — Instead of pulling all providers into Python and computing distances, we can query the DB directly:

```sql
SELECT * FROM providers
WHERE ST_DWithin(location::geography, ST_MakePoint(73.04, 33.68)::geography, 5000);
```

---

## 📱 Mobile App (Expo)

```bash
cd khidmat-mobile
npm install
npm start
```

---

## 🗺️ Implementation Roadmap

- [x] Phase 1 — Foundation (`config`, `database`, `main.py`)
- [x] Phase 2 — ORM Models (`Provider`, `Booking`, `Trace`)
- [x] Phase 3 — Pydantic Schemas (request/response shapes)
- [ ] Phase 4 — Alembic Migrations (create tables in DB)
- [ ] Phase 5 — Agents (`IntentAgent`, `MatchingAgent`, `BookingAgent`)
- [ ] Phase 6 — Routes (`/api/v1/request`, `/booking`, `/trace`)
- [ ] Phase 7 — Seed Data (mock providers in Islamabad)
- [ ] Phase 8 — Mobile App integration

---

## 🤝 Contributing

Pull requests welcome. For major changes, open an issue first.

---

## 📄 License

MIT
