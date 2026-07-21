import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:  # pragma: no cover - import cycle avoidance, type-checking only
    from app.models.scan import Scan


class FindingCategory(str, enum.Enum):
    """
    Every category from the project's scanning-engine design, defined
    up front (like ScanStatus) even though this milestone's checks
    engine only ever produces HTTPS and HEADERS findings -- adding a
    cookies/trackers/policy check later is then just a new BaseCheck
    subclass, not another migration to widen this enum.
    """

    HTTPS = "https"
    HEADERS = "headers"
    COOKIES = "cookies"
    TRACKERS = "trackers"
    PRIVACY_POLICY = "privacy_policy"
    TERMS_OF_SERVICE = "tos"
    CONSENT_BANNER = "consent_banner"


class FindingType(str, enum.Enum):
    """
    Deliberately non-legal. No value in this enum reads as a legal
    conclusion -- there is no "violation" or "non_compliant" option a
    check could reach for. This is the schema-level enforcement of
    PrivacyLens's core design constraint: it reports technical
    observations, never compliance determinations.
    """

    POTENTIAL_ISSUE = "potential_issue"
    OBSERVATION = "observation"
    DETECTED_CONFIGURATION = "detected_configuration"
    RECOMMENDATION = "recommendation"


class FindingSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Finding(Base):
    """One observation produced by one check during one scan."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    scan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )

    category: Mapped[FindingCategory] = mapped_column(
        Enum(FindingCategory, name="finding_category", native_enum=True), nullable=False, index=True
    )
    finding_type: Mapped[FindingType] = mapped_column(
        Enum(FindingType, name="finding_type", native_enum=True), nullable=False
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="finding_severity", native_enum=True), nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Findings are heterogeneous by category -- a header finding's
    # evidence (a header name/value) looks nothing like a cookie
    # finding's (name/domain/flags). JSON (using the Postgres JSONB
    # variant in production, plain JSON in SQLite for tests) avoids
    # either a wide, mostly-null column set or a full EAV schema, at
    # the cost of the evidence shape only being documented by
    # convention (each check's module) rather than enforced by the DB.
    evidence: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scan: Mapped["Scan"] = relationship(back_populates="findings")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Finding id={self.id} category={self.category} type={self.finding_type}>"
