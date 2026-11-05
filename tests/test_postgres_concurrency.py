"""PostgreSQL-only concurrent queue-claim test; SQLite is not a substitute."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from app.storage import SQLAlchemyStore, TaskQueueRecord, TaskRecord


DATABASE_URL = os.getenv("NEXUS_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="NEXUS_TEST_POSTGRES_URL is not configured")


def test_concurrent_postgres_workers_claim_each_task_at_most_once():
    store = SQLAlchemyStore(DATABASE_URL)
    task_ids = [str(uuid4()) for _ in range(256)]
    worker_prefix = f"concurrency-{uuid4()}"
    try:
        for task_id in task_ids:
            task = {"id": task_id, "objective": "concurrency test", "status": "queued"}
            store.enqueue_task(task)

        def drain(worker_number: int):
            worker_id = f"{worker_prefix}-{worker_number}"
            claimed = []
            while True:
                lease = store.claim_next_task(worker_id, lease_seconds=60)
                if lease is None:
                    return claimed
                claimed.append(lease["task_id"])

        with ThreadPoolExecutor(max_workers=16) as pool:
            batches = list(pool.map(drain, range(16)))

        flattened = [task_id for batch in batches for task_id in batch]
        assert len(flattened) == len(set(flattened))
        assert set(flattened) == set(task_ids)
        with store.sessions() as session:
            leased_count = session.query(TaskQueueRecord).filter(
                TaskQueueRecord.task_id.in_(task_ids),
                TaskQueueRecord.status == "leased",
            ).count()
        assert leased_count == len(task_ids)
    finally:
        with store.sessions.begin() as session:
            session.query(TaskQueueRecord).filter(
                TaskQueueRecord.task_id.in_(task_ids)
            ).delete(synchronize_session=False)
            session.query(TaskRecord).filter(
                TaskRecord.id.in_(task_ids)
            ).delete(synchronize_session=False)
        store.close()


def test_postgres_concurrent_enqueue_and_claim_stress():
    """Exercise the PostgreSQL pool and queue with concurrent producers/consumers."""
    store = SQLAlchemyStore(DATABASE_URL)
    task_ids = [str(uuid4()) for _ in range(512)]
    worker_prefix = f"stress-{uuid4()}"
    batches = [task_ids[index:index + 16] for index in range(0, len(task_ids), 16)]
    try:
        def enqueue_batch(batch):
            for task_id in batch:
                store.enqueue_task({
                    "id": task_id,
                    "objective": "postgres concurrency stress",
                    "status": "queued",
                })

        with ThreadPoolExecutor(max_workers=32) as pool:
            list(pool.map(enqueue_batch, batches))

        def drain(worker_number: int):
            worker_id = f"{worker_prefix}-{worker_number}"
            claimed = []
            while True:
                lease = store.claim_next_task(worker_id, lease_seconds=60)
                if lease is None:
                    return claimed
                claimed.append(lease["task_id"])

        with ThreadPoolExecutor(max_workers=32) as pool:
            batches = list(pool.map(drain, range(32)))
        claimed_ids = [task_id for batch in batches for task_id in batch]
        assert len(claimed_ids) == len(set(claimed_ids)) == len(task_ids)
        assert set(claimed_ids) == set(task_ids)
        assert store.queue_summary()["leased"] >= len(task_ids)
        assert store.engine.pool.checkedout() == 0
    finally:
        with store.sessions.begin() as session:
            session.query(TaskQueueRecord).filter(
                TaskQueueRecord.task_id.in_(task_ids)
            ).delete(synchronize_session=False)
            session.query(TaskRecord).filter(
                TaskRecord.id.in_(task_ids)
            ).delete(synchronize_session=False)
        store.close()
