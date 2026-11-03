import pytest
from fastapi.testclient import TestClient

from app.main import app, governance


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("NEXUS_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("NEXUS_ADMIN_ID", "verified-admin")
    monkeypatch.setenv("NEXUS_API_TOKEN", "test-api-token")
    monkeypatch.setenv("NEXUS_API_ID", "verified-operator")
    return TestClient(app)


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/agents", {}),
        ("get", "/tasks/unknown", {}),
        ("post", "/tasks", {"json": {"objective": "analyze market structure"}}),
        ("post", "/approvals/unknown/decision", {"json": {"approved": True}}),
    ],
)
def test_all_non_public_routes_reject_missing_auth(client, method, path, kwargs):
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401


def test_health_is_public_and_minimal(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "nexus-ai-core"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"


def test_operator_can_read_agent_registry(client):
    response = client.get(
        "/agents", headers={"Authorization": "Bearer test-api-token"}
    )
    assert response.status_code == 200


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/agents", headers={"Authorization": "Bearer wrong-token"}
    )
    assert response.status_code == 403


def test_approval_requires_admin_role(client):
    response = client.post(
        "/approvals/missing/decision",
        headers={"Authorization": "Bearer test-api-token"},
        json={"approved": True},
    )
    assert response.status_code == 403


def test_approval_uses_server_identity_not_client_input(client):
    approval = governance.request_approval(
        "asset_transfer", {"amount": 10, "currency": "USD"}, "system"
    )
    response = client.post(
        f"/approvals/{approval['id']}/decision",
        headers={"Authorization": "Bearer test-admin-token"},
        json={"approved": True},
    )
    assert response.status_code == 200
    assert response.json()["reviewer"] == "verified-admin"


def test_client_cannot_supply_reviewer(client):
    response = client.post(
        "/approvals/missing/decision",
        headers={"Authorization": "Bearer test-admin-token"},
        json={"approved": True, "reviewer": "attacker"},
    )
    assert response.status_code == 422


def test_authentication_fails_closed_when_unconfigured(monkeypatch):
    monkeypatch.delenv("NEXUS_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("NEXUS_API_TOKEN", raising=False)
    monkeypatch.delenv("NEXUS_ADMIN_ID", raising=False)
    response = TestClient(app).get("/agents")
    assert response.status_code == 503


def test_duplicate_admin_and_operator_tokens_fail_closed(monkeypatch):
    monkeypatch.setenv("NEXUS_ADMIN_TOKEN", "same-token")
    monkeypatch.setenv("NEXUS_ADMIN_ID", "verified-admin")
    monkeypatch.setenv("NEXUS_API_TOKEN", "same-token")
    monkeypatch.setenv("NEXUS_API_ID", "verified-operator")
    response = TestClient(app).get(
        "/agents", headers={"Authorization": "Bearer same-token"}
    )
    assert response.status_code == 503


def test_configured_admin_token_requires_identity(monkeypatch):
    monkeypatch.setenv("NEXUS_ADMIN_TOKEN", "admin-token")
    monkeypatch.delenv("NEXUS_ADMIN_ID", raising=False)
    monkeypatch.delenv("NEXUS_API_TOKEN", raising=False)
    response = TestClient(app).get(
        "/agents", headers={"Authorization": "Bearer admin-token"}
    )
    assert response.status_code == 503


def test_registry_does_not_advertise_placeholder_agents_as_active(client):
    response = client.get(
        "/agents", headers={"Authorization": "Bearer test-api-token"}
    )
    assert response.status_code == 200
    agents = {agent["id"]: agent for agent in response.json()["agents"]}
    assert agents["executor"]["status"] == "disabled"
    assert agents["executor"]["permissions"] == []
    assert agents["ict_mentor"]["status"] == "specification"
    assert all(
        agent["status"] in {"catalog_only", "disabled", "specification"}
        for agent in agents.values()
    )
