import hmac
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from app.schemas import TaskCreate, TaskView, ApprovalDecision
from app.services.orchestrator import Orchestrator
from app.services.registry import AgentRegistry
from app.services.governance import GovernanceService
from app.services.model_router import ModelRouter
from app.storage import store

app = FastAPI(
    title="NEXUS AI CORE",
    version="0.2.0",
    description="Autonomous multi-agent system foundation",
)

registry = AgentRegistry()
governance = GovernanceService(store)
model_router = ModelRouter.from_env()
orchestrator = Orchestrator(registry, governance, store, model_router)


def require_admin(authorization: str | None = Header(default=None)) -> str:
    expected_token = os.getenv("NEXUS_ADMIN_TOKEN")
    reviewer_id = os.getenv("NEXUS_ADMIN_ID")
    if not expected_token or not reviewer_id:
        raise HTTPException(status_code=503, detail="Approval administration is not configured")
    scheme, _, supplied_token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied_token:
        raise HTTPException(status_code=401, detail="Bearer authentication required")
    if not hmac.compare_digest(supplied_token, expected_token):
        raise HTTPException(status_code=403, detail="Invalid administrator credentials")
    return reviewer_id


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "nexus-ai-core",
        "version": "0.2.0",
        "model_configured": model_router.select("health") is not None,
    }


@app.get("/agents")
def list_agents():
    return {"agents": registry.list_agents()}


@app.post("/tasks", response_model=TaskView)
def create_task(payload: TaskCreate):
    return orchestrator.submit(payload.objective, payload.task_type, payload.context)


@app.get("/tasks/{task_id}", response_model=TaskView)
def get_task(task_id: str):
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/approvals/{approval_id}/decision")
def decide_approval(
    approval_id: str,
    payload: ApprovalDecision,
    reviewer_id: str = Depends(require_admin),
):
    try:
        return governance.decide(approval_id, payload.approved, reviewer_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Approval not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
