from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from core.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
# The engine manages the actual TCP connections to PostgreSQL.
# It keeps a "pool" of connections open so the app doesn't reconnect on every request.

engine = create_engine(
    settings.DATABASE_URL,
    echo=(settings.APP_ENV == "development"),       # prints every SQL query in dev — very useful for learning
    pool_pre_ping=True,                             # SQLAlchemy maintains a connection pool and reuse it 
)


# ── Session Factory ───────────────────────────────────────────────────────────
# SessionLocal is a CLASS (a factory), not a session itself.
# Every time you call SessionLocal() you get a NEW session object.
# A session = one unit of work with the DB (begin → queries → commit/rollback → close)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,                            # we control when to commit (safer)
    autoflush=False,                             # we control when pending changes are sent to DB
) 



# ── Base Class ────────────────────────────────────────────────────────────────
# All SQLAlchemy ORM models (tables) will inherit from Base.
# Base keeps a registry of all models(Tables in SQL) — Alembic reads this to know which tables to create.
class Base(DeclarativeBase):
    pass


# ── Dependency (for FastAPI routes) ──────────────────────────────────────────
# This is a generator function used with FastAPI's Depends() system.
# It gives a route a fresh DB session, and ALWAYS closes it after the request finishes.
#
# How it works:
#   1. `db = SessionLocal()` — opens a new session
#   2. `yield db`            — hands it to the route function
#   3. `finally: db.close()` — runs AFTER the route returns (even if it crashes)

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
