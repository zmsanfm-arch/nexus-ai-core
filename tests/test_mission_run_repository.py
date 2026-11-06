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


def test_finish_persists_terminal_audit_in_same_transaction(tmp_path):
    store = make_store(tmp_path)
    try:
        repo = MissionRunRepository(store)
        run = repo.enqueue("demo_mission", "principal-a", "audit-atomic", mission_data())
        repo.claim_next("audit-worker", lease_seconds=30)
        result = repo.finish(
            run["run_id"], "audit-worker", "completed",
            audit_event={"event": "mission_run_finished", "run_id": run["run_id"], "status": "completed"},
        )
        assert result == "completed"
        events = store.list_audit(limit=20)
        assert any(
            event.get("event") == "mission_run_finished"
            and event.get("run_id") == run["run_id"]
            for event in events
        )
        snapshot = repo.get(run["run_id"], "principal-a")
        assert snapshot["status"] == "completed"
    finally:
        store.close()


def test_finish_rolls_back_terminal_state_if_audit_cannot_be_serialized(tmp_path):
    store = make_store(tmp_path)
    try:
        repo = MissionRunRepository(store)
        run = repo.enqueue("demo_mission", "principal-a", "audit-rollback", mission_data())
        repo.claim_next("audit-worker", lease_seconds=30)
        try:
            repo.finish(
                run["run_id"], "audit-worker", "completed",
                audit_event={"event": "mission_run_finished", "invalid": object()},
            )
        except Exception:
            pass
        else:
            raise AssertionError("non-JSON audit data must fail the transaction")
        snapshot = repo.get(run["run_id"], "principal-a")
        assert snapshot["status"] == "running"
        queue = store.sessions()
        try:
            from app.services.mission_run_repository import MissionQueueRecord
            record = queue.get(MissionQueueRecord, run["run_id"])
            assert record.status == "leased"
            assert record.lease_owner == "audit-worker"
        finally:
            queue.close()
    finally:
        store.close()


def test_finish_handles_orphaned_queue_record_and_audits_dead_letter(tmp_path):
    store = make_store(tmp_path)
    try:
        repo = MissionRunRepository(store)
        run = repo.enqueue("demo_mission", "principal-a", "orphan-queue", mission_data())
        repo.claim_next("orphan-worker", lease_seconds=30)
        with store.sessions.begin() as session:
            record = session.get(MissionRunRecord, run["run_id"])
            session.delete(record)
        result = repo.finish(
            run["run_id"], "orphan-worker", "failed",
            error="mission_run_record_missing", max_attempts=1,
            audit_event={"event": "mission_run_finished", "run_id": run["run_id"]},
        )
        assert result == "failed"
        events = store.list_audit(limit=20)
        assert any(
            event.get("event") == "mission_run_finished"
            and event.get("run_id") == run["run_id"]
            and event.get("status") == "failed"
            for event in events
        )
        with store.sessions() as session:
            queue = session.get(MissionQueueRecord, run["run_id"])
            assert queue.status == "dead"
            assert queue.lease_owner is None
    finally:
        store.close()
