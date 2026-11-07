"""Explicit ownership policy for agent session and memory access.

This policy is a reusable authorization primitive. It does not create storage
or expose session APIs; callers must enforce it before every read or write.
"""
from __future__ import annotations

from dataclasses import dataclass


class SessionAccessDenied(PermissionError):
    """Raised when a principal or agent is outside a session access scope."""


@dataclass(frozen=True)
class SessionScope:
    principal_id: str
    session_id: str
    owner_agent_id: str


class SessionAccessPolicy:
    """Deny by default; cross-agent access requires an exact explicit grant."""

    def __init__(self, cross_agent_grants: frozenset[tuple[str, str]] = frozenset()):
        self.cross_agent_grants = frozenset(cross_agent_grants)

    @staticmethod
    def _validate_identifier(value: str, field: str) -> None:
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            raise SessionAccessDenied(f"Invalid {field}.")

    def authorize_read(
        self, scope: SessionScope, *, principal_id: str, agent_id: str
    ) -> None:
        self._validate_identifier(scope.principal_id, "session principal")
        self._validate_identifier(scope.session_id, "session id")
        self._validate_identifier(scope.owner_agent_id, "session owner")
        self._validate_identifier(principal_id, "request principal")
        self._validate_identifier(agent_id, "request agent")
        if principal_id != scope.principal_id:
            raise SessionAccessDenied("Session belongs to a different principal.")
        if agent_id == scope.owner_agent_id:
            return
        if (scope.owner_agent_id, agent_id) not in self.cross_agent_grants:
            raise SessionAccessDenied("Cross-agent session access is not granted.")

    def authorize_write(
        self, scope: SessionScope, *, principal_id: str, agent_id: str
    ) -> None:
        self.authorize_read(scope, principal_id=principal_id, agent_id=agent_id)
        if agent_id != scope.owner_agent_id:
            raise SessionAccessDenied("Only the owning agent may write to this session.")