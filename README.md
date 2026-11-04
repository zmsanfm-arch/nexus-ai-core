# NEXUS AI CORE

NEXUS AI CORE is a cloud-oriented multi-agent system under active MVP development.

## Central foundation

- FastAPI service, manifest-driven specialist registry, and sequential Research → Analysis → Auditor pipeline for untyped tasks.
- Strict Pydantic contracts, bounded JSON inputs, and server-side model configuration.
- SQLAlchemy persistence for tasks, approvals, audit events, and durable task queue leases.
- Authenticated task submission and principal-scoped task reads.
- Admin-only approvals, audit access, and knowledge-source ingestion.
- Specialist dispatch requires both a central permission policy and an explicit manifest grant.

## ICT Mentor integration

The integration branch registers ICT Mentor through the central Orchestrator and SpecialistRuntime for five advisory capabilities: education, source lookup, chart analysis, strategy formalization, and trade review. Each dispatch requires both the central PermissionService and the manifest grant.

The handler retrieves source segments from the NEXUS-owned knowledge store, validates provenance, accepts only explicitly user-confirmed rules, and structurally forbids execution results. Knowledge search uses an indexed lexical baseline with Persian/Arabic Unicode normalization; it is not semantic/vector retrieval.

**Trading boundary:** ICT Mentor is advisory-only. Position monitoring, position management, autonomous execution, MT5/broker connectivity, account/position access, order placement/cancellation, and live trading remain disabled. Backtesting is deterministic research-only midpoint OHLC simulation, not broker-grade execution simulation and never authorizes a trade.

## Model configuration

Configure these in the runtime environment or deployment secret manager:

- `MODEL_BASE_URL`: provider API base URL.
- `MODEL_NAME`: exact model identifier.
- `MODEL_API_KEY`: secret API key; never commit it.
- `MODEL_PROVIDER`: optional provider label.
- `MODEL_TIMEOUT_SECONDS`: optional timeout, default 45.

Without the required model settings, model-dependent tasks return blocked; they do not pretend inference ran.

## Storage and task lifecycle

- Default database: `sqlite:///./data/nexus.db`.
- PostgreSQL: set `DATABASE_URL` when PostgreSQL is provisioned.
- `POST /tasks` executes through the synchronous orchestration path.
- `POST /tasks/queued` durably enqueues a task.
- `GET /tasks/{task_id}` returns a task only to its owning API principal.
- Worker lifecycle primitives implement leases, retries, ownership checks, and dead-letter state; a standalone worker entrypoint and supervised production service are not yet provided.

The repository contains queue and worker lifecycle primitives, but no continuously supervised worker deployment. A production deployment must run a separately supervised worker with an approved task handler. SQLite is for a single-instance MVP; use PostgreSQL before multi-instance workers.

## Authentication and administration

Set these only in a server-side secret manager:

- `NEXUS_API_TOKEN`: bearer token for agent discovery and task APIs.
- `NEXUS_API_CLIENT_ID`: stable server-configured principal ID (default `api-client`).
- `NEXUS_ADMIN_TOKEN`: separate administrator bearer token.
- `NEXUS_ADMIN_ID`: server-configured reviewer identity.

The current token model supports one configured API principal, not multi-user identity, per-token hashing, or token rotation. Protected routes fail closed when required secrets are missing.

## API

- `GET /health`
- `GET /agents`
- `POST /tasks`
- `POST /tasks/queued`
- `GET /tasks/{task_id}`
- `POST /approvals/{approval_id}/decision` (administrator only)
- `GET /audit?limit=100` (administrator only)
- `POST /knowledge/sources` (administrator only)
- `GET /knowledge/search` (authenticated)
- `POST /research/backtests/run` (authenticated; research-only)

## Deployment status and remaining gates

This repository is not yet a production deployment. No cloud host, production identity provider, secret manager, distributed rate limiter, supervised worker service, or operational monitoring has been provisioned. Do not expose it publicly before deployment hardening and independent security review.

## Local development

```bash
pip install -r requirements.txt
pip install pytest
uvicorn app.main:app --reload
pytest -q
```
