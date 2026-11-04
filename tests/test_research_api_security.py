from fastapi.testclient import TestClient

from app.main import app


def test_research_reads_require_api_authentication(monkeypatch):
    monkeypatch.setenv("NEXUS_API_TOKEN", "research-api-token")
    monkeypatch.setenv("NEXUS_ADMIN_TOKEN", "research-admin-token")
    client = TestClient(app)

    unauthenticated = client.get("/market-data/datasets/missing")
    assert unauthenticated.status_code == 401

    authenticated = client.get(
        "/market-data/datasets/missing",
        headers={"Authorization": "Bearer research-api-token"},
    )
    assert authenticated.status_code == 404


def test_research_writes_require_admin_authentication(monkeypatch):
    monkeypatch.setenv("NEXUS_API_TOKEN", "research-api-token")
    monkeypatch.setenv("NEXUS_ADMIN_TOKEN", "research-admin-token")
    monkeypatch.setenv("NEXUS_ADMIN_ID", "verified-admin")
    client = TestClient(app)
    headers = {"Authorization": "Bearer research-api-token"}

    strategy = client.post(
        "/strategies/gold-ict/versions",
        headers=headers,
        json={"data": {"strategy_id": "gold-ict", "version": "1.0.0"}},
    )
    experiment = client.post(
        "/research/experiments",
        headers=headers,
        json={"data": {"experiment_id": "exp-001"}},
    )
    market_data = client.post(
        "/market-data/datasets",
        headers=headers,
        data={"instrument": "XAUUSD", "timeframe": "M5"},
        files={"file": ("prices.csv", b"timestamp,open,high,low,close\n", "text/csv")},
    )

    assert strategy.status_code == 403
    assert experiment.status_code == 403
    assert market_data.status_code == 403


def test_admin_can_reach_schema_validation_but_invalid_strategy_is_rejected(monkeypatch):
    monkeypatch.setenv("NEXUS_ADMIN_TOKEN", "research-admin-token")
    monkeypatch.setenv("NEXUS_ADMIN_ID", "verified-admin")
    client = TestClient(app)
    response = client.post(
        "/strategies/gold-ict/versions",
        headers={"Authorization": "Bearer research-admin-token"},
        json={"data": {"strategy_id": "gold-ict", "version": "1.0.0"}},
    )
    assert response.status_code == 422
