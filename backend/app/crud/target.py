import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.target import Target


def create(
    db: Session,
    *,
    organization_id: uuid.UUID,
    created_by: uuid.UUID | None,
    url: str,
    label: str,
) -> Target:
    target = Target(
        organization_id=organization_id,
        created_by=created_by,
        url=url,
        label=label,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def get_by_id(db: Session, target_id: uuid.UUID) -> Target | None:
    return db.get(Target, target_id)


def list_by_organization(db: Session, organization_id: uuid.UUID) -> list[Target]:
    stmt = (
        select(Target)
        .where(Target.organization_id == organization_id)
        .order_by(Target.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def deactivate(db: Session, target: Target) -> Target:
    """
    Soft delete: flips is_active to False rather than deleting the row.
    Scans reference targets by foreign key, and a compliance tool that
    silently lost the history of a site it used to monitor (just
    because someone stopped watching it) would undermine the whole
    point of having an audit trail.
    """
    target.is_active = False
    db.add(target)
    db.commit()
    db.refresh(target)
    return target
