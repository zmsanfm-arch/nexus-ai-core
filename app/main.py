import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.schemas import TaskCreate, TaskView, ApprovalDecision
from app.services.orchestrator import Orchestrator
from app.services.registry import AgentRegistry
from app.services.governance import GovernanceService
from app.services.model_router import ModelRouter
from app.security import authenticate, require_admin
from app.storage import store


app = FastAPI(
    title="NEXUS AI CORE",
    version="0.2.0",
    description="Central NEXUS orchestration and governance API",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("NEXUS_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response


app.add_middleware(SecurityHeadersMiddleware)

registry = AgentRegistry()
governance = GovernanceService(store)
model_router = ModelRouter.from_env()
orchestrator = Orchestrator(registry, governance, store, model_router)


@app.get("/health")
def health():
    # Public liveness only; do not disclose model/provider configuration.
    return {"status": "ok", "service": "nexus-ai-core"}


@app.get("/agents", dependencies=[Depends(authenticate)])
def list_agents():
    return {"agents": registry.list_agents()}


@app.post("/tasks", response_model=TaskView, dependencies=[Depends(authenticate)])
def create_task(payload: TaskCreate):
    return orchestrator.submit(payload.objective)


@app.get("/tasks/{task_id}", response_model=TaskView, dependencies=[Depends(authenticate)])
def get_task(task_id: str):
    task = store.get_task(task_id)
    if not task is None:
        return task
    raise HTTPException(status_code=404, detail="Task not found")


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
