import json

from app.services.orchestrator import Orchestrator
from app.storage import InMemoryStore


class FakeModelRouter:
    def __init__(self, verdict="pass", verdicts=None):
        self.calls = []
        self.verdict = verdict
        self.verdicts = list(verdicts or [])

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        if "Auditor Agent" in system_prompt:
            verdict = self.verdicts.pop(0) if self.verdicts else self.verdict
            result = {
                "verdict": verdict,
                "summary": "Review complete",
                "findings": ["Clarify evidence"] if verdict == "revise" else [],
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
    assert set(report) == {"research", "analysis", "audit", "revision_rounds"}
    assert report["revision_rounds"] == 0


def test_revise_then_pass_retries_analysis_and_auditor_once():
    store = InMemoryStore()
    router = FakeModelRouter(verdicts=["revise", "pass"])
    task = make_orchestrator(router, store).submit("Analyze a sample planning objective")

    assert task["status"] == "completed"
    assert len(router.calls) == 5
    report = json.loads(task["result"])
    assert report["audit"]["verdict"] == "pass"
    assert report["revision_rounds"] == 1
    events = [item["event"] for item in store.audit]
    assert events.count("agent_revision_started") == 1
    assert events.count("agent_revision_completed") == 1


def test_permanent_revision_is_blocked_after_bounded_retries():
    store = InMemoryStore()
    router = FakeModelRouter("revise")
    task = make_orchestrator(router, store).submit("Analyze a sample planning objective")

    assert task["status"] == "blocked"
    assert len(router.calls) == 7
    report = json.loads(task["result"])
    assert report["audit"]["verdict"] == "block"
    assert report["revision_rounds"] == 2
    assert any(
        "Revision limit reached" in item
        for item in report["audit"]["limitations"]
    )


def test_auditor_block_stops_without_revision():
    store = InMemoryStore()
    router = FakeModelRouter("block")
    task = make_orchestrator(router, store).submit("Analyze a sample planning objective")

    assert task["status"] == "blocked"
    assert len(router.calls) == 3


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
