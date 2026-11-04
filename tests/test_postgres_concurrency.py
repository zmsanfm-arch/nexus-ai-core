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

        with ThreadPoolExecutor(max_workers=8) as pool:
            batches = list(pool.map(drain, range(8)))

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
