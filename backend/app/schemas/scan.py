import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.scan import ScanStatus


class ScanCreateResponse(BaseModel):
    """
    The response to "create a scan" -- deliberately narrower than
    ScanRead. It matches the 202 Accepted contract: acknowledge that a
    scan was queued and hand back an id to poll, nothing more. There is
    no ScanCreate *request* schema because the client supplies no scan
    fields at all (see routes_scans.py) -- everything about a new scan
    (status=queued, timestamps) is decided server-side.
    """

    scan_id: uuid.UUID
    status: ScanStatus


class ScanRead(BaseModel):
    """Full scan resource, returned by GET /scans/{scan_id}."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_id: uuid.UUID
    status: ScanStatus
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    error_message: str | None
