import pytest

from app.services.strategy_lifecycle import evaluate_transition, assert_transition_allowed


def test_candidate_to_backtested_requires_explicit_cost_and_reproducibility():
    evidence = {
        "valid_dataset": True,
        "pinned_engine_config": True,
        "explicit_cost_model": False,
        "reproducible_run": True,
    }
    decision = evaluate_transition("candidate", "backtested", evidence)
    assert not decision.allowed
    assert decision.missing_evidence == ("explicit_cost_model",)


def test_demo_activation_requires_kill_switch_and_monitoring():
    evidence = {
        "demo_account_verified": True,
        "symbol_mapping_verified": True,
        "execution_permissions_verified": True,
        "monitoring_ready": True,
        "kill_switch_ready": False,
    }
    decision = evaluate_transition("demo_approved", "demo_active", evidence)
    assert not decision.allowed
    assert "Demo promotion is disabled" in decision.reason


def test_active_strategy_can_be_suspended_with_reason():
    decision = evaluate_transition("demo_active", "suspended", {"reason": "stale market data"})
    assert decision.allowed


def test_undefined_transition_is_blocked():
    decision = evaluate_transition("draft", "demo_active", {})
    assert not decision.allowed


def test_demo_promotion_remains_disabled_even_if_client_claims_all_evidence():
    evidence = {
        "acceptance_criteria_passed": True,
        "robustness_passed": True,
        "central_risk_policy_passed": True,
        "central_approval_id": "approval-claimed",
    }
    decision = evaluate_transition("oos_validated", "demo_approved", evidence)
    assert not decision.allowed
    assert "Demo promotion is disabled" in decision.reason
