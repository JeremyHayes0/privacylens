import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:  # pragma: no cover - import cycle avoidance, type-checking only
    from app.models.organization import Organization
    from app.models.scan import Scan

# The scan worker (a later milestone) will eventually fetch whatever
# URL is stored here. Restricting the scheme allow-list at the data
# layer -- not just the API layer -- is a deliberate SSRF-adjacent
# guardrail: even a future code path that creates a Target without
# going through the API (a script, an admin console, a bulk import)
# still can't smuggle in a file://, ftp://, or javascript: "URL".
ALLOWED_URL_SCHEMES = {"http", "https"}


def normalize_target_url(raw_url: str) -> str:
    """
    Validate and normalize a target URL.

    - Only http:// and https:// are accepted.
    - Scheme and host are lowercased.
    - A bare trailing slash on the path is stripped.
    - Any URL fragment (the "#..." part) is dropped -- it's never sent
      to the server and has no bearing on what a scan would observe.

    This means "HTTPS://Example.com/" and "https://example.com" are
    stored as the identical string, so the same site can't accidentally
    end up monitored as two different `Target` rows.

    Raises ValueError (never a bare AssertionError or similar) on any
    input that doesn't parse into a URL with an allowed scheme and a
    non-empty host -- both app/schemas/target.py (API boundary) and
    this model's own `@validates` hook (see below) catch that
    ValueError and turn it into a client-facing error at their
    respective layers.
    """
    raw_url = raw_url.strip()
    parts = urlsplit(raw_url)

    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_URL_SCHEMES:
        raise ValueError(
            f"URL scheme must be one of {sorted(ALLOWED_URL_SCHEMES)}, "
            f"got: {parts.scheme or raw_url!r}"
        )

    if not parts.netloc:
        raise ValueError("URL must include a host, e.g. 'https://example.com'.")

    netloc = parts.netloc.lower()
    path = "" if parts.path in ("", "/") else parts.path.rstrip("/")

    return urlunsplit((scheme, netloc, path, parts.query, ""))


class Target(Base):
    """A website an organization has asked PrivacyLens to monitor."""

    __tablename__ = "targets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Nullable + ON DELETE SET NULL: deleting the user who added a
    # target should not cascade-delete the target itself (and its scan
    # history) -- the target still belongs to the organization. We just
    # lose the "who originally added this" attribution.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="targets")
    scans: Mapped[list["Scan"]] = relationship(
        back_populates="target", cascade="all, delete-orphan"
    )

    @validates("url")
    def _validate_and_normalize_url(self, key: str, value: str) -> str:
        """
        SECURITY / DATA INTEGRITY: re-applies normalize_target_url at
        the ORM layer, not just in the Pydantic schema at the API
        boundary (see app/schemas/target.py). This is deliberate
        defense in depth -- the schema-level check gives a user a fast,
        friendly 422; this check guarantees the invariant holds no
        matter what code constructs a Target (a future admin script, a
        data migration, a test fixture that forgets to go through the
        schema).
        """
        return normalize_target_url(value)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Target id={self.id} url={self.url!r}>"
