import uuid

from app.services.risk import classify_risk
from app.services.model_router import ModelNotConfigured, ModelProviderError


SYSTEM_PROMPT = """You are the reasoning engine of NEXUS AI CORE.
Analyze the user's objective and produce a concise, actionable response.
Do not claim to have executed external actions or accessed tools.
Never request or reveal credentials. Flag financial transfers, data disclosure,
security changes, and irreversible actions as requiring separate authorization."""


class Orchestrator:
    def __init__(self, registry, governance, storage, model_router):
        self.registry = registry
        self.governance = governance
        self.storage = storage
        self.model_router = model_router

    def submit(self, objective: str):
        risk = classify_risk(objective)
        task = {
            "id": str(uuid.uuid4()),
            "objective": objective,
            "status": "running",
            "assigned_agent": "analysis",
            "risk_level": risk,
            "result": None,
        }
        self.storage.save_task(task)
        self.storage.append_audit({
            "event": "task_submitted",
            "task_id": task["id"],
            "risk_level": risk,
        })
        try:
            result = self.model_router.generate(SYSTEM_PROMPT, objective)
            task["status"] = "completed"
            task["result"] = result
        except ModelNotConfigured as exc:
            task["status"] = "blocked"
            task["result"] = str(exc)
        except ModelProviderError as exc:
            task["status"] = "failed"
            task["result"] = str(exc)
        self.storage.save_task(task)
        self.storage.append_audit({
            "event": "task_finished",
            "task_id": task["id"],
            "status": task["status"],
        })
        return task
