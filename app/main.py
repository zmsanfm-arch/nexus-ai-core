import hmac
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from app.schemas import TaskCreate, TaskView, ApprovalDecision, KnowledgeSourceCreate
from app.services.orchestrator import Orchestrator
from app.services.registry import AgentRegistry
from app.services.governance import GovernanceService
from app.services.model_router import ModelRouter
from app.storage import store
from app.services.task_lifecycle import TaskQueueService
from app.services.knowledge_store import KnowledgeStoreAdapter

app = FastAPI(
    title="NEXUS AI CORE",
    version="0.2.0",
    description="Autonomous multi-agent system foundation",
)

registry = AgentRegistry()
governance = GovernanceService(store)
model_router = ModelRouter.from_env()
orchestrator = Orchestrator(registry, governance, store, model_router)
task_queue = TaskQueueService(store)
knowledge_store = KnowledgeStoreAdapter(store)


def require_api_access(authorization: str | None = Header(default=None)) -> str:
    expected_token = os.getenv("NEXUS_API_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=503, detail="API access is not configured")
    scheme, _, supplied_token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied_token:
        raise HTTPException(status_code=401, detail="Bearer authentication required")
    if not hmac.compare_digest(supplied_token, expected_token):
        raise HTTPException(status_code=403, detail="Invalid API credentials")
    principal_id = os.getenv("NEXUS_API_CLIENT_ID", "api-client")
    if not principal_id or len(principal_id) > 128:
        raise HTTPException(status_code=503, detail="API principal identity is invalid")
    return principal_id


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
def list_agents(_: str = Depends(require_api_access)):
    return {"agents": registry.list_agents()}


@app.post("/tasks", response_model=TaskView)
def create_task(
    payload: TaskCreate,
    principal_id: str = Depends(require_api_access),
):
    return orchestrator.submit(payload.objective, payload.task_type, payload.context, principal_id=principal_id)



@app.post("/tasks/queued", response_model=TaskView)
def enqueue_task(payload: TaskCreate, principal_id: str = Depends(require_api_access)):
    try:
        return task_queue.enqueue(payload.objective, payload.task_type, payload.context, principal_id=principal_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/tasks/{task_id}", response_model=TaskView)
def get_task(task_id: str, principal_id: str = Depends(require_api_access)):
    task = store.get_task(task_id)
    if not task or task.get("principal_id", "api-client") != principal_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/audit")
def list_audit(
    limit: int = 100,
    reviewer_id: str = Depends(require_admin),
):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    return {"events": store.list_audit(limit=limit)}


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


@app.post("/knowledge/sources")
def create_knowledge_source(
    payload: KnowledgeSourceCreate,
    reviewer_id: str = Depends(require_admin),
):
    parsed = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(payload.url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Knowledge source URL must be HTTPS")
    try:
        knowledge_store.save_knowledge_source(
            {
                "id": payload.id,
                "title": payload.title,
                "url": payload.url,
                "source_type": payload.source_type,
                "usage_basis": payload.usage_basis,
                "retrieved_at": payload.retrieved_at,
            },
            [chunk.model_dump() for chunk in payload.chunks],
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    store.append_audit({
        "event": "knowledge_source_ingested",
        "source_id": payload.id,
        "actor": reviewer_id,
        "usage_basis": payload.usage_basis,
        "chunk_count": len(payload.chunks),
    })
    return {"source_id": payload.id, "status": "indexed", "chunk_count": len(payload.chunks)}


@app.get("/knowledge/search")
def search_knowledge(
    q: str,
    limit: int = 8,
    principal_id: str = Depends(require_api_access),
):
    if not q.strip() or len(q) > 500:
        raise HTTPException(status_code=422, detail="Query must contain 1 to 500 characters")
    try:
        results = knowledge_store.search_knowledge(q, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"query": q, "results": results, "retrieval_mode": "lexical_baseline"}
