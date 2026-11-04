from fastapi.testclient import TestClient

from app.main import app
from app.storage import InMemoryStore, SQLAlchemyStore


def test_ready_endpoint_reports_database_available(monkeypatch):
    monkeypatch.setattr("app.main.store.check_database", lambda: True)
    response = TestClient(app).get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}


def test_ready_endpoint_returns_sanitized_503_when_database_fails(monkeypatch):
    def fail_probe():
        raise RuntimeError("private database connection detail")

    monkeypatch.setattr("app.main.store.check_database", fail_probe)
    response = TestClient(app).get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable"},
    }
    assert "private database" not in response.text


def test_sql_store_database_probe_executes_query(tmp_path):
    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'readiness.db'}")
    try:
        assert store.check_database() is True
    finally:
        store.close()


def test_in_memory_store_database_probe():
    assert InMemoryStore().check_database() is True
