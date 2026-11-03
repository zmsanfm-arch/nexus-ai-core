import json
import uuid

from app.services.risk import classify_risk
from app.services.model_router import ModelNotConfigured, ModelProviderError
from app.services.agent_framework import AgentFramework, AgentContractError


class Orchestrator:
    def __init__(self, registry, governance, storage, model_router):
        self.registry = registry
        self.governance = governance
        self.storage = storage
        self.model_router = model_router
        self.agent_framework = AgentFramework(model_router, storage)

    def submit(self, objective: str):
        risk = classify_risk(objective)
        task = {
            "id": str(uuid.uuid4()),
            "objective": objective,
            "status": "running",
            "assigned_agent": "multi_agent_pipeline",
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
            report = self.agent_framework.run(task["id"], objective)
            verdict = report["audit"]["verdict"]
            task["status"] = "completed" if verdict == "pass" else "blocked"
            task["result"] = json.dumps(report, ensure_ascii=False)
        except ModelNotConfigured as exc:
            task["status"] = "blocked"
            task["result"] = str(exc)
        except (ModelProviderError, AgentContractError) as exc:
            task["status"] = "failed"
            task["result"] = str(exc)
        self.storage.save_task(task)
        self.storage.append_audit({
            "event": "task_finished",
            "task_id": task["id"],
            "status": task["status"],
        })
        return task
