from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.storage import SQLAlchemyStore
from app.services.mission_run_repository import (
    MissionQueueRecord,
    MissionRunRepository,
)


def mission_data():
    return {
        "mission_id": "demo_mission",
        "name": "Demo",
        "objective": "Analyze supplied data",
        "nodes": [
            {"node_id": "research", "agent_id": "demo_agent",
             "capability": "demo.read", "dependencies": [], "max_attempts": 2},
            {"node_id": "analysis", "agent_id": "demo_agent",
             "capability": "demo.read", "dependencies": ["research"], "max_attempts": 1},
        ],
    }


def make_store(tmp_path):
    # Import model declarations before the Alembic migration and repository use.
    import app.services.mission_run_repository  # noqa: F401
    return SQLAlchemyStore(f"sqlite:///{tmp_path / 'mission-runs.db'}")


def test_enqueue_is_idempotent_and_creates_node_checkpoints(tmp_path):
    store = make_store(tmp_path)
    try:
        repo = MissionRunRepository(store)
        first = repo.enqueue("demo_mission", "principal-a", "request-001", mission_data())
        second = repo.enqueue("demo_mission", "principal-a", "request-001", mission_data())
        assert first["run_id"] == second["run_id"]
        assert [node["status"] for node in first["nodes"]] == ["pending", "pending"]
        assert repo.get(first["run_id"], "principal-b") is None
    finally:
        store.close()


def test_expired_lease_recovers_run_without_erasing_completed_checkpoint(tmp_path):
    store = make_store(tmp_path)
    try:
        repo = MissionRunRepository(store)
        run = repo.enqueue("demo_mission", "principal-a", "request-002", mission_data())
        first_claim = repo.claim_next("worker-a", lease_seconds=30)
        assert first_claim["run_id"] == run["run_id"]

        repo.checkpoint_node(
            run["run_id"], "worker-a", "research", "completed",
            output={"answer": "durable result"}, increment_attempt=True,
        )

        # Simulate process death: the durable lease expires without a clean release.
        with store.sessions.begin() as session:
            queue = session.get(MissionQueueRecord, run["run_id"])
            queue.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

        recovered = repo.claim_next("worker-b", lease_seconds=30)
        assert recovered["run_id"] == run["run_id"]
        snapshot = repo.get(run["run_id"], "principal-a")
        research = next(node for node in snapshot["nodes"] if node["node_id"] == "research")
        analysis = next(node for node in snapshot["nodes"] if node["node_id"] == "analysis")
        assert research["status"] == "completed"
        assert research["output"] == {"answer": "durable result"}
        assert research["attempts"] == 1
        assert analysis["status"] == "pending"
    finally:
        store.close()


def test_checkpoint_requires_current_worker_lease(tmp_path):
    store = make_store(tmp_path)
    try:
        repo = MissionRunRepository(store)
        run = repo.enqueue("demo_mission", "principal-a", "request-003", mission_data())
        repo.claim_next("worker-a", lease_seconds=30)
        try:
            repo.checkpoint_node(run["run_id"], "worker-b", "research", "completed",
                                 output={"answer": "not authorized"})
        except ValueError as exc:
            assert "lease" in str(exc)
        else:
            raise AssertionError("checkpoint writes must require the active lease")
    finally:
        store.close()
