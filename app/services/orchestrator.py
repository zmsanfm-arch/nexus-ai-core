import uuid
from app.services.risk import classify_risk

class Orchestrator:
    def __init__(self, registry, governance, storage):
        self.registry = registry
        self.governance = governance
        self.storage = storage

    def submit(self, objective: str):
        # MVP behavior: deterministic routing placeholder. No model execution yet.
        risk = classify_risk(objective)
        task = {
            "id": str(uuid.uuid4()),
            "objective": objective,
            "status": "queued",
            "assigned_agent": "research",
            "risk_level": risk,
            "result": "Task accepted. Agent execution is not enabled in this scaffold.",
        }
        self.storage.save_task(task)
        self.storage.append_audit({
            "event": "task_submitted",
            "task_id": task["id"],
            "risk_level": risk,
        })
        return task
