import uuid
from unittest.mock import patch

from app.crud import finding as finding_crud
from app.scanning.context import ScanContext
from app.scanning.fetcher import FetchError
from app.services import scan_orchestrator


def _register_and_login(client, email: str, password: str = "supersecret123") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_target_and_scan(client, headers, url: str) -> tuple[str, uuid.UUID]:
    target_response = client.post(
        "/api/v1/targets", json={"url": url, "label": "Orchestrator target"}, headers=headers
    )
    target_id = target_response.json()["id"]
    scan_response = client.post(f"/api/v1/targets/{target_id}/scans", headers=headers)
    return target_id, uuid.UUID(scan_response.json()["scan_id"])


def _fake_context(**overrides) -> ScanContext:
    defaults: dict = dict(
        requested_url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        headers={"content-security-policy": "default-src 'self'"},
        used_https=True,
        tls_certificate_expires_at=None,
        redirected=False,
        cookies=[],
        links=[],
    )
    defaults.update(overrides)
    return ScanContext(**defaults)


def test_run_scan_completes_and_persists_findings(client, db_session):
    """
    fetch_target is mocked -- this test exercises the real ORM/CRUD
    path (findings actually written, scan status actually transitioned
    in SQLite) without making a real network request. The checks
    themselves are exercised for real (not mocked), which is what
    proves the whole pipeline -- context in, findings out, status
    updated -- actually fits together end to end.
    """
    headers = _register_and_login(client, "orchestrator@example.com")
    _target_id, scan_id = _create_target_and_scan(client, headers, "https://example.com")

    with patch("app.services.scan_orchestrator.fetch_target", return_value=_fake_context()):
        scan_orchestrator.run_scan(db_session, scan_id)

    findings = finding_crud.list_by_scan(db_session, scan_id)
    assert len(findings) > 0

    status_response = client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["completed_at"] is not None

    findings_response = client.get(f"/api/v1/scans/{scan_id}/findings", headers=headers)
    assert findings_response.status_code == 200
    assert len(findings_response.json()) == len(findings)


def test_run_scan_marks_failed_when_target_unreachable(client, db_session):
    headers = _register_and_login(client, "orchestrator-fail@example.com")
    _target_id, scan_id = _create_target_and_scan(client, headers, "https://unreachable.example")

    with patch(
        "app.services.scan_orchestrator.fetch_target",
        side_effect=FetchError("Could not reach https://unreachable.example: connection refused"),
    ):
        scan_orchestrator.run_scan(db_session, scan_id)

    status_response = client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    body = status_response.json()
    assert body["status"] == "failed"
    assert "connection refused" in body["error_message"]

    # A failed scan has no findings -- checks never ran because there
    # was never a ScanContext to run them against.
    findings_response = client.get(f"/api/v1/scans/{scan_id}/findings", headers=headers)
    assert findings_response.json() == []


def test_findings_endpoint_returns_empty_list_for_still_queued_scan(client):
    """A scan no worker has picked up yet has zero findings -- that's a valid 200, not a 404."""
    headers = _register_and_login(client, "orchestrator-queued@example.com")
    _target_id, scan_id = _create_target_and_scan(client, headers, "https://still-queued.com")

    response = client.get(f"/api/v1/scans/{scan_id}/findings", headers=headers)

    assert response.status_code == 200
    assert response.json() == []
