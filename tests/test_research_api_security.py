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


def test_new_strategy_cannot_be_created_in_demo_state(monkeypatch):
    monkeypatch.setenv("NEXUS_ADMIN_TOKEN", "research-admin-token")
    monkeypatch.setenv("NEXUS_ADMIN_ID", "verified-admin")
    client = TestClient(app)
    data = {
        "strategy_id": "gold-ict", "name": "Gold ICT", "version": "1.0.0",
        "status": "demo_active", "instrument": "XAUUSD",
        "market": {"asset_class": "metal", "quote_currency": "USD"},
        "timeframes": {"context": ["H4"], "setup": ["M15"], "trigger": ["M5"]},
        "hypothesis": {"statement": "A sufficiently detailed test hypothesis.", "ict_concepts": []},
        "rules": {
            "bias": {}, "setup": {}, "trigger": {}, "entry": {},
            "stop_loss": {}, "take_profit": {}, "invalidation": {}, "exit": {},
        },
        "risk_model": {
            "risk_per_trade": 0.01, "max_positions": 1,
            "sizing_method": "fixed_fractional",
        },
        "execution_model": {
            "order_type": "market", "entry_timing": "next bar",
            "partial_fills": False, "same_bar_policy": "reject_ambiguous",
        },
        "data_assumptions": {
            "price_basis": "bid", "bar_timestamp_convention": "bar_open",
            "required_fields": ["timestamp", "open", "high", "low", "close"],
            "cost_model": {"spread": {}, "commission": {}, "slippage": {}},
        },
        "provenance": {
            "created_by": "security-test", "created_at": "2026-11-04T00:00:00Z",
            "sources": [], "user_rules_used": [], "agent_inferences": [],
        },
    }
    response = client.post(
        "/strategies/gold-ict/versions",
        headers={"Authorization": "Bearer research-admin-token"},
        json={"data": data},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "New strategy versions must start in draft"
