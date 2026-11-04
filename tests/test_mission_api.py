from fastapi.testclient import TestClient

from app.main import app


class MissionRepoStub:
    def __init__(self):
        self.items = {}

    def create(self, mission_id, principal_id, data):
        if mission_id in self.items:
            from app.services.mission_repository import MissionAlreadyExists
            raise MissionAlreadyExists(mission_id)
        self.items[mission_id] = (principal_id, dict(data))
        return {**data, "created_at": "2026-11-05T00:00:00+00:00"}

    def get(self, mission_id, principal_id):
        item = self.items.get(mission_id)
        if item is None or item[0] != principal_id:
            return None
        return {**item[1], "created_at": "2026-11-05T00:00:00+00:00"}


class RegistryStub:
    def list_agents(self):
        return [{
            "id": "demo_agent",
            "status": "registered",
            "mode": "advisory",
            "capabilities": ["demo.read"],
            "permissions": ["payload.read"],
        }]


def mission_payload():
    return {
        "mission_id": "demo_mission",
        "name": "Demo mission",
        "objective": "Review supplied reference material.",
        "nodes": [{
            "node_id": "research",
            "agent_id": "demo_agent",
            "capability": "demo.read",
        }],
        "max_total_attempts": 1,
    }


def setup_api(monkeypatch, principal="client-a"):
    from app import main
    monkeypatch.setenv("NEXUS_API_TOKEN", "mission-api-token")
    monkeypatch.setenv("NEXUS_API_CLIENT_ID", principal)
    monkeypatch.setattr(main, "registry", RegistryStub())
    monkeypatch.setattr(main, "mission_repository", MissionRepoStub())
    monkeypatch.setattr(main.store, "append_audit", lambda event: None)
    return TestClient(app), {"Authorization": "Bearer mission-api-token"}


def test_mission_definition_api_requires_auth(monkeypatch):
    monkeypatch.delenv("NEXUS_API_TOKEN", raising=False)
    client = TestClient(app)
    assert client.post("/missions", json=mission_payload()).status_code == 503


def test_mission_definition_api_validates_and_persists_without_execution(monkeypatch):
    client, headers = setup_api(monkeypatch)
    response = client.post("/missions", json=mission_payload(), headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["mission"]["mission_id"] == "demo_mission"
    assert body["execution_status"] == "not_started"
    assert body["execution_available"] is False


def test_mission_definition_api_rejects_unknown_agent(monkeypatch):
    client, headers = setup_api(monkeypatch)
    payload = mission_payload()
    payload["nodes"][0]["agent_id"] = "missing_agent"

    response = client.post("/missions", json=payload, headers=headers)
    assert response.status_code == 422


def test_mission_reads_are_principal_scoped(monkeypatch):
    client, headers = setup_api(monkeypatch, "client-a")
    created = client.post("/missions", json=mission_payload(), headers=headers)
    assert created.status_code == 200

    from app import main
    main.mission_repository = main.mission_repository

    monkeypatch.setenv("NEXUS_API_CLIENT_ID", "client-b")
    response = client.get("/missions/demo_mission", headers=headers)
    assert response.status_code == 404
