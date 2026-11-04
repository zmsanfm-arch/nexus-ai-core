import pytest

from app.services.task_lifecycle import TaskQueueService, TaskWorker
from app.storage import InMemoryStore, SQLAlchemyStore


def test_worker_claims_and_completes_task_with_audit():
    store = InMemoryStore()
    task = TaskQueueService(store).enqueue(
        "Run a bounded research task", principal_id="user-17"
    )
    worker = TaskWorker(
        store, "worker-a", lambda item: {"summary": "done", "audit_verdict": "pass"}, lease_seconds=10
    )

    assert worker.run_once() is True
    saved = store.get_task(task["id"])
    assert saved["status"] == "completed"
    assert saved["result"] == {"summary": "done"}
    assert store.queue[task["id"]]["status"] == "completed"
    assert any(e["event"] == "task_worker_completed" for e in store.audit)
    assert worker.run_once() is False


def test_worker_retries_then_dead_letters_without_leaking_exception_text():
    store = InMemoryStore()
    task = TaskQueueService(store).enqueue("Run a retryable task")
    def fail(_):
        raise RuntimeError("secret provider response must not enter audit")
    worker = TaskWorker(
        store, "worker-b", fail, max_attempts=2, retry_delay_seconds=0
    )

    worker.run_once()
    assert store.queue[task["id"]]["status"] == "queued"
    worker.run_once()
    assert store.queue[task["id"]]["status"] == "dead"
    assert store.get_task(task["id"])["status"] == "failed"
    assert all("secret provider response" not in str(e) for e in store.audit)


def test_worker_cannot_complete_another_workers_lease():
    store = InMemoryStore()
    task = TaskQueueService(store).enqueue("Run a lease ownership test")
    lease = store.claim_next_task("worker-owner", lease_seconds=30)
    assert lease["task_id"] == task["id"]
    with pytest.raises(ValueError, match="not owned"):
        store.complete_queued_task(task["id"], "worker-attacker")


def test_sql_store_persists_queue_state_across_recreation(tmp_path):
    url = f"sqlite:///{tmp_path / 'queue.db'}"
    first = SQLAlchemyStore(url)
    task = {"id": "queue-task-1", "objective": "persist queue", "status": "queued"}
    first.save_task(task)
    first.enqueue_task(task)
    lease = first.claim_next_task("durable-worker", lease_seconds=30)
    assert lease["task_id"] == task["id"]
    first.close()

    second = SQLAlchemyStore(url)
    saved_lease = second.claim_next_task("recovery-worker", lease_seconds=30)
    assert saved_lease is None
    assert second.complete_queued_task(task["id"], "durable-worker") == "completed"
    second.close()


def test_worker_records_nonpass_auditor_verdict_as_blocked_task():
    store = InMemoryStore()
    task = TaskQueueService(store).enqueue("Run an audited task")
    worker = TaskWorker(
        store,
        "worker-auditor",
        lambda item: {"audit_verdict": "revise", "report": {"audit": {"verdict": "revise"}}},
        lease_seconds=10,
    )

    assert worker.run_once() is True
    saved = store.get_task(task["id"])
    assert saved["status"] == "blocked"
    assert saved["result"]["audit_verdict"] == "revise"
    assert store.queue[task["id"]]["status"] == "completed"
    event = [item for item in store.audit if item["event"] == "task_worker_completed"][-1]
    assert event["task_status"] == "blocked"
    assert event["audit_verdict"] == "revise"
