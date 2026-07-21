"""
Importing this package (rather than an individual module) guarantees
every model is registered on the shared declarative Base before any
relationship string-reference (e.g. Mapped["User"]) needs to resolve,
and before Alembic's autogenerate inspects Base.metadata. Individual
modules can still be imported directly (e.g. `from app.models.user
import User`) -- this just ensures the *package* import alone is
always sufficient.
"""

from app.models.finding import Finding, FindingCategory, FindingSeverity, FindingType
from app.models.organization import Organization
from app.models.scan import Scan, ScanStatus
from app.models.target import Target
from app.models.user import User, UserRole

__all__ = [
    "Finding",
    "FindingCategory",
    "FindingSeverity",
    "FindingType",
    "Organization",
    "Scan",
    "ScanStatus",
    "Target",
    "User",
    "UserRole",
]
