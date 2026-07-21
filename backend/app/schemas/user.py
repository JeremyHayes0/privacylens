import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    # A minimum length is enforced here at the API boundary; this is
    # deliberately not the place for a full password-strength policy
    # (that's a product decision, not a schema concern) but it does
    # reject trivially empty/short input before it ever reaches the
    # service or hashing layer.
    password: str = Field(min_length=8, max_length=128)

    # There is no invite flow yet (a Phase 2 feature per the project
    # roadmap), so every registration creates a brand-new organization.
    # This field lets the caller name it; if omitted, auth_service
    # derives a default from the email address. It is intentionally
    # optional rather than required -- most users signing up for the
    # first time don't have an organization name in mind yet, and
    # forcing the decision at the register form is unnecessary friction
    # for what is, for now, a single-user organization anyway.
    organization_name: str | None = Field(default=None, max_length=255)


class UserRead(UserBase):
    """
    Response schema for returning a user. Notably absent:
    `hashed_password`. Pydantic's response_model filtering means the
    hash can never accidentally leak into an API response, even if a
    future contributor passes the full ORM object straight through.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    role: UserRole
    is_active: bool
    created_at: datetime
