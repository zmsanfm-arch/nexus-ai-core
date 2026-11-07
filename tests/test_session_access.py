import pytest

from app.services.session_access import (
    SessionAccessDenied, SessionAccessPolicy, SessionScope,
)


def _scope():
    return SessionScope(principal_id="tenant-a", session_id="session-1", owner_agent_id="research")


def test_session_owner_can_read_and_write():
    policy = SessionAccessPolicy()
    policy.authorize_read(_scope(), principal_id="tenant-a", agent_id="research")
    policy.authorize_write(_scope(), principal_id="tenant-a", agent_id="research")


def test_other_principal_cannot_read_session():
    with pytest.raises(SessionAccessDenied, match="different principal"):
        SessionAccessPolicy().authorize_read(_scope(), principal_id="tenant-b", agent_id="research")


def test_other_agent_is_denied_by_default():
    with pytest.raises(SessionAccessDenied, match="Cross-agent"):
        SessionAccessPolicy().authorize_read(_scope(), principal_id="tenant-a", agent_id="analysis")


def test_cross_agent_read_requires_exact_grant():
    policy = SessionAccessPolicy(frozenset({("research", "analysis")}))
    policy.authorize_read(_scope(), principal_id="tenant-a", agent_id="analysis")


def test_cross_agent_grant_does_not_allow_write():
    policy = SessionAccessPolicy(frozenset({("research", "analysis")}))
    with pytest.raises(SessionAccessDenied, match="Only the owning agent"):
        policy.authorize_write(_scope(), principal_id="tenant-a", agent_id="analysis")


def test_invalid_scope_fails_closed():
    scope = SessionScope(principal_id="", session_id="session-1", owner_agent_id="research")
    with pytest.raises(SessionAccessDenied, match="session principal"):
        SessionAccessPolicy().authorize_read(scope, principal_id="tenant-a", agent_id="research")