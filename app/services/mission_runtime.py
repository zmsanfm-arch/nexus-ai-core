"""Bounded, sequential execution for advisory-only specialist missions.

This runtime deliberately has no connector, credential, or external-action API.
"""
from __future__ import annotations

import json
from typing import Any

from app.services.mission_audit import MissionAuditResult
from app.services.mission_contract import MissionDefinition, compile_mission
from app.services.permissions import PermissionDenied, PermissionService
from app.services.specialist_contract import SpecialistInput, SpecialistResult


class MissionExecutionError(RuntimeError):
    pass


class MissionRuntime:
    """Executes advisory specialists and optionally requires a separate auditor.

    Execution is sequential. A node is eligible only after all dependencies
    succeeded, and each node is bounded by its declared max_attempts.
    The final auditor is injected separately and is never selected as a node
    handler by this runtime.
    """

    def __init__(
        self, registry, storage, handlers, permission_service=None, auditor=None
    ):
        self.registry = registry
        self.storage = storage
        self.handlers = dict(handlers)
        self.permission_service = permission_service or PermissionService()
        self.auditor = auditor

    def _audit(self, event: str, mission: MissionDefinition, **fields: Any) -> None:
        self.storage.append_audit({
            "event": event,
            "mission_id": mission.mission_id,
            **fields,
        })

    def execute(self, mission: MissionDefinition, *, task_id: str) -> dict:
        agents = {item["id"]: item for item in self.registry.list_agents()}
        plan = compile_mission(mission, set(agents))
        self._audit(
            "mission_execution_started",
            mission,
            task_id=task_id,
            node_count=len(plan.ordered_nodes),
            attempt_budget=plan.max_attempts,
        )

        mission_nodes = {item.node_id: item for item in mission.nodes}
        outputs: dict[str, dict] = {}
        attempts_used = 0
        for node in plan.ordered_nodes:
            mission_node = mission_nodes[node.node_id]
            agent = agents[node.agent_id]
            capability = mission_node.capability
            if agent.get("status") != "registered":
                return self._blocked(mission, task_id, node.node_id, "agent_disabled", outputs)
            if agent.get("mode") != "advisory":
                return self._blocked(mission, task_id, node.node_id, "unsupported_agent_mode", outputs)
            if capability not in agent.get("capabilities", []):
                return self._blocked(mission, task_id, node.node_id, "capability_not_declared", outputs)
            try:
                permission = self.permission_service.authorize(agent, capability)
            except PermissionDenied:
                return self._blocked(mission, task_id, node.node_id, "permission_denied", outputs)

            handler = self.handlers.get(node.agent_id)
            if handler is None:
                return self._blocked(mission, task_id, node.node_id, "handler_unavailable", outputs)

            dependency_context = {
                dependency: outputs[dependency]
                for dependency in node.dependencies
            }
            request = SpecialistInput(
                task_id=task_id,
                task_type=capability,
                request=mission.objective,
                context={
                    "mission_id": mission.mission_id,
                    "mission_name": mission.name,
                    "node_id": node.node_id,
                    "dependency_outputs": dependency_context,
                },
            )
            succeeded = False
            for attempt in range(1, mission_node.max_attempts + 1):
                attempts_used += 1
                self._audit(
                    "mission_node_started",
                    mission,
                    task_id=task_id,
                    node_id=node.node_id,
                    agent_id=node.agent_id,
                    capability=capability,
                    attempt=attempt,
                    permission=permission,
                )
                try:
                    result = handler.run(request)
                    if not isinstance(result, SpecialistResult):
                        raise MissionExecutionError("invalid_result_type")
                    if result.agent_id != node.agent_id or result.mode != "advisory":
                        raise MissionExecutionError("result_identity_or_mode_mismatch")
                    if result.execution_result is not None:
                        raise MissionExecutionError("execution_result_forbidden")
                    output = result.model_dump(mode="json")
                    if len(json.dumps(output, ensure_ascii=False).encode("utf-8")) > 16_384:
                        raise MissionExecutionError("specialist_output_too_large")
                    outputs[node.node_id] = output
                    self._audit(
                        "mission_node_completed",
                        mission,
                        task_id=task_id,
                        node_id=node.node_id,
                        agent_id=node.agent_id,
                        attempt=attempt,
                    )
                    succeeded = True
                    break
                except Exception as exc:
                    self._audit(
                        "mission_node_attempt_failed",
                        mission,
                        task_id=task_id,
                        node_id=node.node_id,
                        agent_id=node.agent_id,
                        attempt=attempt,
                        error_type=type(exc).__name__,
                    )
            if not succeeded:
                self._audit(
                    "mission_execution_failed",
                    mission,
                    task_id=task_id,
                    node_id=node.node_id,
                    reason="attempt_limit_reached",
                )
                return {
                    "status": "failed",
                    "mission_id": mission.mission_id,
                    "task_id": task_id,
                    "failed_node": node.node_id,
                    "reason": "attempt_limit_reached",
                    "outputs": outputs,
                    "attempts_used": attempts_used,
                    "final_audit": "not_performed",
                }

        if self.auditor is None:
            self._audit(
                "mission_nodes_succeeded",
                mission,
                task_id=task_id,
                attempts_used=attempts_used,
                final_audit="not_performed",
            )
            return {
                "status": "nodes_succeeded",
                "mission_id": mission.mission_id,
                "task_id": task_id,
                "outputs": outputs,
                "attempts_used": attempts_used,
                "final_audit": "not_performed",
            }

        try:
            audit_payload = json.dumps(
                {"mission_id": mission.mission_id, "objective": mission.objective,
                 "outputs": outputs},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if len(audit_payload.encode("utf-8")) > 32_768:
                raise MissionExecutionError("audit_input_too_large")
            raw_audit = self.auditor.audit(mission=mission, outputs=outputs)
            audit = MissionAuditResult.model_validate(raw_audit)
        except Exception as exc:
            self._audit(
                "mission_final_audit_failed",
                mission,
                task_id=task_id,
                error_type=type(exc).__name__,
            )
            return {
                "status": "audit_failed",
                "mission_id": mission.mission_id,
                "task_id": task_id,
                "outputs": outputs,
                "attempts_used": attempts_used,
                "final_audit": "failed",
            }

        self._audit(
            "mission_final_audit_completed",
            mission,
            task_id=task_id,
            verdict=audit.verdict,
            findings_count=len(audit.findings),
            limitations_count=len(audit.limitations),
        )
        status = {
            "pass": "completed",
            "revise": "review_required",
            "block": "blocked",
        }[audit.verdict]
        self._audit(
            "mission_execution_finished",
            mission,
            task_id=task_id,
            status=status,
            attempts_used=attempts_used,
        )
        return {
            "status": status,
            "mission_id": mission.mission_id,
            "task_id": task_id,
            "outputs": outputs,
            "attempts_used": attempts_used,
            "final_audit": audit.model_dump(mode="json"),
        }

    def _blocked(self, mission, task_id, node_id, reason, outputs):
        self._audit(
            "mission_execution_blocked",
            mission,
            task_id=task_id,
            node_id=node_id,
            reason=reason,
        )
        return {
            "status": "blocked",
            "mission_id": mission.mission_id,
            "task_id": task_id,
            "blocked_node": node_id,
            "reason": reason,
            "outputs": outputs,
            "final_audit": "not_performed",
        }
