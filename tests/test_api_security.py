import pytest
from fastapi.testclient import TestClient

from app.main import app, governance


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("NEXUS_ADMIN_TOKEN", "test-secret-token")
    monkeypatch.setenv("NEXUS_ADMIN_ID", "verified-admin")
    return TestClient(app)


def test_approval_endpoint_rejects_missing_auth(client):
    response = client.post(
        "/approvals/missing/decision",
        json={"approved": True},
    )
    assert response.status_code == 401


def test_approval_endpoint_rejects_invalid_token(client):
    response = client.post(
        "/approvals/missing/decision",
        headers={"Authorization": "Bearer wrong-token"},
        json={"approved": True},
    )
    assert response.status_code == 403


def test_approval_endpoint_uses_server_identity_not_client_input(client):
    approval = governance.request_approval(
        "asset_transfer", {"amount": 10, "currency": "USD"}, "system"
    )
    response = client.post(
        f"/approvals/{approval['id']}/decision",
        headers={"Authorization": "Bearer test-secret-token"},
        json={"approved": True},
    )
    assert response.status_code == 200
    assert response.json()["reviewer"] == "verified-admin"


def test_approval_endpoint_rejects_client_supplied_reviewer(client):
    response = client.post(
        "/approvals/missing/decision",
        headers={"Authorization": "Bearer test-secret-token"},
        json={"approved": True, "reviewer": "attacker"},
    )
    assert response.status_code == 422


def test_approval_endpoint_fails_closed_when_not_configured(monkeypatch):
    monkeypatch.delenv("NEXUS_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("NEXUS_ADMIN_ID", raising=False)
    response = TestClient(app).post(
        "/approvals/missing/decision",
        headers={"Authorization": "Bearer anything"},
        json={"approved": True},
    )
    assert response.status_code == 503
