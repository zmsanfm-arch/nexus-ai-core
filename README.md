# NEXUS AI CORE

NEXUS AI CORE is a cloud-oriented multi-agent system under active MVP development.

## Central foundation

- FastAPI service, manifest-driven specialist registry, and sequential Research → Analysis → Auditor pipeline for untyped tasks.
- Strict Pydantic contracts, bounded JSON inputs, and server-side model configuration.
- SQLAlchemy persistence for tasks, approvals, audit events, and durable task queue leases.
- Authenticated task submission and principal-scoped task reads.
- Admin-only approvals, audit access, knowledge-source ingestion, and aggregate queue observability.
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
- Worker lifecycle includes a standalone `python -m app.worker_entrypoint` process and an opt-in supervised Compose service (`--profile worker`). The generic worker only accepts `general` tasks; unregistered specialist and execution task types fail closed. The service requires an explicitly approved and configured model provider.
- Non-pass or missing auditor verdicts leave the business task blocked even when queue processing completes. Queue state is visible through admin-only `GET /admin/queue`, which returns aggregate counts only.
- Queue processing has bounded retries and dead-letter state. Active workers renew owner-checked leases while handlers run; a lost lease is audited and stale results are not committed. External dead-letter alert delivery, idempotency validation, and PostgreSQL multi-worker load/concurrency testing remain outstanding. SQLite is for a single-instance MVP; use PostgreSQL before multi-instance workers.

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
- `GET /admin/queue` (administrator only; aggregate counts only)
- `POST /knowledge/sources` (administrator only)
- `GET /knowledge/search` (authenticated)
- `POST /research/backtests/run` (authenticated; research-only)

## Deployment status and remaining gates

A controlled Railway deployment is online: the `nexus-api` service runs one replica, its latest deployment completed successfully, and `/ready` returned HTTP 200 against PostgreSQL after the dedicated Alembic release migration. The migration job logs confirm the PostgreSQL dialect and the API starts in fail-closed schema-verification mode. No public domain is attached; DNS/TLS and external firewall verification remain operator-owned and public exposure is not approved. CI run 430 passed on the PR #19 candidate, including Python 3.11/3.12 tests, PostgreSQL concurrency tests, container smoke test, dependency audit, Bandit, and encrypted PostgreSQL backup/restore drill on disposable CI databases. This does not constitute a production backup schedule or off-host restore test. Remaining gates include secret lifecycle/rotation evidence, OIDC or multi-user identity, distributed rate limiting, production load testing, active monitoring and alert delivery, production backup retention and restore drill, incident/rollback rehearsal, and independent security/recovery assessment. The worker remains opt-in and is not active by default. Trading and broker connectivity remain disabled.

## Local development

```bash
pip install -r requirements.txt
pip install pytest
uvicorn app.main:app --reload
pytest -q
```

## Strategy research and historical market data

- Strategy specifications are schema-validated and immutable; lifecycle transitions require deterministic evidence gates and are centrally audited.
- Research experiment plans are immutable and schema-validated.
- Historical OHLC CSV datasets are imported with strict bounds, timestamp/price validation, quality reporting, SHA-256 identity, and immutable storage. Dataset reads are paginated.
- Research and market-data APIs are authenticated; writes require the administrator role. Demo promotion remains disabled and no broker/live execution capability is introduced.

### APIs

- `POST /strategies/{strategy_id}/versions` and `GET /strategies/{strategy_id}/versions/{version}`
- `POST /strategies/{strategy_id}/versions/{version}/transitions` and `GET /strategies/{strategy_id}/versions/{version}/transitions`
- `POST /research/experiments` and `GET /research/experiments/{experiment_id}`
- `POST /market-data/datasets` (multipart CSV; maximum 5 MiB and 10,000 rows)
- `GET /market-data/datasets/{dataset_id}` and `GET /market-data/datasets/{dataset_id}/candles`

Market datasets are research inputs only. Backtest or lifecycle evidence cannot authorize demo or live trading.
