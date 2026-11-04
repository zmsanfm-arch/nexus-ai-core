import uuid

SENSITIVE_ACTIONS = {
    "security_policy_change",
    "sensitive_data_disclosure",
    "asset_transfer",
    "irreversible_deletion",
    "high_risk_operation",
}

class GovernanceService:
    """Deterministic policy gate; independent from model-generated decisions."""
    def __init__(self, storage):
        self.storage = storage

    def requires_approval(self, action_type: str) -> bool:
        return action_type in SENSITIVE_ACTIONS

    def request_approval(self, action_type: str, exact_parameters: dict, requester: str):
        if action_type not in SENSITIVE_ACTIONS:
            raise ValueError("Approval workflow is reserved for classified sensitive actions")
        approval = {
            "id": str(uuid.uuid4()),
            "action_type": action_type,
            "parameters": exact_parameters,
            "requester": requester,
            "status": "pending",
            "reviewer": None,
        }
        self.storage.create_approval_with_audit(approval, {
            "event": "approval_requested",
            "approval_id": approval["id"],
            "action_type": action_type,
            "requester": requester,
        })
        return approval

    def decide(self, approval_id: str, approved: bool, reviewer: str):
        return self.storage.decide_approval_with_audit(approval_id, approved, reviewer)
