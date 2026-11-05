from __future__ import annotations

from collections.abc import Mapping


# Core-owned permissions. Forex-side declarations are requests only; this
# allowlist is the independent authorization boundary.
CAPABILITY_PERMISSIONS = {
    "ict.education": "user_input.read",
    "ict.source_lookup": "knowledge.retrieve",
    "ict.chart_analysis": "chart_attachment.read",
    "ict.strategy_formalization": "user_input.read",
    "ict.trade_review": "user_input.read",
    "web.mission.orchestrate": "mission.plan",
    "web.brief.analyze": "brief.read",
    "web.research.public": "public.research",
    "web.ux.architecture": "ux.design",
    "web.ui.design": "design.create",
    "web.visual.identity": "brand.design",
    "web.motion.design": "motion.design",
    "web.content.plan": "content.plan",
    "web.seo.audit": "seo.audit",
    "web.frontend.build": "sandbox.build",
    "web.backend.build": "sandbox.build",
    "web.cms.integrate": "cms.integrate",
    "web.accessibility.audit": "accessibility.audit",
    "web.browser.test": "browser.execute",
    "web.visual.audit": "visual.audit",
    "web.performance.audit": "performance.audit",
    "web.security.audit": "security.audit",
    "web.conversion.analyze": "conversion.analyze",
    "web.release.prepare": "release.prepare",
    "web.quality.audit": "quality.audit",
    "web.maintenance.review": "maintenance.review",
}

CORE_ALLOWED_PERMISSIONS = frozenset(CAPABILITY_PERMISSIONS.values())


class PermissionDenied(RuntimeError):
    """Raised when central policy does not authorize a specialist capability."""


class PermissionService:
    """A manifest grant and central allowlist are both required."""

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
