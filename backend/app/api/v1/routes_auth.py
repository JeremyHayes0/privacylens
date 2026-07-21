from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_database_session
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserRead
from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_database_session),
) -> User:
    """
    Create a new user account.

    The route itself does nothing but: validate input (via UserCreate),
    delegate to the service layer, and translate the outcome into an
    HTTP response. It does not touch SQLAlchemy directly and does not
    contain the "is this email already taken" business rule — that
    lives in auth_service.register_user, which makes it independently
    unit-testable without spinning up FastAPI at all.
    """
    try:
        return auth_service.register_user(db, user_in)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login", response_model=Token)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_database_session),
) -> Token:
    """
    Validate credentials and return a short-lived JWT access token.

    Note the request body is a JSON `LoginRequest`, not FastAPI's
    built-in OAuth2 form dependency — that form-based flow is a good
    fit for a pure API-token exchange, but a plain JSON body is simpler
    for a React SPA's login form and keeps the request/response schema
    consistent with the rest of the API.
    """
    try:
        return auth_service.login(db, credentials.email, credentials.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Protected route: returns the authenticated caller's own user record.

    Its only job is to exist and require `get_current_user` — it's the
    simplest possible proof that the bearer-token auth dependency works
    end to end, and it's what the frontend calls on app load to
    validate a stored token / hydrate the logged-in user's session.
    """
    return current_user
