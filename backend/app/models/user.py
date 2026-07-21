import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:  # pragma: no cover - import cycle avoidance, type-checking only
    from app.models.organization import Organization


class UserRole(str, enum.Enum):
    """
    Mirrors the RBAC roles from the project's design docs. Kept as a
    plain three-value enum for the MVP; org-scoped role assignment
    (a user belonging to multiple orgs with different roles) is a
    Phase 2 concern once the `organizations` table exists.
    """

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    # A UUID primary key (rather than an auto-incrementing integer) is a
    # deliberate, small security choice: it avoids leaking information
    # via sequential, guessable IDs (e.g. "/users/2" implying "/users/1"
    # exists) in any endpoint that ever echoes a user ID back.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Every user belongs to exactly one organization -- this is the
    # foundation of the app's multi-tenancy model (see
    # app/models/organization.py). Deliberately NOT NULL: there is no
    # concept of a user without an org, so the schema itself makes an
    # orphaned user impossible rather than relying on application code
    # to enforce it. See app/services/auth_service.py for how this gets
    # populated at registration time (a new org is created per
    # self-registered user).
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # SECURITY: this column must only ever contain a bcrypt hash, never
    # a plaintext password. The name makes that contract explicit so a
    # future contributor isn't tempted to assign a raw password to it.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True),
        default=UserRole.VIEWER,
        server_default=UserRole.VIEWER.value,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="users")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<User id={self.id} email={self.email} role={self.role}>"
