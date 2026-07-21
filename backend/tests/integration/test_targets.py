def _register_and_login(client, email: str, password: str = "supersecret123") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_authenticated_user_can_create_target(client):
    headers = _register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/v1/targets",
        json={"url": "https://example.com", "label": "Example Site"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["url"] == "https://example.com"
    assert body["label"] == "Example Site"
    assert body["is_active"] is True


def test_unauthenticated_user_cannot_create_target(client):
    response = client.post(
        "/api/v1/targets",
        json={"url": "https://example.com", "label": "Example Site"},
    )
    assert response.status_code == 401


def test_target_url_must_use_http_or_https_scheme(client):
    headers = _register_and_login(client, "scheme@example.com")

    response = client.post(
        "/api/v1/targets",
        json={"url": "ftp://example.com", "label": "Bad scheme"},
        headers=headers,
    )
    assert response.status_code == 422


def test_target_url_is_normalized_before_storage(client):
    headers = _register_and_login(client, "normalize@example.com")

    response = client.post(
        "/api/v1/targets",
        json={"url": "HTTPS://Example.com/", "label": "Normalize me"},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["url"] == "https://example.com"


def test_user_cannot_access_another_organizations_target(client):
    owner_headers = _register_and_login(client, "org-a-owner@example.com")
    create_response = client.post(
        "/api/v1/targets",
        json={"url": "https://org-a-site.com", "label": "Org A site"},
        headers=owner_headers,
    )
    target_id = create_response.json()["id"]

    # A second registration creates a second, independent organization
    # (there's no invite flow yet -- see auth_service.register_user).
    other_org_headers = _register_and_login(client, "org-b-owner@example.com")
    response = client.get(f"/api/v1/targets/{target_id}", headers=other_org_headers)

    assert response.status_code == 404


def test_list_targets_only_returns_own_organizations_targets(client):
    owner_headers = _register_and_login(client, "list-owner@example.com")
    client.post(
        "/api/v1/targets",
        json={"url": "https://mine.com", "label": "Mine"},
        headers=owner_headers,
    )

    other_headers = _register_and_login(client, "list-other@example.com")
    client.post(
        "/api/v1/targets",
        json={"url": "https://theirs.com", "label": "Theirs"},
        headers=other_headers,
    )

    response = client.get("/api/v1/targets", headers=owner_headers)

    urls = [t["url"] for t in response.json()]
    assert urls == ["https://mine.com"]


def test_deactivate_target_soft_deletes(client):
    headers = _register_and_login(client, "deactivate@example.com")
    create_response = client.post(
        "/api/v1/targets",
        json={"url": "https://deactivate-me.com", "label": "Deactivate"},
        headers=headers,
    )
    target_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/targets/{target_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Soft delete -- the target still exists and is still readable, just inactive.
    get_response = client.get(f"/api/v1/targets/{target_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False
