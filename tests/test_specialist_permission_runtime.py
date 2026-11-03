import pytest

from app.services.specialist_contract import SpecialistInput, SpecialistResult
from app.services.specialist_runtime import SpecialistRuntime, SpecialistUnavailable
from app.storage import InMemoryStore


class Registry:
    def __init__(self, permissions):
        self.permissions = permissions

    def resolve_capability(self, capability):
        return [{
            "id": "ict_mentor",
            "mode": "advisory",
            "permissions": self.permissions,
        }]


class Handler:
    def __init__(self):
        self.called = False

    def run(self, request):
        self.called = True
        return SpecialistResult(
            agent_id="ict_mentor",
            mode="advisory",
            answer="Advisory only",
        )


def test_runtime_blocks_handler_when_manifest_has_no_permission():
    handler = Handler()
    store = InMemoryStore()
    runtime = SpecialistRuntime(
        Registry([]),
        store,
        handlers={"ict_mentor": handler},
    )
    request = SpecialistInput(task_id="task-1", task_type="ict.education")

    with pytest.raises(SpecialistUnavailable, match="not been granted"):
        runtime.run("ict.education", request)

    assert handler.called is False


def test_runtime_dispatches_only_when_manifest_and_core_policy_allow():
    handler = Handler()
    runtime = SpecialistRuntime(
        Registry(["ict.advisory.education"]),
        InMemoryStore(),
        handlers={"ict_mentor": handler},
    )
    request = SpecialistInput(task_id="task-2", task_type="ict.education")

    result = runtime.run("ict.education", request)

    assert handler.called is True
    assert result.execution_result is None
