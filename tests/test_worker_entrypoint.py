import pytest

from app.worker_entrypoint import build_handler


class FakeFramework:
    def __init__(self, verdict="pass"):
        self.calls = []
        self.verdict = verdict

    def run(self, task_id, objective):
        self.calls.append((task_id, objective))
        return {
            "research": {"summary": "research", "findings": [], "limitations": []},
            "analysis": {"summary": "analysis", "findings": [], "limitations": []},
            "audit": {
                "verdict": self.verdict,
                "summary": "audited",
                "findings": [],
                "limitations": [],
            },
        }


def test_worker_handler_runs_generic_task_and_preserves_audit_verdict():
    framework = FakeFramework("revise")
    handler = build_handler(framework)
    result = handler({
        "id": "task-1",
        "task_type": "general",
        "objective": "Review this planning objective",
        "context": {"source": "user supplied"},
    })

    assert result["execution_status"] == "completed"
    assert result["audit_verdict"] == "revise"
    assert framework.calls[0][0] == "task-1"
    assert "Untrusted user context" in framework.calls[0][1]


@pytest.mark.parametrize("task_type", ["ict.chart_analysis", "trade.execute", "unknown"])
def test_worker_rejects_unregistered_specialist_and_execution_task_types(task_type):
    framework = FakeFramework()
    handler = build_handler(framework)
    with pytest.raises(ValueError, match="No approved worker handler"):
        handler({
            "id": "task-2",
            "task_type": task_type,
            "objective": "Review this planning objective",
            "context": {},
        })
    assert framework.calls == []


def test_worker_rejects_invalid_task_payload_before_model_call():
    framework = FakeFramework()
    handler = build_handler(framework)
    with pytest.raises(ValueError, match="objective is invalid"):
        handler({"id": "task-3", "objective": "bad", "context": {}})
    assert framework.calls == []
