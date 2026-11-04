from app.storage import SQLAlchemyStore
from app.services.mission_run_repository import MissionRunRepository
from app.services.mission_run_worker import MissionRunWorker
from app.services.permissions import PermissionService
from app.services.specialist_contract import SpecialistResult
from app.services.mission_audit import MissionAuditResult


class Registry:
    def list_agents(self):
        return [{
            "id": "demo_agent", "status": "registered", "mode": "advisory",
            "capabilities": ["demo.read"], "permissions": ["demo.permission"],
        }]


class Handler:
    def run(self, request):
        return SpecialistResult(
            agent_id="demo_agent", mode="advisory",
            answer="Reviewed.", source_claims=[], user_rules_used=[],
            agent_inferences=[], proposed_actions=[],
            risk_decision="not_requested", execution_result=None,
            uncertainties=[],
        )


class Auditor:
    def audit(self, *, mission, outputs):
        assert "research" in outputs
        assert "analysis" in outputs
        return MissionAuditResult(verdict="pass", summary="All nodes reviewed.")


def test_worker_executes_and_checkpoints_dependency_order(tmp_path):
    import app.services.mission_run_repository  # noqa: F401
    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'worker.db'}")
    try:
        repository = MissionRunRepository(store)
        mission = {
            "mission_id": "demo_mission", "name": "Demo",
            "objective": "Analyze supplied data",
            "nodes": [
                {"node_id": "research", "agent_id": "demo_agent",
                 "capability": "demo.read", "dependencies": [], "max_attempts": 2},
                {"node_id": "analysis", "agent_id": "demo_agent",
                 "capability": "demo.read", "dependencies": ["research"], "max_attempts": 1},
            ],
            "max_total_attempts": 3,
            "approval_policy": "required_for_external_actions",
        }
        run = repository.enqueue("demo_mission", "principal-a", "worker-test", mission)
        worker = MissionRunWorker(
            repository, Registry(), {"demo_agent": Handler()}, store,
            worker_id="worker-test-1", auditor=Auditor(),
            permission_service=PermissionService(
                capability_permissions={"demo.read": "demo.permission"},
                allowed_permissions=frozenset({"demo.permission"}),
            ),
        )
        assert worker.run_once() is True
        assert worker.run_once() is False
        snapshot = repository.get(run["run_id"], "principal-a")
        assert snapshot["status"] == "completed"
        assert all(node["status"] == "completed" for node in snapshot["nodes"])
        assert all(node["attempts"] == 1 for node in snapshot["nodes"])
    finally:
        store.close()
