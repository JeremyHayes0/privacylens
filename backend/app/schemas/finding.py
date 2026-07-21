import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.finding import FindingCategory, FindingSeverity, FindingType


class FindingRead(BaseModel):
    """
    Read-only -- there is no FindingCreate schema, because findings are
    never created via the API. They only ever come from a check
    running inside the orchestrator (app/services/scan_orchestrator.py).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scan_id: uuid.UUID
    category: FindingCategory
    finding_type: FindingType
    severity: FindingSeverity
    title: str
    description: str
    evidence: dict
    created_at: datetime
