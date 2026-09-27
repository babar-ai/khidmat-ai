from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ── Point Alembic at our models ───────────────────────────────────────────────
# This is the CRITICAL change from the boilerplate.
#
# We import Base from our database module — Base.metadata contains the full
# schema (every table/column) of all models that inherit from Base.
#
# We also import all models (via models/__init__.py) so they register themselves
# with Base.metadata before autogenerate runs. If a model is not imported here,
# Alembic won't know the table exists and won't generate a migration for it.
from core.database import Base       # noqa: E402
import models                        # noqa: E402, F401 — triggers all model imports

target_metadata = Base.metadata      # Alembic reads this to diff against the live DB


# ── Override the DB URL from .env ─────────────────────────────────────────────
# alembic.ini has a placeholder for sqlalchemy.url.
# We override it here with the real value from our Settings object.
# This means you never hardcode the DB URL in two places.
from core.config import settings     # noqa: E402
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """
    Offline mode: generates SQL scripts without connecting to the DB.
    Useful for reviewing what Alembic will do before running it.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter function that tells Alembic which DB objects to manage.

    PostGIS adds dozens of internal tables (spatial_ref_sys, tiger schema, topology schema etc.)
    into the public schema. Without this filter, Alembic would try to DROP all of them
    thinking they don't belong to our app.

    We only manage objects that come from our models (not reflected from the DB).
    `reflected=True` means Alembic found it in the DB but NOT in our models.
    `compare_to is None` means it has no equivalent in our codebase.
    """
    if type_ == "table" and reflected and compare_to is None:
        return False  # skip PostGIS system tables
    return True


def run_migrations_online() -> None:
    """
    Online mode: connects to the DB and runs migrations directly.
    This is what `alembic upgrade head` uses.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,       # detects column type changes
            include_object=include_object,  # skip PostGIS internal tables
        )

        with context.begin_transaction():
            context.run_migrations()



if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
