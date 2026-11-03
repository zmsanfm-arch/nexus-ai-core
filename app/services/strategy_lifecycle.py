"""Deterministic strategy lifecycle gates; no model output can authorize transitions."""
from dataclasses import dataclass


TRANSITIONS = {
    ("draft", "candidate"): {
        "complete_specification", "deterministic_rules", "provenance_complete",
        "assumptions_documented",
    },
    ("candidate", "backtested"): {
        "valid_dataset", "pinned_engine_config", "explicit_cost_model",
        "reproducible_run",
    },
    ("backtested", "oos_validated"): {
        "holdout_untouched", "walk_forward_completed", "sufficient_sample",
        "no_critical_data_quality_issues",
    },
    ("oos_validated", "demo_approved"): {
        "acceptance_criteria_passed", "robustness_passed",
        "central_risk_policy_passed", "central_approval_id",
    },
    ("demo_approved", "demo_active"): {
        "demo_account_verified", "symbol_mapping_verified",
        "execution_permissions_verified", "monitoring_ready", "kill_switch_ready",
    },
}


@dataclass(frozen=True)
class LifecycleDecision:
    allowed: bool
    current_state: str
    target_state: str
    missing_evidence: tuple[str, ...]
    reason: str


def evaluate_transition(current_state: str, target_state: str, evidence: dict) -> LifecycleDecision:
    if target_state == "retired":
        if evidence.get("reason"):
            return LifecycleDecision(True, current_state, target_state, (), "Explicit retirement reason supplied")
        return LifecycleDecision(False, current_state, target_state, ("reason",), "Retirement requires an audit reason")

    if target_state == "suspended":
        if current_state in {"demo_active", "demo_approved"} and evidence.get("reason"):
            return LifecycleDecision(True, current_state, target_state, (), "Safety suspension")
        return LifecycleDecision(False, current_state, target_state, ("reason",), "Suspension requires an eligible state and reason")

    required = TRANSITIONS.get((current_state, target_state))
    if required is None:
        return LifecycleDecision(False, current_state, target_state, (), "Transition is not defined")
    missing = tuple(sorted(key for key in required if not evidence.get(key)))
    if missing:
        return LifecycleDecision(False, current_state, target_state, missing, "Required evidence is missing")
    return LifecycleDecision(True, current_state, target_state, (), "All transition evidence is present")


def assert_transition_allowed(current_state: str, target_state: str, evidence: dict) -> LifecycleDecision:
    decision = evaluate_transition(current_state, target_state, evidence)
    if not decision.allowed:
        missing = ", ".join(decision.missing_evidence) or decision.reason
        raise ValueError(f"Strategy transition blocked: {missing}")
    return decision
