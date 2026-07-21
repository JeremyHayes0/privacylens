import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


def get_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return db.execute(stmt).scalar_one_or_none()


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def create(
    db: Session,
    user_in: UserCreate,
    *,
    organization_id: uuid.UUID,
    role: UserRole = UserRole.VIEWER,
) -> User:
    """
    Persist a new user.

    This function only ever writes a bcrypt hash to the `hashed_password`
    column — the plaintext password from `user_in.password` is consumed
    once, by `hash_password`, and never assigned to a model attribute or
    interpolated into a query.

    `organization_id` and `role` are required keyword arguments rather
    than being derived from `user_in` -- which organization a new user
    lands in, and what role they get, are business decisions (see
    app/services/auth_service.py), not something the caller of a "dumb"
    CRUD function should be trusted to have encoded correctly in a
    request body.

    This function still contains no business rules of its own (no
    uniqueness check, no validation) -- those live in the service layer,
    which keeps this module a thin, easily-testable data-access layer.
    """
    db_user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        organization_id=organization_id,
        role=role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
