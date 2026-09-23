from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from core.database import engine


# ── Lifespan ──────────────────────────────────────────────────────────────────
# `lifespan` is a special async context manager that FastAPI calls:
#   - BEFORE the first request  → code before `yield` runs (startup)
#   - AFTER the server shuts down → code after `yield` runs (shutdown)
#
# We use it here to verify the DB connection is alive when the app boots.
# If the DB is unreachable, we want to know immediately — not on the first user request.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    print("🚀 Starting Khidmat backend...")

    # Test the DB connection by running a trivial query
    # `text()` wraps a raw SQL string so SQLAlchemy can execute it
    with engine.connect() as connection:                             # Give me a database connection from the connection pool.
        connection.execute(text("SELECT 1"))
    print("✅ Database connection verified.")

    yield  # <── server is now running and handling requests

    # ── Shutdown ──────────────────────────────────────────────────────────────
    print("🛑 Shutting down. Closing DB connections...")
    engine.dispose()  # closes all pooled connections cleanly


# ── App Instance ──────────────────────────────────────────────────────────────
# We pass `lifespan=lifespan` so FastAPI knows to run our startup/shutdown logic.
# title, description, version appear in the auto-generated docs at /docs
app = FastAPI(
    title="Khidmat API",
    description="Agentic service orchestrator — finds and books local service providers.",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Routes ────────────────────────────────────────────────────────────────────
# A simple health check endpoint.
# Used by Docker, load balancers, and monitoring tools to check if the app is alive.
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "khidmat-backend"}