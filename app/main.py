import os
import time
import uuid
import uuid
from collections import defaultdict, deque
import json
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

from jsonschema import Draft202012Validator

from fastapi import Depends, FastAPI, HTTPException
from starlette.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.schemas import TaskCreate, TaskView, ApprovalDecision, StrategyVersionCreate, ExperimentCreate, KnowledgeSourceCreate, ICTMentorInvocationCreate, StrategyTransitionCreate
from app.services.orchestrator import Orchestrator
from app.services.registry import AgentRegistry
from app.services.governance import GovernanceService
from app.services.model_router import ModelRouter
from app.agents.ict_mentor import ICTMentorRuntime
from app.services.strategy_lifecycle import evaluate_transition
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



_RATE_LIMIT_WINDOW = 60.0
_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("NEXUS_RATE_LIMIT_PER_MINUTE", "120"))
_MAX_REQUEST_BYTES = int(os.getenv("NEXUS_MAX_REQUEST_BYTES", "1048576"))
_REQUEST_TIMES = defaultdict(deque)


class RequestGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > _MAX_REQUEST_BYTES:
                    response = JSONResponse({"detail": "Request body too large"}, status_code=413)
                    response.headers["X-Request-ID"] = request_id
                    return response
            except ValueError:
                response = JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
                response.headers["X-Request-ID"] = request_id
                return response

        if request.url.path != "/health":
            client_host = request.client.host if request.client else "unknown"
            now = time.monotonic()
            bucket = _REQUEST_TIMES[client_host]
            while bucket and now - bucket[0] >= _RATE_LIMIT_WINDOW:
                bucket.popleft()
            if len(bucket) >= _RATE_LIMIT_MAX_REQUESTS:
                response = JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
                response.headers["X-Request-ID"] = request_id
                response.headers["Retry-After"] = "60"
                return response
            bucket.append(now)

        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


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
app.add_middleware(RequestGuardMiddleware)

registry = AgentRegistry()
governance = GovernanceService(store)
model_router = ModelRouter.from_env()
orchestrator = Orchestrator(registry, governance, store, model_router)
ict_mentor_runtime = ICTMentorRuntime(model_router, store)


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
    if task is not None:
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



def _validate_contract(schema_name: str, payload: dict) -> None:
    schema_path = Path(__file__).resolve().parents[1] / "docs" / "strategy-research" / "schemas" / schema_name
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: list(error.path))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Research schema is unavailable or invalid") from exc
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "$"
        raise HTTPException(status_code=422, detail=f"Invalid research contract at {location}: {first.message}")


