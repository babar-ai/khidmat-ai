"""
GET /api/v1/trace/{session_id} — fetch the full agent reasoning trace for a pipeline run.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models.trace import Trace
from schemas.trace import TraceRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Trace"])


@router.get("/trace/{session_id}", response_model=TraceRead)
def get_trace(session_id: str, db: Session = Depends(get_db)):
    """
    Fetch the full agent reasoning trace for a pipeline run.

    The session_id is returned in the POST /api/v1/request response.
    Use this to inspect what each agent did, how long it took, and why.
    """
    trace = db.query(Trace).filter(Trace.session_id == session_id).first()
    if not trace:
        raise HTTPException(status_code=404, detail=f"No trace found for session '{session_id}'.")
    return trace
