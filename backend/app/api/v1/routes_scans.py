import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.database import get_database_session
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.user import User, UserRole
from app.schemas.finding import FindingRead
from app.schemas.scan import ScanCreateResponse, ScanRead
from app.services import scan_service
from app.services.scan_service import ScanAccessError, ScanNotFoundError
from app.services.target_service import TargetAccessError, TargetNotFoundError

# Two routers because these endpoints live under two different URL
# shapes: creating a scan is nested under the target it scans
# (POST /targets/{target_id}/scans), while checking a scan's status is
# a standalone resource lookup (GET /scans/{scan_id}). Both are
# included into api_router in app/api/v1/__init__.py.
target_scans_router = APIRouter(prefix="/targets", tags=["scans"])
scans_router = APIRouter(prefix="/scans", tags=["scans"])


@target_scans_router.post(
    "/{target_id}/scans",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_scan(
    target_id: uuid.UUID,
    db: Session = Depends(get_database_session),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
) -> ScanCreateResponse:
    """
    Create a queued scan record and hand it to the worker for background processing.

    202 Accepted (rather than 200/201) is a deliberate signal: the
    request has been accepted for processing, not completed. No actual
    scanning happens inside this request/response cycle -- an RQ
    worker process (see app/worker/tasks.py, run via
    worker_entrypoint.py) is what picks this scan up, runs checks
    against the target, and transitions its status. Callers are
    expected to poll GET /scans/{scan_id} for progress.
    """
    try:
        scan = scan_service.create_scan(db, current_user=current_user, target_id=target_id)
    except (TargetNotFoundError, TargetAccessError) as exc:
        # A user triggering a scan for a target that doesn't exist (or
        # isn't theirs) gets the identical 404 they'd get from
        # GET /targets/{target_id} -- one consistent answer to
        # "can you see this target" across every endpoint that asks it.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return ScanCreateResponse(scan_id=scan.id, status=scan.status)


@target_scans_router.get("/{target_id}/scans", response_model=list[ScanRead])
def list_target_scans(
    target_id: uuid.UUID,
    db: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> list[Scan]:
    """
    A target's scan history, most recent first -- this is what powers
    the scan timeline on a target's detail view. Any authenticated
    role can read it; only creating a new scan is restricted to
    admin/analyst (see create_scan above).
    """
    try:
        return scan_service.list_scans_for_target(db, current_user=current_user, target_id=target_id)
    except (TargetNotFoundError, TargetAccessError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@scans_router.get("/{scan_id}", response_model=ScanRead)
def get_scan(
    scan_id: uuid.UUID,
    db: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> Scan:
    """Any authenticated role can check the status of a scan belonging to their organization."""
    try:
        return scan_service.get_scan_for_user(db, current_user=current_user, scan_id=scan_id)
    except (ScanNotFoundError, ScanAccessError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@scans_router.get("/{scan_id}/findings", response_model=list[FindingRead])
def get_scan_findings(
    scan_id: uuid.UUID,
    db: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> list[Finding]:
    """
    List the findings produced by a scan. Returns an empty list (not a
    404 or 202) while a scan is still queued or running -- findings
    accumulate as checks complete, so an empty list is a legitimate,
    honest answer for "no findings yet," distinct from "this scan
    doesn't exist," which is still a 404.
    """
    try:
        return scan_service.list_findings_for_scan(db, current_user=current_user, scan_id=scan_id)
    except (ScanNotFoundError, ScanAccessError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
