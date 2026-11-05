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


def test_worker_restart_resumes_after_durable_node_checkpoint(tmp_path):
    from datetime import datetime, timedelta, timezone
    from app.services.mission_run_repository import MissionQueueRecord

    import app.services.mission_run_repository  # noqa: F401
    database_url = f"sqlite:///{tmp_path / 'restart.db'}"
    first_store = SQLAlchemyStore(database_url)
    repository = MissionRunRepository(first_store)
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
    run = repository.enqueue("demo_mission", "principal-a", "restart-test", mission)
    repository.claim_next("worker-before-crash", lease_seconds=60)
    repository.checkpoint_node(
        run["run_id"], "worker-before-crash", "research", "completed",
        output=Handler().run(None).model_dump(mode="json"), increment_attempt=True,
    )
    with first_store.sessions.begin() as session:
        queue = session.get(MissionQueueRecord, run["run_id"])
        queue.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    first_store.close()

    # A fresh store/worker process resumes from the committed checkpoint.
    restarted_store = SQLAlchemyStore(database_url)
    try:
        restarted_repository = MissionRunRepository(restarted_store)
        worker = MissionRunWorker(
            restarted_repository, Registry(), {"demo_agent": Handler()},
            restarted_store, worker_id="worker-after-restart",
            auditor=Auditor(),
            permission_service=PermissionService(
                capability_permissions={"demo.read": "demo.permission"},
                allowed_permissions=frozenset({"demo.permission"}),
            ),
        )
        assert worker.run_once() is True
        snapshot = restarted_repository.get(run["run_id"], "principal-a")
        assert snapshot["status"] == "completed"
        states = {node["node_id"]: node for node in snapshot["nodes"]}
        assert states["research"]["attempts"] == 1
        assert states["analysis"]["attempts"] == 1
        assert states["research"]["status"] == "completed"
        assert states["analysis"]["status"] == "completed"
    finally:
        restarted_store.close()


def test_lease_heartbeat_renews_during_slow_handler():
    import threading
    import time
    from app.services.mission_run_worker import _LeaseHeartbeat

    class LeaseRepo:
        def __init__(self):
            self.calls = []
        def renew_lease(self, run_id, worker_id, lease_seconds):
            self.calls.append((run_id, worker_id, lease_seconds))
            return True

    repository = LeaseRepo()
    with _LeaseHeartbeat(repository, "run-1", "worker-1", 3) as heartbeat:
        time.sleep(1.15)
        assert not heartbeat.lost.is_set()
    assert repository.calls
    assert repository.calls[0] == ("run-1", "worker-1", 3)


def test_lease_heartbeat_stops_work_when_ownership_is_lost():
    import time
    from app.services.mission_run_worker import _LeaseHeartbeat

    class LeaseRepo:
        def renew_lease(self, *_args):
            return False

    with _LeaseHeartbeat(LeaseRepo(), "run-2", "worker-2", 3) as heartbeat:
        assert heartbeat.lost.wait(timeout=2)
    assert heartbeat.lost.is_set()
