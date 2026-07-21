import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:  # pragma: no cover - import cycle avoidance, type-checking only
    from app.models.target import Target
    from app.models.user import User


class Organization(Base):
    """
    The tenant boundary for the whole application. Every user belongs
    to exactly one organization, and every target (and, transitively,
    every scan and finding) belongs to exactly one organization. All
    organization-scoped data access checks (see
    app/services/target_service.py) ultimately compare against
    `organization_id`, so this table is the root of the multi-tenancy
    model even though it has no columns of its own beyond a name.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    targets: Mapped[list["Target"]] = relationship(back_populates="organization")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Organization id={self.id} name={self.name!r}>"
