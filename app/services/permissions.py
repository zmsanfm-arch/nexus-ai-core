from __future__ import annotations

from collections.abc import Mapping


# This policy is owned by NEXUS CORE. A manifest cannot expand this allowlist.
CAPABILITY_PERMISSIONS = {
    "ict.education": "ict.advisory.education",
    "ict.source_lookup": "ict.advisory.source_lookup",
    "ict.chart_analysis": "ict.advisory.chart_analysis",
    "ict.strategy_formalization": "ict.advisory.strategy_formalization",
    "ict.trade_review": "ict.advisory.trade_review",
}

CORE_ALLOWED_PERMISSIONS = frozenset(CAPABILITY_PERMISSIONS.values())


class PermissionDenied(RuntimeError):
    """Raised when central policy does not authorize a specialist capability."""


class PermissionService:
    """Deterministic allowlist gate; manifest declarations alone never grant access."""

    def __init__(
        self,
        capability_permissions: Mapping[str, str] | None = None,
        allowed_permissions: frozenset[str] = CORE_ALLOWED_PERMISSIONS,
    ):
        self.capability_permissions = dict(
            CAPABILITY_PERMISSIONS if capability_permissions is None else capability_permissions
        )
        self.allowed_permissions = frozenset(allowed_permissions)

    def authorize(self, agent: dict, capability: str) -> str:
        required = self.capability_permissions.get(capability)
        if required is None:
            raise PermissionDenied("No central permission policy exists for this capability.")
        if required not in self.allowed_permissions:
            raise PermissionDenied("Required permission is not allowed by central policy.")
        declared = agent.get("permissions", [])
        if not isinstance(declared, (list, tuple, set, frozenset)):
            raise PermissionDenied("Agent permission declaration is invalid.")
        if required not in declared:
            raise PermissionDenied("Agent has not been granted the required permission.")
        if agent.get("mode") != "advisory":
            raise PermissionDenied("Only advisory specialist permissions are supported.")
        return required
