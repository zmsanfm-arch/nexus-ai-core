import pytest
from fastapi.testclient import TestClient

from app.main import app, governance, store


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


def test_research_routes_require_admin_for_writes(client):
    response = client.post(
        "/research/experiments",
        headers={"Authorization": "Bearer test-api-token"},
        json={"data": {"experiment_id": "exp-1"}},
    )
    assert response.status_code == 403


def test_experiment_contract_rejects_incomplete_payload(client):
    response = client.post(
        "/research/experiments",
        headers={"Authorization": "Bearer test-admin-token"},
        json={"data": {"experiment_id": "exp-incomplete"}},
    )
    assert response.status_code == 422
    assert "Invalid research contract" in response.json()["detail"]


def test_strategy_contract_rejects_path_payload_mismatch(client):
    response = client.post(
        "/strategies/gold-ict/versions",
        headers={"Authorization": "Bearer test-admin-token"},
        json={"data": {"strategy_id": "different-id", "version": "1.0.0"}},
    )
    assert response.status_code == 422
    assert "must match URL" in response.json()["detail"]


def test_knowledge_source_ingestion_and_provenance_search(client):
    payload = {
        "id": "ict-source-test",
        "title": "ICT public excerpt",
        "url": "https://www.youtube.com/@InnerCircleTrader",
        "source_type": "video_transcript",
        "usage_basis": "official_public_excerpt",
        "retrieved_at": "2026-11-04T10:00:00Z",
        "metadata": {"publisher": "ICT"},
        "chunks": [{"ordinal": 0, "text": "Fair value gap and liquidity concepts", "timestamp_start": "00:01:00", "timestamp_end": "00:02:00"}],
    }
    created = client.post(
        "/knowledge/sources",
        headers={"Authorization": "Bearer test-admin-token"},
        json=payload,
    )
    assert created.status_code == 200
    found = client.get(
        "/knowledge/search?q=fair%20value%20gap",
        headers={"Authorization": "Bearer test-api-token"},
    )
    assert found.status_code == 200
    result = found.json()["results"][0]
    assert result["source_id"] == "ict-source-test"
    assert result["segment_id"] == "ict-source-test:0"
    assert result["url"] == payload["url"]


def test_knowledge_ingestion_requires_admin(client):
    response = client.post(
        "/knowledge/sources",
        headers={"Authorization": "Bearer test-api-token"},
        json={"id": "abc", "title": "x", "url": "https://example.com", "usage_basis": "licensed", "retrieved_at": "2026-11-04T10:00:00Z", "chunks": [{"ordinal": 0, "text": "test"}]},
    )
    assert response.status_code == 403


def test_ict_mentor_invocation_is_central_and_advisory_only(client):
    response = client.post(
        "/agents/ict-mentor/invoke",
        headers={"Authorization": "Bearer test-api-token"},
        json={"task_type": "ict.education", "request": "Explain fair value gaps"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["agent_id"] == "ict_mentor"
    assert result["mode"] == "advisory"
    assert result["execution_result"] is None
    assert result["risk_decision"] == "blocked_insufficient_information"


def test_ict_mentor_invocation_rejects_unsupported_capabilities(client):
    response = client.post(
        "/agents/ict-mentor/invoke",
        headers={"Authorization": "Bearer test-api-token"},
        json={"task_type": "ict.autonomous_execution", "request": "Open a trade"},
    )
    assert response.status_code == 422


def test_security_middleware_sets_request_id_and_rejects_oversized_body(client):
    healthy = client.get("/health")
    assert healthy.status_code == 200
    assert healthy.headers.get("x-request-id")

    oversized = client.post(
        "/tasks",
        headers={
            "Authorization": "Bearer test-api-token",
            "Content-Length": "2000000",
        },
        json={"objective": "analyze market structure"},
    )
    assert oversized.status_code == 413


def test_strategy_lifecycle_api_blocks_missing_evidence_and_records_transition(client):
    strategy_id = "lifecycle-test-strategy"
    store.create_strategy_version(strategy_id, "1.0.0", {"strategy_id": strategy_id, "version": "1.0.0", "status": "draft"})
    headers = {"Authorization": "Bearer test-admin-token"}
    blocked = client.post(
        f"/strategies/{strategy_id}/versions/1.0.0/transitions",
        headers=headers,
        json={"target_state": "candidate", "evidence": {"complete_specification": True}},
    )
    assert blocked.status_code == 409
    assert "deterministic_rules" in blocked.json()["detail"]["missing_evidence"]

    evidence = {
        "complete_specification": True,
        "deterministic_rules": True,
        "provenance_complete": True,
        "assumptions_documented": True,
    }
    accepted = client.post(
        f"/strategies/{strategy_id}/versions/1.0.0/transitions",
        headers=headers,
        json={"target_state": "candidate", "evidence": evidence},
    )
    assert accepted.status_code == 200
    history = client.get(
        f"/strategies/{strategy_id}/versions/1.0.0/transitions",
        headers={"Authorization": "Bearer test-api-token"},
    )
    assert history.status_code == 200
    assert history.json()["current_state"] == "candidate"
