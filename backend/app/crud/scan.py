import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scan import Scan, ScanStatus


def create_queued(db: Session, *, target_id: uuid.UUID, triggered_by: uuid.UUID | None) -> Scan:
    """
    Insert a scan row in QUEUED status. This function performs no
    scanning itself -- it is exactly as "dumb" as every other CRUD
    function in this layer. Enqueueing the row for the worker to pick
    up (app/core/queue.py, app/worker/tasks.py) is the caller's
    responsibility (see scan_service.create_scan), not this function's;
    this one's only job is to make sure the row exists.
    """
    scan = Scan(target_id=target_id, triggered_by=triggered_by, status=ScanStatus.QUEUED)
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def get_by_id(db: Session, scan_id: uuid.UUID) -> Scan | None:
    return db.get(Scan, scan_id)


def list_by_target(db: Session, target_id: uuid.UUID) -> list[Scan]:
    stmt = select(Scan).where(Scan.target_id == target_id).order_by(Scan.created_at.desc())
    return list(db.execute(stmt).scalars().all())
