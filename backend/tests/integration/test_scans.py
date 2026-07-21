def _register_and_login(client, email: str, password: str = "supersecret123") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_target(client, headers, url: str = "https://scan-me.com", label: str = "Scan target") -> str:
    response = client.post("/api/v1/targets", json={"url": url, "label": label}, headers=headers)
    return response.json()["id"]


def test_create_scan_returns_202_with_queued_status(client):
    headers = _register_and_login(client, "scan-owner@example.com")
    target_id = _create_target(client, headers)

    response = client.post(f"/api/v1/targets/{target_id}/scans", headers=headers)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert "scan_id" in body


def test_get_scan_status(client):
    headers = _register_and_login(client, "scan-status@example.com")
    target_id = _create_target(client, headers)
    create_response = client.post(f"/api/v1/targets/{target_id}/scans", headers=headers)
    scan_id = create_response.json()["scan_id"]

    response = client.get(f"/api/v1/scans/{scan_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == scan_id
    assert body["target_id"] == target_id
    assert body["status"] == "queued"
    assert body["started_at"] is None
    assert body["completed_at"] is None
    assert body["error_message"] is None


def test_unauthenticated_user_cannot_create_scan(client):
    headers = _register_and_login(client, "scan-noauth@example.com")
    target_id = _create_target(client, headers)

    response = client.post(f"/api/v1/targets/{target_id}/scans")

    assert response.status_code == 401


def test_cannot_create_scan_for_another_organizations_target(client):
    owner_headers = _register_and_login(client, "scan-org-a@example.com")
    target_id = _create_target(client, owner_headers, url="https://org-a.com")

    other_headers = _register_and_login(client, "scan-org-b@example.com")
    response = client.post(f"/api/v1/targets/{target_id}/scans", headers=other_headers)

    assert response.status_code == 404


def test_cannot_view_another_organizations_scan(client):
    owner_headers = _register_and_login(client, "scan-view-a@example.com")
    target_id = _create_target(client, owner_headers, url="https://view-a.com")
    scan_id = client.post(
        f"/api/v1/targets/{target_id}/scans", headers=owner_headers
    ).json()["scan_id"]

    other_headers = _register_and_login(client, "scan-view-b@example.com")
    response = client.get(f"/api/v1/scans/{scan_id}", headers=other_headers)

    assert response.status_code == 404


def test_scan_for_nonexistent_target_returns_404(client):
    headers = _register_and_login(client, "scan-missing-target@example.com")
    fake_target_id = "00000000-0000-0000-0000-000000000000"

    response = client.post(f"/api/v1/targets/{fake_target_id}/scans", headers=headers)

    assert response.status_code == 404


def test_list_target_scans_returns_most_recent_first(client):
    headers = _register_and_login(client, "scan-history@example.com")
    target_id = _create_target(client, headers)

    first_scan_id = client.post(
        f"/api/v1/targets/{target_id}/scans", headers=headers
    ).json()["scan_id"]
    second_scan_id = client.post(
        f"/api/v1/targets/{target_id}/scans", headers=headers
    ).json()["scan_id"]

    response = client.get(f"/api/v1/targets/{target_id}/scans", headers=headers)

    assert response.status_code == 200
    scan_ids = [scan["id"] for scan in response.json()]
    assert scan_ids == [second_scan_id, first_scan_id]


def test_cannot_list_scans_for_another_organizations_target(client):
    owner_headers = _register_and_login(client, "scan-history-a@example.com")
    target_id = _create_target(client, owner_headers, url="https://history-a.com")

    other_headers = _register_and_login(client, "scan-history-b@example.com")
    response = client.get(f"/api/v1/targets/{target_id}/scans", headers=other_headers)

    assert response.status_code == 404
