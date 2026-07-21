import uuid

from sqlalchemy.orm import Session

from app.models.organization import Organization


def create(db: Session, *, name: str) -> Organization:
    organization = Organization(name=name)
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


def get_by_id(db: Session, organization_id: uuid.UUID) -> Organization | None:
    return db.get(Organization, organization_id)
