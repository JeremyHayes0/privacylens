import uuid

from sqlalchemy.orm import Session

from app.crud import target as target_crud
from app.models.target import Target
from app.models.user import User
from app.schemas.target import TargetCreate


class TargetNotFoundError(Exception):
    """Raised when a target id does not exist at all."""


class TargetAccessError(Exception):
    """Raised when a user attempts to access a target outside their own organization."""


def create_target(db: Session, *, current_user: User, target_in: TargetCreate) -> Target:
    """
    Add a new target, scoped to the current user's organization. There
    is no cross-organization concern here (there's nothing to check
    against yet) -- the ownership rule only matters on the read/write
    paths that resolve an *existing* target by id, which is why the
    interesting logic lives in get_target_for_user below, not here.
    """
    return target_crud.create(
        db,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        url=target_in.url,
        label=target_in.label,
    )


def list_targets_for_user(db: Session, *, current_user: User) -> list[Target]:
    return target_crud.list_by_organization(db, current_user.organization_id)


def get_target_for_user(db: Session, *, current_user: User, target_id: uuid.UUID) -> Target:
    """
    The single choke point for "does this target exist, and can this
    user see it." Every route (and scan_service, which needs to check
    a target before creating a scan against it) resolves a target by
    id through this function rather than calling target_crud.get_by_id
    directly -- that way the organization check can't be accidentally
    skipped by a new call site that forgets to add it.
    """
    target = target_crud.get_by_id(db, target_id)
    if target is None:
        raise TargetNotFoundError("Target not found.")
    _assert_same_organization(current_user, target)
    return target


def deactivate_target(db: Session, *, current_user: User, target_id: uuid.UUID) -> Target:
    target = get_target_for_user(db, current_user=current_user, target_id=target_id)
    return target_crud.deactivate(db, target)


def _assert_same_organization(current_user: User, target: Target) -> None:
    """
    SECURITY: enforces organization-scoped data isolation for targets.

    Deliberately raises the *same* exception type and message
    (TargetAccessError, "Target not found.") that a genuinely
    nonexistent id would raise -- both are mapped to an identical 404
    by the route layer. Returning a distinct 403 for "this target
    exists, just not in your org" would itself leak information: it
    would let a caller enumerate valid target IDs belonging to other
    organizations just by watching which ids return 403 vs 404.
    """
    if target.organization_id != current_user.organization_id:
        raise TargetAccessError("Target not found.")
