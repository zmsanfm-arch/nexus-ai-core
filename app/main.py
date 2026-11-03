from fastapi import FastAPI, HTTPException
from app.schemas import TaskCreate, TaskView, ApprovalDecision
from app.services.orchestrator import Orchestrator
from app.services.registry import AgentRegistry
from app.services.governance import GovernanceService
from app.storage import store

app = FastAPI(title="NEXUS AI CORE", version="0.1.0",
              description="Autonomous multi-agent system foundation")

registry = AgentRegistry()
governance = GovernanceService(store)
orchestrator = Orchestrator(registry, governance, store)

@app.get("/health")
def health():
    return {"status": "ok", "service": "nexus-ai-core", "version": "0.1.0"}

@app.get("/agents")
def list_agents():
    return {"agents": registry.list_agents()}

@app.post("/tasks", response_model=TaskView)
def create_task(payload: TaskCreate):
    task = orchestrator.submit(payload.objective)
    return task

@app.get("/tasks/{task_id}", response_model=TaskView)
def get_task(task_id: str):
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, payload: ApprovalDecision):
    # Authentication is intentionally not mocked. This endpoint must be protected
    # by a real identity provider before deployment outside a local sandbox.
    try:
        result = governance.decide(approval_id, payload.approved, payload.reviewer)
    except KeyError:
        raise HTTPException(status_code=404, detail="Approval not found")
    return result
