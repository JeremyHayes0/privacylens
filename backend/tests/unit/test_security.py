import time

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_return_plaintext():
    hashed = hash_password("mypassword123")
    assert hashed != "mypassword123"
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")  # bcrypt format marker


def test_verify_password_accepts_correct_password():
    hashed = hash_password("mypassword123")
    assert verify_password("mypassword123", hashed) is True


def test_verify_password_rejects_incorrect_password():
    hashed = hash_password("mypassword123")
    assert verify_password("wrong-password", hashed) is False


def test_hash_password_uses_a_random_salt_per_call():
    """Two hashes of the same password must differ (proves salting is happening)."""
    first = hash_password("mypassword123")
    second = hash_password("mypassword123")
    assert first != second
    # Both must still independently verify correctly.
    assert verify_password("mypassword123", first)
    assert verify_password("mypassword123", second)


def test_create_and_decode_access_token_round_trip():
    token = create_access_token(subject="user-123", role="admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_decode_access_token_rejects_tampered_signature():
    token = create_access_token(subject="user-123", role="admin")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered)


def test_decode_access_token_rejects_garbage_input():
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("not.a.jwt")
