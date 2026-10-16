from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_configuration_without_secrets(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["cors_allowlist_configured"] is True
    assert all(isinstance(value, bool) for value in body["checks"].values())


def test_version_returns_public_metadata(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200

    body = response.json()
    assert set(body) == {"application_version", "corpus_version", "build_commit"}


def test_security_headers_are_present(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