@app.post("/strategies/{strategy_id}/versions")
def create_strategy_version(
    strategy_id: str,
    payload: StrategyVersionCreate,
    reviewer_id: str = Depends(require_admin),
):
    data = payload.data
    if data.get("strategy_id") != strategy_id:
        raise HTTPException(status_code=422, detail="strategy_id in payload must match URL")
    _validate_contract("strategy.schema.json", data)
    try:
        record_id = store.create_strategy_version(strategy_id, data["version"], data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    store.append_audit({
        "event": "strategy_version_created",
        "strategy_id": strategy_id,
        "version": data["version"],
        "actor": reviewer_id,
        "status": data["status"],
    })
    return {"id": record_id, "strategy_id": strategy_id, "version": data["version"], "status": data["status"]}


@app.get("/strategies/{strategy_id}/versions/{version}", dependencies=[Depends(authenticate)])
def get_strategy_version(strategy_id: str, version: str):
    data = store.get_strategy_version(strategy_id, version)
    if data is None:
        raise HTTPException(status_code=404, detail="Strategy version not found")
    return {"strategy_id": strategy_id, "version": version, "data": data}


@app.post("/research/experiments")
def create_experiment(
    payload: ExperimentCreate,
    reviewer_id: str = Depends(require_admin),
):
    data = payload.data
    _validate_contract("experiment-plan.schema.json", data)
    try:
        store.save_research_record("experiment", data["experiment_id"], data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    store.append_audit({
        "event": "research_experiment_created",
        "experiment_id": data["experiment_id"],
        "actor": reviewer_id,
        "strategy_id": data["strategy_id"],
        "strategy_version": data["strategy_version"],
    })
    return {"experiment_id": data["experiment_id"], "status": "registered"}


@app.get("/research/experiments/{experiment_id}", dependencies=[Depends(authenticate)])
def get_experiment(experiment_id: str):
    record = store.get_research_record(experiment_id)
    if record is None or record.get("record_type") != "experiment":
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"experiment_id": experiment_id, "data": {k: v for k, v in record.items() if k != "record_type"}}


@app.post("/knowledge/sources")
def create_knowledge_source(
    payload: KnowledgeSourceCreate,
    reviewer_id: str = Depends(require_admin),
):
    parsed_url = urlparse(payload.url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise HTTPException(status_code=422, detail="Knowledge source URL must be HTTPS")
    try:
        retrieved_at = datetime.fromisoformat(payload.retrieved_at.replace("Z", "+00:00"))
        if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    chunks = [chunk.model_dump() for chunk in payload.chunks]
    ordinals = [chunk["ordinal"] for chunk in chunks]
    if len(ordinals) != len(set(ordinals)):
        raise HTTPException(status_code=422, detail="Chunk ordinals must be unique")
    try:
        store.save_knowledge_source(
            {
                "id": payload.id,
                "title": payload.title,
                "url": payload.url,
                "source_type": payload.source_type,
                "usage_basis": payload.usage_basis,
                "retrieved_at": retrieved_at,
                "metadata": payload.metadata,
            },
            chunks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    store.append_audit({
        "event": "knowledge_source_ingested",
        "source_id": payload.id,
        "actor": reviewer_id,
        "usage_basis": payload.usage_basis,
        "chunk_count": len(chunks),
    })
    return {"source_id": payload.id, "status": "indexed", "chunk_count": len(chunks)}


@app.get("/knowledge/search", dependencies=[Depends(authenticate)])
def search_knowledge(q: str, limit: int = 10):
    if not q.strip() or len(q) > 500:
        raise HTTPException(status_code=422, detail="Query must contain 1 to 500 characters")
    results = store.search_knowledge(q, limit)
    return {"query": q, "results": results, "retrieval_mode": "lexical_baseline"}


@app.post("/agents/ict-mentor/invoke", dependencies=[Depends(authenticate)])
def invoke_ict_mentor(payload: ICTMentorInvocationCreate):
    invocation = {
        **payload.model_dump(),
        "mode": "advisory",
    }
    try:
        result = ict_mentor_runtime.invoke(invocation)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store.append_audit({
        "event": "ict_mentor_invoked",
        "task_type": payload.task_type,
        "risk_decision": result["risk_decision"],
        "source_claim_count": len(result["source_claims"]),
    })
    return result


@app.post("/strategies/{strategy_id}/versions/{version}/transitions")
def transition_strategy(
    strategy_id: str,
    version: str,
    payload: StrategyTransitionCreate,
    reviewer_id: str = Depends(require_admin),
):
    strategy = store.get_strategy_version(strategy_id, version)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy version not found")
    history = store.list_strategy_transitions(strategy_id)
    current_state = history[-1]["to_state"] if history else strategy["status"]
    decision = evaluate_transition(current_state, payload.target_state, payload.evidence)
    if not decision.allowed:
        store.append_audit({
            "event": "strategy_transition_blocked",
            "strategy_id": strategy_id,
            "version": version,
            "from_state": current_state,
            "to_state": payload.target_state,
            "missing_evidence": list(decision.missing_evidence),
            "actor": reviewer_id,
        })
        raise HTTPException(
            status_code=409,
            detail={"reason": decision.reason, "missing_evidence": list(decision.missing_evidence)},
        )
    transition = {
        "transition_id": str(uuid.uuid4()),
        "strategy_id": strategy_id,
        "version": version,
        "from_state": current_state,
        "to_state": payload.target_state,
        "evidence": payload.evidence,
        "actor": reviewer_id,
        "recorded_at": datetime.now().astimezone().isoformat(),
    }
    store.save_research_record("strategy_transition", transition["transition_id"], transition)
    store.append_audit({
        "event": "strategy_transition_accepted",
        "strategy_id": strategy_id,
        "version": version,
        "from_state": current_state,
        "to_state": payload.target_state,
        "actor": reviewer_id,
    })
    return transition


@app.get("/strategies/{strategy_id}/versions/{version}/transitions", dependencies=[Depends(authenticate)])
def get_strategy_transitions(strategy_id: str, version: str):
    strategy = store.get_strategy_version(strategy_id, version)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy version not found")
    history = [item for item in store.list_strategy_transitions(strategy_id) if item["version"] == version]
    current_state = history[-1]["to_state"] if history else strategy["status"]
    return {"strategy_id": strategy_id, "version": version, "current_state": current_state, "history": history}
