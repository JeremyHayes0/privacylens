import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:  # pragma: no cover - import cycle avoidance, type-checking only
    from app.models.finding import Finding
    from app.models.target import Target


class ScanStatus(str, enum.Enum):
    """
    The full lifecycle of a scan. This milestone only ever creates a
    scan in QUEUED and never transitions it further -- RUNNING,
    COMPLETED, and FAILED are here so the schema is ready for the
    worker process (a later milestone) to write to, without requiring
    another migration just to add a status value.
    """

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Scan(Base):
    """
    One request to scan a target, and its lifecycle. The scan itself
    holds only status/timing -- the actual observations it produces
    live in `findings` (app/models/finding.py), written by the checks
    engine (app/scanning/) via the orchestrator
    (app/services/scan_orchestrator.py) as the worker process runs it.
    """

    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("targets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Nullable + SET NULL for the same reason as Target.created_by:
    # deleting a user shouldn't destroy the historical record that a
    # scan happened, just the attribution of who triggered it. Also
    # nullable to leave room for scheduled/automatic scans later, which
    # have no triggering user at all.
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, name="scan_status", native_enum=True),
        default=ScanStatus.QUEUED,
        server_default=ScanStatus.QUEUED.value,
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    target: Mapped["Target"] = relationship(back_populates="scans")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="scan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Scan id={self.id} status={self.status}>"
