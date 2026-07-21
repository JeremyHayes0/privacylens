import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finding import Finding, FindingCategory, FindingSeverity, FindingType


def create(
    db: Session,
    *,
    scan_id: uuid.UUID,
    category: FindingCategory,
    finding_type: FindingType,
    severity: FindingSeverity,
    title: str,
    description: str,
    evidence: dict,
) -> Finding:
    finding = Finding(
        scan_id=scan_id,
        category=category,
        finding_type=finding_type,
        severity=severity,
        title=title,
        description=description,
        evidence=evidence,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def list_by_scan(db: Session, scan_id: uuid.UUID) -> list[Finding]:
    stmt = (
        select(Finding)
        .where(Finding.scan_id == scan_id)
        .order_by(Finding.category, Finding.created_at)
    )
    return list(db.execute(stmt).scalars().all())
