import uuid

from sqlalchemy.orm import Session

from app.core.queue import enqueue_scan
from app.crud import finding as finding_crud
from app.crud import scan as scan_crud
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.user import User
from app.services import target_service


class ScanNotFoundError(Exception):
    """Raised when a scan id does not exist at all."""


class ScanAccessError(Exception):
    """Raised when a user attempts to access a scan outside their own organization."""


def create_scan(db: Session, *, current_user: User, target_id: uuid.UUID) -> Scan:
    """
    Create a queued scan record for a target and enqueue it for
    background processing.

    This function does NOT perform any scanning itself -- it creates a
    row with status=QUEUED and hands its id to the RQ worker queue
    (app/core/queue.py). The worker process (app/worker/tasks.py, run
    via worker_entrypoint.py) is what actually transitions the scan
    through running -> completed/failed and writes findings (see
    app/services/scan_orchestrator.py). That separation is exactly why
    this function returns immediately: the route that calls it
    responds with 202 Accepted and a scan id to poll, rather than
    blocking on the several seconds a real scan takes.

    Authorization is delegated to target_service.get_target_for_user --
    "can this user create a scan for this target" is the same question
    as "can this user see this target," so there is exactly one place
    that answers it, and this function reuses it rather than
    re-implementing the organization check.
    """
    target = target_service.get_target_for_user(db, current_user=current_user, target_id=target_id)
    scan = scan_crud.create_queued(db, target_id=target.id, triggered_by=current_user.id)

    # Hand the scan off to the worker and return immediately -- this is
    # the moment the "asynchronous by design" contract described in the
    # README actually happens. If Redis is unreachable, this raises and
    # the whole request fails loudly (a 500) rather than silently
    # leaving a scan queued forever with no one ever told; the test
    # suite stubs this function out (see tests/conftest.py) rather than
    # requiring a live Redis instance to run.
    enqueue_scan(scan.id)

    return scan


def get_scan_for_user(db: Session, *, current_user: User, scan_id: uuid.UUID) -> Scan:
    scan = scan_crud.get_by_id(db, scan_id)
    if scan is None:
        raise ScanNotFoundError("Scan not found.")

    # A scan has no organization_id column of its own -- its
    # organization is defined transitively through scan.target. Adding
    # a denormalized organization_id directly on Scan would risk it
    # drifting out of sync with the target's actual organization; going
    # through the relationship instead means there is only one place
    # that fact can ever live.
    if scan.target.organization_id != current_user.organization_id:
        # Same "not found" message as a genuinely missing scan id, for
        # the same anti-enumeration reason as target_service -- see
        # that module's _assert_same_organization docstring.
        raise ScanAccessError("Scan not found.")

    return scan


def list_findings_for_scan(db: Session, *, current_user: User, scan_id: uuid.UUID) -> list[Finding]:
    """Reuses get_scan_for_user for the same organization-scoping check, then reads its findings."""
    scan = get_scan_for_user(db, current_user=current_user, scan_id=scan_id)
    return finding_crud.list_by_scan(db, scan.id)


def list_scans_for_target(db: Session, *, current_user: User, target_id: uuid.UUID) -> list[Scan]:
    """Reuses target_service's organization-scoping check, then reads that target's scan history."""
    target = target_service.get_target_for_user(db, current_user=current_user, target_id=target_id)
    return scan_crud.list_by_target(db, target.id)
