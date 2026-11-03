import json
import uuid

from app.services.risk import classify_risk
from app.services.model_router import ModelNotConfigured, ModelProviderError
from app.services.agent_framework import AgentFramework, AgentContractError
from app.services.specialist_contract import SpecialistInput
from app.services.specialist_runtime import (
    SpecialistRuntime,
    SpecialistUnavailable,
    SpecialistContractError,
)


class Orchestrator:
    def __init__(self, registry, governance, storage, model_router):
        self.registry = registry
        self.governance = governance
        self.storage = storage
        self.model_router = model_router
        self.agent_framework = AgentFramework(model_router, storage)
        self.specialist_runtime = SpecialistRuntime(registry, storage)

    def submit(self, objective: str, task_type: str | None = None, context=None, principal_id: str = "api-client"):
        risk = classify_risk(objective)
        task = {
            "id": str(uuid.uuid4()),
            "objective": objective,
            "task_type": task_type,
            "status": "running",
            "assigned_agent": "multi_agent_pipeline" if task_type is None else None,
            "risk_level": risk,
            "result": None,
            "principal_id": principal_id,
        }
        self.storage.save_task(task)
        self.storage.append_audit({
            "event": "task_submitted",
            "task_id": task["id"],
            "risk_level": risk,
            "task_type": task_type,
            "principal_id": principal_id,
        })
        try:
            if task_type is None:
                report = self.agent_framework.run(task["id"], objective)
                verdict = report["audit"]["verdict"]
                task["status"] = "completed" if verdict == "pass" else "blocked"
                task["result"] = json.dumps(report, ensure_ascii=False)
            else:
                specialist_input = SpecialistInput(
                    task_id=task["id"],
                    task_type=task_type,
                    request=objective,
                    context=context or {},
                )
                result = self.specialist_runtime.run(task_type, specialist_input)
                task["assigned_agent"] = result.agent_id
                task["status"] = "completed"
                task["result"] = result.model_dump_json()
        except (SpecialistUnavailable, SpecialistContractError) as exc:
            task["status"] = "blocked"
            task["result"] = str(exc)
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
            "principal_id": principal_id,
        })
        return task
