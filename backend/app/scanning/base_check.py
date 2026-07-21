from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.finding import FindingCategory, FindingSeverity, FindingType
from app.scanning.context import ScanContext


@dataclass
class FindingDraft:
    """
    A check's raw output -- not yet a persisted `Finding` row. A draft
    deliberately has no `scan_id`: a check has no reason to know which
    scan it's running as part of, and no reason to touch the database
    at all. The orchestrator (app/services/scan_orchestrator.py) is
    the only thing that turns a draft into a real `Finding`, via
    app/crud/finding.py, once a check has finished running.
    """

    category: FindingCategory
    finding_type: FindingType
    severity: FindingSeverity
    title: str
    description: str
    evidence: dict = field(default_factory=dict)


class BaseCheck(ABC):
    """
    A single, independent unit of analysis over an already-fetched
    ScanContext.

    Checks never fetch anything themselves. The orchestrator fetches a
    target exactly once (see app/scanning/fetcher.py) and hands every
    registered check the same ScanContext. That separation is why:

    - Adding a new check category is just writing a pure function over
      data that's already been collected -- never new network code.
    - Each check is unit-testable with a hand-built ScanContext
      fixture (see tests/unit/test_checks.py) and needs no network
      access, no database, and no running app at all.
    - A slow, buggy, or flaky check can't cause the target to be
      re-fetched, and can't affect any other check's view of the page.
    """

    category: FindingCategory

    @abstractmethod
    def run(self, context: ScanContext) -> list[FindingDraft]:
        """Return zero or more findings. Must not raise for expected/observable conditions --
        e.g. a missing header is a finding to report, not an exception to throw."""
        raise NotImplementedError
