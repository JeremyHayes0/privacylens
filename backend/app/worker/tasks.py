import uuid

from app.core.database import SessionLocal
from app.services.scan_orchestrator import run_scan


def run_scan_task(scan_id: str) -> None:
    """
    The function an RQ worker process actually executes.

    Opens its own database session -- a worker runs in a separate OS
    process from the API, so it can never share the API's
    request-scoped session (see app/core/database.get_database_session).
    All real logic is delegated to scan_orchestrator.run_scan, which
    has no knowledge of RQ, Redis, or worker processes at all: that
    keeps the core scanning logic testable by calling run_scan directly
    with a throwaway session, without a running worker or Redis.
    """
    db = SessionLocal()
    try:
        run_scan(db, uuid.UUID(scan_id))
    finally:
        db.close()
