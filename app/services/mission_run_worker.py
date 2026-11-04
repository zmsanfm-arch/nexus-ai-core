"""Lease-driven mission worker with durable per-node checkpoints."""
from __future__ import annotations

import json
from typing import Any

from app.services.mission_audit import MissionAuditResult
from app.services.mission_contract import MissionDefinition, compile_mission
from app.services.permissions import PermissionDenied, PermissionService
from app.services.specialist_contract import SpecialistInput, SpecialistResult


class MissionRunWorker:
    """At-least-once worker; completed node checkpoints are resumed, not rerun.

    A process crash during a handler call can cause that in-flight advisory
    call to be retried after lease expiry. Run enqueue is idempotent, and
    completed outputs are durable. No external side effects are exposed.
    """

    def __init__(self, repository, registry, handlers, storage,
                 worker_id: str, auditor=None, permission_service=None,
                 lease_seconds: int = 600, max_queue_attempts: int = 3):
        if not worker_id or len(worker_id) > 128:
            raise ValueError("Invalid worker identity.")
        self.repository = repository
        self.registry = registry
        self.handlers = dict(handlers)
        self.storage = storage
        self.worker_id = worker_id
        self.auditor = auditor
        self.permission_service = permission_service or PermissionService()
        self.lease_seconds = lease_seconds
        self.max_queue_attempts = max_queue_attempts

    def _audit(self, event: str, run_id: str, **fields: Any):
        self.storage.append_audit({"event": event, "run_id": run_id, **fields})

    def run_once(self) -> bool:
        claim = self.repository.claim_next(self.worker_id, self.lease_seconds)
        if claim is None:
            return False
        run_id = claim["run_id"]
        if claim["attempts"] > self.max_queue_attempts:
            self.repository.finish(run_id, self.worker_id, "failed",
                                   "mission_queue_attempt_limit_reached", max_attempts=1)
            return True
        run = self.repository.get_for_worker(run_id)
        if run is None:
            self.repository.finish(run_id, self.worker_id, "failed",
                                   "mission_run_record_missing", max_attempts=1)
            return True

        try:
            mission = MissionDefinition.model_validate({
                key: value for key, value in run.items()
                if key in {"mission_id", "name", "objective", "nodes",
                           "max_total_attempts", "approval_policy"}
            })
            agents = {item["id"]: item for item in self.registry.list_agents()}
            plan = compile_mission(mission, set(agents))
            node_states = {item["node_id"]: item for item in run["nodes"]}
            outputs = {
                node_id: state["output"]
                for node_id, state in node_states.items()
                if state["status"] == "completed" and state["output"] is not None
            }
            mission_nodes = {item.node_id: item for item in mission.nodes}
            self._audit("mission_run_worker_started", run_id,
                        resumed_nodes=len(outputs), queue_attempt=claim["attempts"])

            for planned in plan.ordered_nodes:
                if not self.repository.renew_lease(
                    run_id, self.worker_id, self.lease_seconds
                ):
                    raise RuntimeError("mission_lease_lost")
                state = node_states[planned.node_id]
                if state["status"] == "completed":
                    continue
                spec = mission_nodes[planned.node_id]
                agent = agents.get(planned.agent_id)
                if (agent is None or agent.get("status") != "registered"
                        or agent.get("mode") != "advisory"
                        or spec.capability not in agent.get("capabilities", [])):
                    self.repository.checkpoint_node(
                        run_id, self.worker_id, planned.node_id, "blocked",
                        error="agent_or_capability_not_enabled",
                    )
                    self.repository.finish(run_id, self.worker_id, "blocked",
                                            "agent_or_capability_not_enabled")
                    return True
                try:
                    permission = self.permission_service.authorize(agent, spec.capability)
                except PermissionDenied:
                    self.repository.checkpoint_node(
                        run_id, self.worker_id, planned.node_id, "blocked",
                        error="permission_denied",
                    )
                    self.repository.finish(run_id, self.worker_id, "blocked", "permission_denied")
                    return True

                handler = self.handlers.get(planned.agent_id)
                if handler is None:
                    self.repository.checkpoint_node(
                        run_id, self.worker_id, planned.node_id, "blocked",
                        error="handler_unavailable",
                    )
                    self.repository.finish(run_id, self.worker_id, "blocked", "handler_unavailable")
                    return True

                missing = [dep for dep in planned.dependencies if dep not in outputs]
                if missing:
                    self.repository.finish(run_id, self.worker_id, "blocked",
                                            "dependency_checkpoint_missing")
                    return True

                self.repository.checkpoint_node(
                    run_id, self.worker_id, planned.node_id, "running",
                    increment_attempt=True,
                )
                self._audit("mission_node_started", run_id, node_id=planned.node_id,
                            agent_id=planned.agent_id, permission=permission)
                try:
                    request = SpecialistInput(
                        task_id=run_id,
                        task_type=spec.capability,
                        request=mission.objective,
                        context={
                            "mission_id": mission.mission_id,
                            "mission_name": mission.name,
                            "node_id": planned.node_id,
                            "dependency_outputs": {
                                dep: outputs[dep] for dep in planned.dependencies
                            },
                        },
                        correlation_id=f"{run_id}:{planned.node_id}",
                    )
                    result = handler.run(request)
                    if not isinstance(result, SpecialistResult):
                        raise ValueError("invalid_result_type")
                    if result.agent_id != planned.agent_id or result.mode != "advisory":
                        raise ValueError("result_identity_or_mode_mismatch")
                    if result.execution_result is not None:
                        raise ValueError("execution_result_forbidden")
                    output = result.model_dump(mode="json")
                    if len(json.dumps(output, ensure_ascii=False).encode("utf-8")) > 16_384:
                        raise ValueError("specialist_output_too_large")
                    self.repository.checkpoint_node(
                        run_id, self.worker_id, planned.node_id, "completed",
                        output=output,
                    )
                    outputs[planned.node_id] = output
                    self._audit("mission_node_completed", run_id,
                                node_id=planned.node_id)
                except Exception as exc:
                    self.repository.checkpoint_node(
                        run_id, self.worker_id, planned.node_id, "failed",
                        error=type(exc).__name__,
                    )
                    self._audit("mission_node_attempt_failed", run_id,
                                node_id=planned.node_id, error_type=type(exc).__name__)
                    current = self.repository.get_for_worker(run_id)
                    current_node = next(n for n in current["nodes"]
                                        if n["node_id"] == planned.node_id)
                    terminal = current_node["attempts"] >= spec.max_attempts
                    self.repository.finish(
                        run_id, self.worker_id, "failed", type(exc).__name__,
                        retry_delay_seconds=15,
                        max_attempts=1 if terminal else self.max_queue_attempts,
                    )
                    return True

            if self.auditor is None:
                final_status = "nodes_succeeded"
                self._audit("mission_nodes_succeeded", run_id,
                            final_audit="not_performed")
            else:
                audit_payload = json.dumps(
                    {"mission_id": mission.mission_id,
                     "objective": mission.objective, "outputs": outputs},
                    ensure_ascii=False, separators=(",", ":"),
                )
                if len(audit_payload.encode("utf-8")) > 32_768:
                    raise ValueError("audit_input_too_large")
                audit = MissionAuditResult.model_validate(
                    self.auditor.audit(mission=mission, outputs=outputs)
                )
                final_status = {
                    "pass": "completed", "revise": "review_required",
                    "block": "blocked",
                }[audit.verdict]
                self._audit("mission_final_audit_completed", run_id,
                            verdict=audit.verdict,
                            findings_count=len(audit.findings))
            self.repository.finish(run_id, self.worker_id, final_status)
            self._audit("mission_run_finished", run_id, status=final_status)
        except Exception as exc:
            self._audit("mission_run_failed", run_id,
                        error_type=type(exc).__name__)
            self.repository.finish(
                run_id, self.worker_id, "failed", type(exc).__name__,
                retry_delay_seconds=15, max_attempts=self.max_queue_attempts,
            )
        return True
