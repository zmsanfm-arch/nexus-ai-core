from __future__ import annotations

from app.services.specialist_contract import SpecialistInput, SpecialistResult
from app.services.permissions import PermissionDenied, PermissionService


class SpecialistUnavailable(RuntimeError):
    pass


class SpecialistContractError(RuntimeError):
    pass


class SpecialistRuntime:
    """Dispatches only enabled, explicitly injected specialists; never grants tools."""

    def __init__(self, registry, storage, handlers=None, permission_service=None):
        self.registry = registry
        self.storage = storage
        self.handlers = dict(handlers or {})
        self.permission_service = permission_service or PermissionService()

    def run(self, task_type: str, request: SpecialistInput) -> SpecialistResult:
        matches = self.registry.resolve_capability(task_type)
        if len(matches) != 1:
            raise SpecialistUnavailable(
                f"No uniquely enabled specialist for capability: {task_type}"
            )
        agent = matches[0]
        agent_id = agent["id"]
        try:
            granted_permission = self.permission_service.authorize(agent, task_type)
        except PermissionDenied as exc:
            self.storage.append_audit({
                "event": "specialist_permission_denied",
                "task_id": request.task_id,
                "agent_id": agent_id,
                "task_type": task_type,
                "reason": str(exc),
            })
            raise SpecialistUnavailable(str(exc)) from exc
        handler = self.handlers.get(agent_id)
        if handler is None:
            raise SpecialistUnavailable(
                f"Specialist runtime is not installed: {agent_id}"
            )
        self.storage.append_audit({
            "event": "specialist_invocation_started",
            "task_id": request.task_id,
            "agent_id": agent_id,
            "task_type": task_type,
            "permission": granted_permission,
        })
        try:
            result = handler.run(request)
            if not isinstance(result, SpecialistResult):
                raise SpecialistContractError("Specialist returned an invalid result type.")
            if result.agent_id != agent_id:
                raise SpecialistContractError("Specialist identity mismatch.")
            if result.mode != "advisory":
                raise SpecialistContractError("Only advisory specialist mode is allowed.")
            if result.execution_result is not None:
                raise SpecialistContractError("Specialists cannot return execution results.")
        except Exception as exc:
            self.storage.append_audit({
                "event": "specialist_invocation_failed",
                "task_id": request.task_id,
                "agent_id": agent_id,
                "error_type": type(exc).__name__,
            })
            raise
        self.storage.append_audit({
            "event": "specialist_invocation_completed",
            "task_id": request.task_id,
            "agent_id": agent_id,
        })
        return result
