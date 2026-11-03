# NEXUS AI CORE

NEXUS AI CORE is a cloud-oriented multi-agent system under active MVP development.

## Current central foundation

- FastAPI service, static agents, and manifest-driven specialist registry.
- Sequential Research → Analysis → Auditor pipeline for untyped tasks.
- Strict Pydantic contracts and bounded JSON input.
- OpenAI-compatible model adapter using server-side environment variables.
- SQLAlchemy persistence for tasks, approvals, audit events, and durable task queue leases.
- Authenticated task submission and principal-scoped task reads.
- Admin-only approvals and audit access with server-derived reviewer identity.
- Central specialist authorization requires both a core allowlist entry and an explicit manifest grant.
- Task queue has expiring worker leases, retry limits, dead-letter state, and audit events.

## ICT Mentor integration status

ICT Mentor is registered as disabled and advisory-only. Its initial capabilities are education, source lookup, user-supplied chart analysis, strategy formalization, and trade review.

The central Pydantic contract now models the Forex project's v1 input/output structure, including source provenance, explicitly confirmed user rules, separate model inferences, structured proposed actions, constrained risk-decision vocabulary, and execution_result fixed to null.

The Forex manifest's three permissions are recorded as requests only: knowledge.retrieve, user_input.read, and chart_attachment.read. The granted permissions list remains empty. The specialist therefore cannot be dispatched. There is no ICT handler, no live market/account access, no MT5/broker connection, and no trade execution.

See docs/ICT_INTEGRATION_RECONCILIATION.md and docs/SPECIALIST_AGENT_CONTRACT.md.

## Model configuration

Configure these in the runtime environment or deployment secret manager:

- MODEL_BASE_URL: provider API base URL.
- MODEL_NAME: exact model identifier.
- MODEL_API_KEY: secret API key; never commit it.
- MODEL_PROVIDER: optional provider label.
- MODEL_TIMEOUT_SECONDS: optional timeout, default 45.

Without the required model settings, model-dependent tasks return blocked; they do not pretend inference ran.

## Storage and task lifecycle

- Default database: sqlite:///./data/nexus.db.
- PostgreSQL: set DATABASE_URL when a PostgreSQL service is provisioned.
- POST /tasks executes through the current synchronous orchestration path.
- POST /tasks/queued durably enqueues a task and returns its queued state.
- GET /tasks/{task_id} returns a task only to its owning API principal.
- Worker primitives implement leases, retries, ownership checks, and dead-letter state in app/services/task_lifecycle.py.

A deployment must run a separately supervised worker process and inject an approved task handler before queued tasks are processed. The repository currently provides the queue and worker lifecycle library, not an always-on worker service or a configured cloud deployment. SQLite is for a single-instance MVP; use PostgreSQL before multi-instance workers.

## Authentication and administration

Set these only in a server-side secret manager:

- NEXUS_API_TOKEN: bearer token for agent discovery and task APIs.
- NEXUS_API_CLIENT_ID: stable server-configured principal ID for that token (default api-client).
- NEXUS_ADMIN_TOKEN: separate administrator bearer token.
- NEXUS_ADMIN_ID: server-configured reviewer identity.

The current API token model supports one configured API principal, not a multi-user token directory, token rotation service, or per-user account management. Protected routes fail closed when required secrets are missing.

## API

- GET /health
- GET /agents
- POST /tasks
- POST /tasks/queued
- GET /tasks/{task_id}
- POST /approvals/{approval_id}/decision (administrator only)
- GET /audit?limit=100 (administrator only; maximum 500)

## Known limitations and next gates

- ICT remains disabled until a reviewed handler, permission grants, schema tests, and deployment controls exist.
- No live web research, market-data integration, MT5, broker credentials, order execution, or position management.
- The worker lifecycle is implemented but no worker process is deployed or continuously supervised.
- No production multi-user identity provider, per-token hashing/rotation, rate limiting, OPA, Vault, Redis, Temporal, or pgvector.
- No cloud deployment or control-panel website has been provisioned.
- The system is not production-ready. Do not expose it publicly before deployment hardening and independent security review.

## Local development

```bash
pip install -r requirements.txt
pip install pytest
uvicorn app.main:app --reload
pytest -q
```
