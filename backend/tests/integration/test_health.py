def test_app_starts_and_health_check_responds(client):
    """
    If FastAPI failed to wire up (bad import, misconfigured settings,
    broken dependency graph), this test fails at the `client` fixture
    itself -- before assertions even run. That makes it a reasonable
    stand-in for "the application starts successfully."
    """
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "PrivacyLens"


def test_openapi_docs_are_served(client):
    """Automatic OpenAPI docs should be reachable under the versioned prefix."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "PrivacyLens"
