import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.target import normalize_target_url


class TargetCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    label: str = Field(min_length=1, max_length=255)

    @field_validator("url")
    @classmethod
    def validate_and_normalize_url(cls, value: str) -> str:
        """
        Normalize/validate at the API boundary so a malformed URL or a
        disallowed scheme (ftp://, file://, javascript:, etc.) is
        rejected with a clear 422 before it ever reaches the service or
        database layer.

        This duplicates the Target model's own `@validates("url")`
        (app/models/target.py) on purpose -- see that file's docstring
        for why that's defense in depth rather than redundancy.
        """
        try:
            return normalize_target_url(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class TargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    url: str
    label: str
    is_active: bool
    created_at: datetime
