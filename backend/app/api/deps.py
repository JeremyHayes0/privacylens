import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.database import get_database_session
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.models.user import User, UserRole

# `tokenUrl` only tells Swagger UI's "Authorize" button which endpoint to
# hit when a developer logs in through the docs; FastAPI does not use it
# to perform validation itself. auto_error=False lets us return a
# consistent 401 body (rather than FastAPI's default) when no token is
# present at all.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_database_session),
) -> User:
    """
    Resolve the authenticated user from the request's bearer token.

    SECURITY: the token's `sub` claim is used only to *look up* the
    user — the user's current role and active status are re-read from
    the database on every single request rather than trusted from the
    (possibly stale) JWT payload. This matters concretely: if an admin
    demotes or deactivates a user, that change takes effect on the
    user's very next request, rather than only once their existing
    token happens to expire.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_error

    try:
        payload = decode_access_token(token)
    except PyJWTError:
        raise credentials_error

    raw_user_id = payload.get("sub")
    if raw_user_id is None:
        raise credentials_error

    try:
        user_id = uuid.UUID(raw_user_id)
    except ValueError:
        raise credentials_error

    user = user_crud.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_error

    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.get("/admin-only")
        def admin_route(user: User = Depends(require_role(UserRole.ADMIN))):
            ...

    Multiple roles may be allowed:
        Depends(require_role(UserRole.ADMIN, UserRole.ANALYST))

    RBAC is enforced here, server-side, as a dependency on the route —
    never inferred client-side and never skipped for convenience. Every
    route that needs a role restriction declares it explicitly and
    visibly in its function signature, rather than checking `if
    user.role == ...` ad hoc inside a handler body.
    """

    def _require_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return _require_role
