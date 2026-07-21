VALID_PASSWORD = "supersecret123"


def test_register_user_succeeds(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": VALID_PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "test@example.com"
    # Registration creates a brand-new organization for this user and
    # makes them its admin (there's no invite flow yet -- see
    # auth_service.register_user).
    assert body["role"] == "admin"
    assert "organization_id" in body
    assert body["is_active"] is True
    # The response schema must never leak the password hash.
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_duplicate_email_is_rejected(client):
    payload = {"email": "dupe@example.com", "password": VALID_PASSWORD}
    first = client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "shortpw@example.com", "password": "short"},
    )
    # Enforced by the Pydantic schema (min_length=8), not the service layer.
    assert response.status_code == 422


def test_login_with_correct_credentials_returns_jwt(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": VALID_PASSWORD},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": VALID_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 0


def test_login_with_wrong_password_is_rejected(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "password": VALID_PASSWORD},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "not-the-password"},
    )

    assert response.status_code == 401


def test_login_with_unknown_email_gives_same_error_as_wrong_password(client):
    """
    SECURITY: verifies the anti-enumeration property directly -- an
    unknown email and a wrong password for a known email must be
    indistinguishable to the caller.
    """
    client.post(
        "/api/v1/auth/register",
        json={"email": "known@example.com", "password": VALID_PASSWORD},
    )

    unknown_email_response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": VALID_PASSWORD},
    )
    wrong_password_response = client.post(
        "/api/v1/auth/login",
        json={"email": "known@example.com", "password": "not-the-password"},
    )

    assert unknown_email_response.status_code == wrong_password_response.status_code == 401
    assert unknown_email_response.json()["detail"] == wrong_password_response.json()["detail"]


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_rejects_garbage_token(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": VALID_PASSWORD},
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": VALID_PASSWORD},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
