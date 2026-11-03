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
