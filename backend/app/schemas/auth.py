from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Shape of the data we put inside the JWT. Used for internal typing only."""

    sub: str | None = None
    role: str | None = None
    exp: int | None = None
