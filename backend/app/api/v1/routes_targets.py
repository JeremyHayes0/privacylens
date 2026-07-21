import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.database import get_database_session
from app.models.target import Target
from app.models.user import User, UserRole
from app.schemas.target import TargetCreate, TargetRead
from app.services import target_service
from app.services.target_service import TargetAccessError, TargetNotFoundError

router = APIRouter(prefix="/targets", tags=["targets"])


@router.post("", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
def create_target(
    target_in: TargetCreate,
    db: Session = Depends(get_database_session),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
) -> Target:
    """
    Add a website for PrivacyLens to monitor.

    Restricted to admin/analyst roles: a viewer can see what's being
    monitored and read scan results, but changing what's monitored is a
    mutating, org-configuration-level action -- the same reasoning
    that restricts DELETE below.
    """
    return target_service.create_target(db, current_user=current_user, target_in=target_in)


@router.get("", response_model=list[TargetRead])
def list_targets(
    db: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> list[Target]:
    """Any authenticated role can view the targets belonging to their own organization."""
    return target_service.list_targets_for_user(db, current_user=current_user)


@router.get("/{target_id}", response_model=TargetRead)
def get_target(
    target_id: uuid.UUID,
    db: Session = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
) -> Target:
    try:
        return target_service.get_target_for_user(db, current_user=current_user, target_id=target_id)
    except (TargetNotFoundError, TargetAccessError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{target_id}", response_model=TargetRead)
def deactivate_target(
    target_id: uuid.UUID,
    db: Session = Depends(get_database_session),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
) -> Target:
    """
    "Delete" is a soft delete (is_active=False), not a row deletion.
    Scans reference targets by foreign key, and silently losing the
    history of a site PrivacyLens used to monitor -- just because
    someone stopped watching it -- would undermine the audit trail a
    compliance-adjacent tool needs to stay credible.
    """
    try:
        return target_service.deactivate_target(db, current_user=current_user, target_id=target_id)
    except (TargetNotFoundError, TargetAccessError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
