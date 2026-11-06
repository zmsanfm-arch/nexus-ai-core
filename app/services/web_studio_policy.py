"""Fail-closed action policy for the Web Development Studio.

This module is a policy contract, not an execution adapter. It deliberately
does not grant connector access or external side-effect permissions to Web Studio.
"""
from __future__ import annotations

from dataclasses import dataclass


class WebStudioActionDenied(PermissionError):
    """Raised when a requested action is not explicitly permitted."""


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    approval_required: bool
    reason: str


# Only local, non-destructive planning is permitted without approval.
# These identifiers do not imply that a corresponding runtime handler exists.
LOCAL_ADVISORY_ACTIONS = frozenset({
    "brief.analyze",
    "research.summarize_supplied_material",
    "ia.propose",
    "design.specify",
    "content.draft",
    "seo.review",
    "accessibility.review",
    "code.propose",
    "qa.review",
})

HUMAN_APPROVAL_ACTIONS = frozenset({
    "deployment.production",
    "dns.change",
    "tls.change",
    "secret.write",
    "payment.configure",
    "account.modify",
    "database.migrate_destructive",
    "customer_data.access",
    "cms.publish",
    "content.publish",
    "repository.write",
})


class WebStudioActionPolicy:
    """Default-deny policy; approval is necessary but never sufficient here."""

    def evaluate(self, action: str, *, human_approved: bool = False) -> ActionDecision:
        if action in LOCAL_ADVISORY_ACTIONS:
            return ActionDecision(
                allowed=True,
                approval_required=False,
                reason="local_advisory_only",
            )
        if action in HUMAN_APPROVAL_ACTIONS:
            return ActionDecision(
                allowed=False,
                approval_required=True,
                reason="human_approval_and_separate_execution_adapter_required",
            )
        return ActionDecision(
            allowed=False,
            approval_required=True,
            reason="unknown_action_denied_by_default",
        )

    def require_advisory(self, action: str) -> None:
        decision = self.evaluate(action)
        if not decision.allowed:
            raise WebStudioActionDenied(decision.reason)
