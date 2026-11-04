import pytest

from app.services.mission_contract import MissionDefinition
from app.services.mission_runtime import MissionRuntime
from app.services.permissions import PermissionService
from app.services.specialist_contract import SpecialistResult
from app.storage import InMemoryStore


def mission():
    return MissionDefinition.model_validate({
        "mission_id": "demo_mission",
        "name": "Demo advisory workflow",
        "objective": "Review the supplied information.",
        "nodes": [
            {"node_id": "research", "agent_id": "demo_agent", "capability": "demo.read"},
            {"node_id": "review", "agent_id": "demo_agent", "capability": "demo.read", "dependencies": ["research"], "max_attempts": 2},
        ],
        "max_total_attempts": 3,
    })


class Registry:
    def list_agents(self):
        return [{
            "id": "demo_agent",
            "status": "registered",
            "mode": "advisory",
            "capabilities": ["demo.read"],
            "permissions": ["payload.read"],
        }]


class Handler:
    def __init__(self, fail_first=False):
        self.calls = 0
        self.fail_first = fail_first
        self.requests = []

    def run(self, request):
        self.calls += 1
        self.requests.append(request)
        if self.fail_first and self.calls == 2:
            raise RuntimeError("transient")
        return SpecialistResult(
            agent_id="demo_agent",
            mode="advisory",
            answer="Reviewed",
            source_claims=[],
            user_rules_used=[],
            agent_inferences=[],
            proposed_actions=[],
            risk_decision="not_assessed_by_specialist",
            execution_result=None,
            uncertainties=[],
        )


def runtime(handler, permissions=None):
    policy = PermissionService(
        capability_permissions={"demo.read": "payload.read"},
        allowed_permissions=frozenset({"payload.read"}),
    )
    if permissions is not None:
        policy = PermissionService(
            capability_permissions={"demo.read": "payload.read"},
            allowed_permissions=frozenset(permissions),
        )
    return MissionRuntime(Registry(), InMemoryStore(), {"demo_agent": handler}, policy)


def test_runtime_executes_nodes_sequentially_and_passes_dependency_outputs():
    handler = Handler()
    result = runtime(handler).execute(mission(), task_id="task-1")
    assert result["status"] == "nodes_succeeded"
    assert result["attempts_used"] == 2
    assert result["final_audit"] == "not_performed"
    assert handler.calls == 2
    assert "research" in handler.requests[1].context["dependency_outputs"]


def test_runtime_retries_only_within_node_attempt_budget():
    handler = Handler(fail_first=True)
    result = runtime(handler).execute(mission(), task_id="task-2")
    assert result["status"] == "succeeded"
    assert result["attempts_used"] == 3
    assert handler.calls == 3


def test_runtime_fails_closed_when_central_permission_is_missing():
    handler = Handler()
    result = runtime(handler, permissions=set()).execute(mission(), task_id="task-3")
    assert result["status"] == "blocked"
    assert result["reason"] == "permission_denied"
    assert handler.calls == 0


def test_runtime_does_not_complete_after_attempt_limit():
    class AlwaysFails:
        def __init__(self):
            self.calls = 0

        def run(self, request):
            self.calls += 1
            raise RuntimeError("failure")

    handler = AlwaysFails()
    result = runtime(handler).execute(mission(), task_id="task-4")
    assert result["status"] == "failed"
    assert result["failed_node"] == "research"
    assert handler.calls == 1
