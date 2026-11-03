import json

from app.services.agent_framework import AgentFramework
from app.services.orchestrator import Orchestrator
from app.storage import InMemoryStore


class FakeModelRouter:
    def __init__(self, verdict="pass"):
        self.calls = []
        self.verdict = verdict

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        if "Auditor Agent" in system_prompt:
            result = {
                "verdict": self.verdict,
                "summary": "Review complete",
                "findings": [],
                "limitations": [],
            }
        else:
            result = {
                "summary": "Agent summary",
                "findings": ["Finding"],
                "limitations": [],
            }
        return json.dumps(result)


def make_orchestrator(router, store):
    class Registry:
        pass

    class Governance:
        pass

    return Orchestrator(Registry(), Governance(), store, router)


def test_three_agents_run_in_order_and_are_audited():
    store = InMemoryStore()
    router = FakeModelRouter()
    task = make_orchestrator(router, store).submit("Analyze a sample planning objective")

    assert task["status"] == "completed"
    assert task["assigned_agent"] == "multi_agent_pipeline"
    assert len(router.calls) == 3
    events = [item["event"] for item in store.audit]
    assert events.count("agent_invocation_started") == 3
    assert events.count("agent_invocation_completed") == 3
    report = json.loads(task["result"])
    assert set(report) == {"research", "analysis", "audit"}


def test_auditor_revision_blocks_completion():
    store = InMemoryStore()
    task = make_orchestrator(FakeModelRouter("revise"), store).submit(
        "Analyze a sample planning objective"
    )
    assert task["status"] == "blocked"


def test_invalid_agent_contract_fails_task():
    class InvalidRouter:
        def generate(self, system_prompt, user_prompt):
            return "not-json"

    store = InMemoryStore()
    task = make_orchestrator(InvalidRouter(), store).submit(
        "Analyze a sample planning objective"
    )
    assert task["status"] == "failed"
    assert any(item["event"] == "agent_invocation_failed" for item in store.audit)
