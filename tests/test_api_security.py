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



def test_agent_and_task_apis_require_api_bearer_token(monkeypatch):
    monkeypatch.delenv("NEXUS_API_TOKEN", raising=False)
    client = TestClient(app)

    assert client.get("/agents").status_code == 503
    assert client.post("/tasks", json={"objective": "Explain liquidity"}).status_code == 503
    assert client.get("/tasks/unknown").status_code == 503


def test_agent_api_rejects_invalid_api_token(monkeypatch):
    monkeypatch.setenv("NEXUS_API_TOKEN", "valid-api-token")
    response = TestClient(app).get(
        "/agents",
        headers={"Authorization": "Bearer invalid"},
    )
    assert response.status_code == 403


def test_agent_api_accepts_configured_api_token(monkeypatch):
    monkeypatch.setenv("NEXUS_API_TOKEN", "valid-api-token")
    response = TestClient(app).get(
        "/agents",
        headers={"Authorization": "Bearer valid-api-token"},
    )
    assert response.status_code == 200
    assert "agents" in response.json()


def test_audit_endpoint_requires_admin_auth(client):
    response = client.get("/audit")
    assert response.status_code == 401


def test_audit_endpoint_rejects_invalid_limit(client):
    response = client.get(
        "/audit?limit=501",
        headers={"Authorization": "Bearer test-secret-token"},
    )
    assert response.status_code == 422



def test_queued_task_endpoint_requires_api_auth(monkeypatch):
    monkeypatch.delenv("NEXUS_API_TOKEN", raising=False)
    response = TestClient(app).post(
        "/tasks/queued", json={"objective": "Queue a task for a worker"}
    )
    assert response.status_code == 503


def test_queued_task_is_owned_by_configured_api_principal(monkeypatch):
    monkeypatch.setenv("NEXUS_API_TOKEN", "queue-api-token")
    monkeypatch.setenv("NEXUS_API_CLIENT_ID", "service-a")
    client = TestClient(app)
    response = client.post(
        "/tasks/queued",
        headers={"Authorization": "Bearer queue-api-token"},
        json={"objective": "Queue a task for a worker"},
    )
    assert response.status_code == 200
    task_id = response.json()["id"]
    assert response.json()["status"] == "queued"

    own_read = client.get(
        f"/tasks/{task_id}",
        headers={"Authorization": "Bearer queue-api-token"},
    )
    assert own_read.status_code == 200

    monkeypatch.setenv("NEXUS_API_CLIENT_ID", "service-b")
    other_read = client.get(
        f"/tasks/{task_id}",
        headers={"Authorization": "Bearer queue-api-token"},
    )
    assert other_read.status_code == 404


def test_queue_status_requires_admin_auth(client):
    response = client.get("/admin/queue")
    assert response.status_code == 401


def test_queue_status_returns_aggregate_counts_only(client, monkeypatch):
    from app import main

    monkeypatch.setattr(
        main.store,
        "queue_summary",
        lambda: {"queued": 2, "leased": 1, "completed": 4, "dead": 1, "total": 8},
    )
    response = client.get(
        "/admin/queue",
        headers={"Authorization": "Bearer test-secret-token"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "queue": {"queued": 2, "leased": 1, "completed": 4, "dead": 1, "total": 8}
    }
