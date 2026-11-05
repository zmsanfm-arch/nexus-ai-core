import pytest

from app.services.web_studio_policy import (
    HUMAN_APPROVAL_ACTIONS,
    LOCAL_ADVISORY_ACTIONS,
    WebStudioActionDenied,
    WebStudioActionPolicy,
)


def test_local_advisory_actions_are_allowed_without_external_effects():
    policy = WebStudioActionPolicy()
    for action in LOCAL_ADVISORY_ACTIONS:
        decision = policy.evaluate(action)
        assert decision.allowed is True
        assert decision.approval_required is False
        policy.require_advisory(action)


def test_sensitive_actions_are_never_executed_by_advisory_policy():
    policy = WebStudioActionPolicy()
    for action in HUMAN_APPROVAL_ACTIONS:
        decision = policy.evaluate(action, human_approved=True)
        assert decision.allowed is False
        assert decision.approval_required is True
        with pytest.raises(WebStudioActionDenied):
            policy.require_advisory(action)


def test_unknown_actions_fail_closed():
    decision = WebStudioActionPolicy().evaluate("arbitrary.external.action")
    assert decision.allowed is False
    assert decision.approval_required is True
    assert decision.reason == "unknown_action_denied_by_default"
