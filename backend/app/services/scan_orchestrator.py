import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.crud import finding as finding_crud
from app.crud import scan as scan_crud
from app.models.scan import ScanStatus
from app.scanning.fetcher import FetchError, fetch_target
from app.scanning.registry import REGISTERED_CHECKS


def run_scan(db: Session, scan_id: uuid.UUID) -> None:
    """
    Run a single scan end to end: fetch the target once, run every
    registered check against that one fetch, persist the resulting
    findings, and transition the scan to COMPLETED or FAILED.

    This function is called by the worker (app/worker/tasks.py), never
    directly by an API route -- it does real network I/O and can take
    several seconds, which is exactly what a request handler must never
    block on. It takes a plain Session and a scan_id rather than a
    request-scoped dependency, precisely so it can also be called
    directly from a test with a throwaway session and no worker or
    Redis running at all (see tests/integration/test_scan_orchestrator.py).
    """
    scan = scan_crud.get_by_id(db, scan_id)
    if scan is None:
        # The scan row is gone by the time a worker picked up the job.
        # Scans are never hard-deleted today, so this shouldn't happen
        # in practice -- but a worker function should never assume
        # nothing has changed between "job enqueued" and "job running."
        return

    scan.status = ScanStatus.RUNNING
    scan.started_at = datetime.now(timezone.utc)
    db.add(scan)
    db.commit()

    try:
        context = fetch_target(scan.target.url)
    except FetchError as exc:
        _mark_failed(db, scan, error_message=str(exc))
        return

    try:
        for check in REGISTERED_CHECKS:
            for draft in check.run(context):
                finding_crud.create(
                    db,
                    scan_id=scan.id,
                    category=draft.category,
                    finding_type=draft.finding_type,
                    severity=draft.severity,
                    title=draft.title,
                    description=draft.description,
                    evidence=draft.evidence,
                )
    except Exception as exc:  # noqa: BLE001 - a misbehaving check must not crash the worker
        _mark_failed(db, scan, error_message=f"Scan failed while running checks: {exc}")
        return

    scan.status = ScanStatus.COMPLETED
    scan.completed_at = datetime.now(timezone.utc)
    db.add(scan)
    db.commit()


def _mark_failed(db: Session, scan, *, error_message: str) -> None:
    scan.status = ScanStatus.FAILED
    scan.error_message = error_message
    scan.completed_at = datetime.now(timezone.utc)
    db.add(scan)
    db.commit()
