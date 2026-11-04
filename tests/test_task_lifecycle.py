import time
from threading import Event, Thread

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
    assert saved["result"] == {"summary": "done", "audit_verdict": "pass"}
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


def test_worker_fails_closed_when_handler_omits_auditor_verdict():
    store = InMemoryStore()
    task = TaskQueueService(store).enqueue("Run a task without an auditor verdict")
    worker = TaskWorker(
        store, "worker-no-verdict", lambda item: {"summary": "unreviewed"}, lease_seconds=10
    )

    assert worker.run_once() is True
    assert store.get_task(task["id"])["status"] == "blocked"
    assert store.queue[task["id"]]["status"] == "completed"


def test_queue_summary_reports_all_lifecycle_states():
    store = InMemoryStore()
    queue = TaskQueueService(store)
    first = queue.enqueue("Queue the first task")
    lease = store.claim_next_task("worker-summary", lease_seconds=30)
    assert lease["task_id"] == first["id"]
    store.complete_queued_task(first["id"], "worker-summary")
    queue.enqueue("Queue the second task")
    summary = store.queue_summary()
    assert summary == {"queued": 1, "leased": 0, "completed": 1, "dead": 0, "total": 2}


def test_sql_queue_summary_reports_durable_status_counts(tmp_path):
    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'queue-summary.db'}")
    queue = TaskQueueService(store)
    first = queue.enqueue("Queue the SQL task")
    lease = store.claim_next_task("worker-sql-summary", lease_seconds=30)
    assert lease["task_id"] == first["id"]
    assert store.queue_summary() == {
        "queued": 0, "leased": 1, "completed": 0, "dead": 0, "total": 1
    }
    store.close()



def test_worker_renews_lease_during_long_running_handler():
    store = InMemoryStore()
    task = TaskQueueService(store).enqueue("Run a task longer than its lease")
    started = Event()
    finish = Event()

    def slow_handler(_):
        started.set()
        assert finish.wait(timeout=4)
        return {"summary": "finished", "audit_verdict": "pass"}

    worker = TaskWorker(store, "worker-heartbeat", slow_handler, lease_seconds=1)
    runner = Thread(target=worker.run_once)
    runner.start()
    assert started.wait(timeout=2)
    time.sleep(1.3)

    # A second worker must not steal a task while the original worker renews it.
    assert store.claim_next_task("worker-contender", lease_seconds=2) is None
    finish.set()
    runner.join(timeout=3)
    assert not runner.is_alive()
    assert store.get_task(task["id"])["status"] == "completed"
    assert store.queue[task["id"]]["status"] == "completed"


def test_lease_renewal_requires_current_owner_and_unexpired_lease():
    store = InMemoryStore()
    task = TaskQueueService(store).enqueue("Run a lease ownership check")
    lease = store.claim_next_task("worker-owner", lease_seconds=30)
    assert lease["task_id"] == task["id"]
    assert store.renew_queued_task_lease(task["id"], "worker-attacker", 30) is False
    assert store.renew_queued_task_lease(task["id"], "worker-owner", 30) is True

    store.queue[task["id"]]["lease_expires_at"] = store.queue[task["id"]]["lease_expires_at"].replace(year=2000)
    assert store.renew_queued_task_lease(task["id"], "worker-owner", 30) is False


def test_sql_store_renews_only_owned_unexpired_lease(tmp_path):
    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'lease-renewal.db'}")
    task = {"id": "lease-renewal-task", "objective": "lease renewal", "status": "queued"}
    store.save_task(task)
    store.enqueue_task(task)
    lease = store.claim_next_task("sql-worker", lease_seconds=30)
    assert lease["task_id"] == task["id"]
    assert store.renew_queued_task_lease(task["id"], "wrong-worker", 30) is False
    assert store.renew_queued_task_lease(task["id"], "sql-worker", 30) is True
    store.close()
