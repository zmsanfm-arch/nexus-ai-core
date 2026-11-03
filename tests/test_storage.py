from app.storage import SQLAlchemyStore


def test_tasks_and_approvals_survive_store_recreation(tmp_path):
    url = f"sqlite:///{tmp_path / 'nexus.db'}"
    first = SQLAlchemyStore(url)
    task = {"id": "task-1", "objective": "persist this", "status": "completed"}
    approval = {"id": "approval-1", "status": "pending", "parameters": {"amount": 10}}

    first.save_task(task)
    first.save_approval(approval)
    first.append_audit({"event": "created", "task_id": "task-1"})
    first.close()

    second = SQLAlchemyStore(url)
    assert second.get_task("task-1") == task
    assert second.get_approval("approval-1") == approval
    events = second.list_audit()
    assert len(events) == 1
    assert events[0]["event"] == "created"
    assert events[0]["task_id"] == "task-1"
    second.close()


def test_missing_records_return_none(tmp_path):
    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'empty.db'}")
    assert store.get_task("missing") is None
    assert store.get_approval("missing") is None
    store.close()


def test_strategy_versions_are_insert_only_and_immutable(tmp_path):
    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'strategy.db'}")
    payload = {"strategy_id": "gold-ict", "version": "1.0.0", "status": "draft"}
    key = store.create_strategy_version("gold-ict", "1.0.0", payload)
    assert key == "gold-ict:1.0.0"
    assert store.get_strategy_version("gold-ict", "1.0.0") == payload
    import pytest
    with pytest.raises(ValueError, match="immutable"):
        store.create_strategy_version("gold-ict", "1.0.0", {"status": "demo_active"})
    assert store.get_strategy_version("gold-ict", "1.0.0") == payload
    store.close()


def test_research_and_demo_records_are_environment_scoped(tmp_path):
    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'records.db'}")
    store.save_research_record("experiment", "exp-1", {"dataset": "bars-v1"})
    assert store.get_research_record("exp-1") == {
        "record_type": "experiment", "dataset": "bars-v1"
    }
    store.save_trading_record("demo_account", "account-1", "demo", {"broker": "demo"})
    import pytest
    with pytest.raises(ValueError, match="Live trading persistence is disabled"):
        store.save_trading_record("order", "order-live-1", "live", {"side": "buy"})
    store.close()


def test_knowledge_sources_are_provenance_preserving_and_immutable(tmp_path):
    from datetime import datetime, timezone
    import pytest

    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'knowledge.db'}")
    source = {
        "id": "source-1",
        "title": "Public source",
        "url": "https://example.org/ict",
        "source_type": "web",
        "usage_basis": "official_public_excerpt",
        "retrieved_at": datetime(2026, 11, 4, tzinfo=timezone.utc),
        "metadata": {"publisher": "official"},
    }
    chunks = [{"ordinal": 0, "text": "Liquidity sweep and displacement"}]
    store.save_knowledge_source(source, chunks)
    results = store.search_knowledge("liquidity displacement")
    assert results[0]["segment_id"] == "source-1:0"
    assert results[0]["url"] == source["url"]
    with pytest.raises(ValueError, match="immutable"):
        store.save_knowledge_source(source, chunks)
    store.close()
