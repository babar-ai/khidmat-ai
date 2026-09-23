# ── Models Package ────────────────────────────────────────────────────────────
# Importing all models here serves two purposes:
#
# 1. Alembic: When alembic runs, it imports this file. Because Base.metadata
#    tracks every class that inherits from Base, all three models get registered
#    automatically — so Alembic knows which tables to CREATE / ALTER / DROP.
#
# 2. Convenience: Other files can do `from models import Provider, Booking, Trace`
#    instead of remembering which sub-module each class lives in.

from models.provider import Provider, ServiceCategory   # noqa: F401
from models.booking  import Booking,  BookingStatus     # noqa: F401
from models.trace    import Trace                       # noqa: F401
