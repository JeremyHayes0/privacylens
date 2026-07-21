from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password with bcrypt.

    SECURITY: bcrypt generates and embeds a random salt per password
    automatically, and its tunable work factor makes brute-force
    guessing computationally expensive even if the hash is ever exposed.
    Plaintext passwords are never stored, logged, or included in any
    API response — they exist only transiently, inside this function
    call, at registration/login time.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check a plaintext password against a stored bcrypt hash.

    bcrypt.checkpw performs the comparison internally in a way that
    avoids leaking timing information about *where* a mismatch
    occurred, which is the relevant property for resisting timing
    attacks here (as opposed to a naive `==` string comparison).
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Raised if hashed_password isn't a valid bcrypt hash at all
        # (e.g. corrupted data) — treat as "does not match" rather than
        # propagating an internal error to the caller.
        return False


def create_access_token(subject: str, role: str) -> str:
    """
    Issue a signed, short-lived JWT access token.

    SECURITY: the token is deliberately short-lived
    (ACCESS_TOKEN_EXPIRE_MINUTES, default 15 min). A JWT is stateless —
    the server doesn't check it against a database on every request —
    so it cannot be revoked before it expires. Keeping the lifetime
    short limits the damage window if a token is ever leaked. A
    refresh-token mechanism with server-side revocation (a stored,
    hashed refresh token the server *can* invalidate) is the natural
    next addition once this foundation is in place, rather than simply
    extending the access token's lifetime.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT's signature and expiry.

    Raises jwt.PyJWTError (or a subclass, e.g. ExpiredSignatureError,
    InvalidSignatureError) on any invalid, tampered, or expired token.
    Callers are expected to catch this and translate it into a 401 —
    this function itself has no knowledge of HTTP.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
