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
