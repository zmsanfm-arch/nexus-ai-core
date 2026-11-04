import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import inspect, text

from app.storage import SQLAlchemyStore


EXPECTED_TABLES = {
    "alembic_version", "tasks", "approvals", "audit_events",
    "task_queue", "knowledge_sources", "knowledge_chunks",
}


def test_sqlite_schema_is_created_by_versioned_migration_and_is_idempotent(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    first = SQLAlchemyStore(url)
    inspector = inspect(first.engine)
    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))
    with first.engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial"
    first.save_task({"id": "persisted-task", "status": "queued"})
    first.close()

    second = SQLAlchemyStore(url)
    assert second.get_task("persisted-task") == {"id": "persisted-task", "status": "queued"}
    with second.engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar_one() == 1
    second.close()


def test_knowledge_tables_are_migrated_before_adapter_use(tmp_path):
    from app.services.knowledge_store import KnowledgeStoreAdapter

    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'knowledge.db'}")
    adapter = KnowledgeStoreAdapter(store)
    adapter.save_knowledge_source(
        {
            "id": "ict-source-1",
            "title": "ICT research note",
            "url": "https://example.org/ict",
            "retrieved_at": "2026-11-04T00:00:00+00:00",
        },
        [{"ordinal": 0, "text": "Liquidity rests above a prior high."}],
    )
    result = adapter.search_knowledge("liquidity prior high")
    assert result and result[0]["source_id"] == "ict-source-1"
    store.close()


@pytest.mark.skipif(not os.getenv("NEXUS_TEST_POSTGRES_URL"), reason="PostgreSQL CI service is not configured")
def test_postgres_migrations_and_concurrent_queue_claims():
    store = SQLAlchemyStore(os.environ["NEXUS_TEST_POSTGRES_URL"])
    try:
        with store.engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial"

        for task_id in ("pg-queue-1", "pg-queue-2"):
            store.enqueue_task({"id": task_id, "objective": "database concurrency test"})
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda worker: store.claim_next_task(worker), ("worker-a", "worker-b")))
        claimed_ids = [claim["task_id"] for claim in claims if claim]
        assert len(claimed_ids) == 2
        assert len(set(claimed_ids)) == 2
    finally:
        store.close()
