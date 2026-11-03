import pytest

from app.schemas import TaskCreate
from app.services.orchestrator import Orchestrator
from app.services.registry import AgentRegistry
from app.services.specialist_contract import SpecialistInput, SpecialistResult
from app.services.specialist_runtime import SpecialistRuntime, SpecialistUnavailable
from app.storage import InMemoryStore


class FakeRouter:
    def generate(self, system_prompt, user_prompt):
        raise AssertionError("ICT specialist task must not enter generic model pipeline")


def test_disabled_ict_task_fails_closed_at_orchestrator():
    store = InMemoryStore()
    orchestrator = Orchestrator(AgentRegistry(), object(), store, FakeRouter())
    task = orchestrator.submit(
        "Analyze this XAUUSD chart",
        task_type="ict.chart_analysis",
        context={"symbol": "XAUUSD"},
    )
    assert task["status"] == "blocked"
    assert task["assigned_agent"] is None
    assert "No uniquely enabled specialist" in task["result"]


def test_task_create_accepts_typed_task_and_context():
    payload = TaskCreate(
        objective="Explain liquidity sweeps",
        task_type="ict.education",
        context={"market": "XAUUSD"},
    )
    assert payload.task_type == "ict.education"
    assert payload.context["market"] == "XAUUSD"


def test_unknown_task_type_is_not_fallback_routed():
    store = InMemoryStore()
    orchestrator = Orchestrator(AgentRegistry(), object(), store, FakeRouter())
    task = orchestrator.submit("Do an unknown specialist task", task_type="unknown.execute")
    assert task["status"] == "blocked"


def test_specialist_runtime_requires_handler_even_if_registered():
    class Registry:
        def resolve_capability(self, capability):
            return [{"id": "demo_specialist", "status": "registered"}]

    runtime = SpecialistRuntime(Registry(), InMemoryStore())
    request = SpecialistInput(task_id="task-1", task_type="demo.run")
    with pytest.raises(SpecialistUnavailable):
        runtime.run("demo.run", request)


def test_specialist_result_is_advisory_and_execution_is_null():
    result = SpecialistResult(
        agent_id="ict_mentor",
        mode="advisory",
        answer="Chart analysis only",
    )
    assert result.execution_result is None
