import pytest
from app.storage import InMemoryStore
from app.services.governance import GovernanceService

def test_sensitive_action_requires_explicit_approval():
    store = InMemoryStore()
    gov = GovernanceService(store)
    item = gov.request_approval("asset_transfer", {"amount": 10, "currency": "USD"}, "user")
    assert item["status"] == "pending"
    result = gov.decide(item["id"], True, "reviewer-1")
    assert result["status"] == "approved"

def test_unknown_approval_fails():
    gov = GovernanceService(InMemoryStore())
    with pytest.raises(KeyError):
        gov.decide("missing", True, "reviewer-1")


def test_approval_decision_and_audit_are_atomic_and_single_use():
    store = InMemoryStore()
    gov = GovernanceService(store)
    approval = gov.request_approval("asset_transfer", {"amount": 25}, "user")
    before = len(store.audit)
    decided = gov.decide(approval["id"], False, "reviewer")
    assert decided["status"] == "rejected"
    assert len(store.audit) == before + 1
    with pytest.raises(ValueError, match="already resolved"):
        gov.decide(approval["id"], True, "second-reviewer")
    assert len(store.audit) == before + 1


def test_sql_approval_decision_and_audit_commit_together(tmp_path):
    from app.storage import SQLAlchemyStore

    store = SQLAlchemyStore(f"sqlite:///{tmp_path / 'approval-atomic.db'}")
    gov = GovernanceService(store)
    approval = gov.request_approval("asset_transfer", {"amount": 25}, "user")
    events_before = len(store.list_audit())
    result = gov.decide(approval["id"], True, "reviewer")
    assert result["status"] == "approved"
    assert store.get_approval(approval["id"])["reviewer"] == "reviewer"
    events = store.list_audit()
    assert len(events) == events_before + 1
    assert events[-1]["event"] == "approval_decided"
    with pytest.raises(ValueError, match="already resolved"):
        gov.decide(approval["id"], False, "other")
    assert len(store.list_audit()) == events_before + 1
    store.close()
