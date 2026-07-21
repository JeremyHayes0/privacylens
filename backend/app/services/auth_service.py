from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.crud import organization as organization_crud
from app.crud import user as user_crud
from app.models.user import User, UserRole
from app.schemas.auth import Token
from app.schemas.user import UserCreate


class AuthError(Exception):
    """
    Raised for any authentication/registration failure. The API layer
    (routes) is responsible for catching this and translating it into
    the appropriate HTTP status code — this module has no knowledge of
    FastAPI or HTTP at all, which keeps the business logic testable in
    isolation and reusable outside a web context (e.g. a future CLI or
    background job that needs to create users).
    """


def register_user(db: Session, user_in: UserCreate) -> User:
    """
    Business rule: emails must be unique. Lives here, not in the route
    or CRUD layer.

    Every user must belong to an organization (organization_id is
    NOT NULL on the User model), and there is no invite flow yet, so
    registration creates a brand-new organization for the new user and
    makes them its admin. This is a deliberate, minimal design choice
    for this milestone: a self-registered user owns their own
    single-user organization until a Phase 2 invite flow lets an
    existing admin add teammates to it.
    """
    if user_crud.get_by_email(db, user_in.email):
        raise AuthError("A user with this email already exists.")

    organization_name = user_in.organization_name or _default_organization_name(user_in.email)
    organization = organization_crud.create(db, name=organization_name)

    return user_crud.create(
        db,
        user_in,
        organization_id=organization.id,
        role=UserRole.ADMIN,
    )


def _default_organization_name(email: str) -> str:
    local_part = email.split("@", 1)[0]
    return f"{local_part}'s Organization"


def authenticate(db: Session, email: str, password: str) -> User:
    user = user_crud.get_by_email(db, email)

    # SECURITY: deliberately return the identical error message and
    # status whether the email doesn't exist or the password is simply
    # wrong. Distinguishing "no such user" from "wrong password" in the
    # response would let an attacker enumerate which emails have
    # registered accounts — a small but real information leak.
    if not user or not verify_password(password, user.hashed_password):
        raise AuthError("Incorrect email or password.")

    if not user.is_active:
        raise AuthError("This account is inactive.")

    return user


def login(db: Session, email: str, password: str) -> Token:
    user = authenticate(db, email, password)
    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    return Token(access_token=access_token)
