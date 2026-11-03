# Web Platform Implementation Gap Register

**Assessment basis:** repository files inspected on 2026-11-04, including `app/main.py`, `app/storage.py`, `app/services/registry.py`, `app/services/orchestrator.py`, and `requirements.txt`.

This is a bounded code inspection, not a penetration test or production certification.

## Current backend baseline observed

- FastAPI application exposes `/health`, `/agents`, `/tasks`, `/tasks/{task_id}`, and approval decision routes.
- Approval decision endpoint uses a single server-configured bearer token and reviewer ID.
- Other listed read/task endpoints do not currently enforce general user authentication in the inspected API module.
- Registry is an in-memory hard-coded list of generic agents; it does not prove agent runtime health.
- SQLAlchemy persistence currently stores tasks, approvals and audit events.
- SQLite is the default database; PostgreSQL is configurable by environment variable.
- The current orchestration path submits one model request; it is not yet a complete specialist research/backtesting/trading pipeline.
- No web frontend, production identity provider, role/permission system, strategy repository, backtest persistence, market-data service or MT5 Demo connector was observed in the inspected files.

## Blocking gaps before public website exposure

| Priority | Gap | Required work |
|---|---|---|
| Critical | General API authentication absent on several routes | Add production identity/session middleware and protect every non-public endpoint |
| Critical | No resource/action-level RBAC | Add central authorization policies and tests |
| Critical | Single static admin bearer token is not a production identity system | Replace with managed identities, MFA for privileged roles, rotation and revocation |
| Critical | No CSRF/CORS/rate-limit policy defined in runtime | Add deployment-specific security middleware and tests |
| Critical | No production secret manager integration | Keep secrets server-side and rotate credentials |
| High | SQLite default is single-instance MVP storage | Provision managed PostgreSQL, migrations, backup and restore tests |
| High | Audit table is application-writable | Restrict mutation paths and define append-only/tamper-evidence and retention controls |
| High | Registry status is static | Separate declared capability from observed runtime health |
| High | No strategy/research/backtest persistence | Implement versioned entities, artifact storage and immutable run records |
| High | No market-data pipeline or MT5 Demo connector | Build central services with freshness and reconciliation controls |
| High | No observability/alerting contract | Add structured logs, metrics, traces and operational alerts |

## Required implementation sequence

1. Add automated API security tests that prove unauthenticated requests are rejected on every protected route.
2. Define a central identity adapter and resource/action authorization interface; do not bind the code to an unselected external provider.
3. Add CSRF, CORS, rate-limit, request-size and security-header controls with secure defaults.
4. Add database migrations and PostgreSQL deployment configuration; do not assume `create_all` is a migration strategy.
5. Harden audit records and add request/correlation IDs.
6. Implement strategy, experiment, backtest and evaluation persistence contracts.
7. Implement market-data services and deterministic Backtesting Engine.
8. Build the read-only web UI against real authenticated API responses.
9. Add Demo connector and risk-gated execution only after research and operational controls are verified.

## Explicit deployment inputs eventually required

Do not request or commit passwords, API keys, broker credentials or private tokens in chat or Git. At the deployment stage, obtain:
- chosen domain name and DNS control;
- hosting/cloud provider and region preference;
- identity provider choice (or approval to select a suitable managed provider);
- environment separation and backup/retention requirements;
- administrator account enrollment through a secure invite flow.

Until these are resolved, local development and repository-level implementation can continue, but public deployment must remain blocked.


## Persistence implementation update

- Alembic migration infrastructure is now present (`alembic.ini`, `migrations/env.py`, versioned revisions).
- The initial migration captures tasks, approvals and audit events; the next revision adds strategy versions, research records and environment-scoped trading records.
- Strategy versions are insert-only through the storage API. A duplicate `(strategy_id, version)` is rejected.
- Research record types are constrained to experiments, backtest runs, trades and evaluator results.
- Trading record types are constrained to risk events, Demo accounts, orders and positions. The storage API rejects the `live` environment.
- SQLite auto-creates schema for development/tests. PostgreSQL schema creation is migration-owned unless `NEXUS_AUTO_CREATE_SCHEMA=true` is explicitly set.
- Apply migrations with `alembic upgrade head` after configuring `DATABASE_URL`.

Remaining persistence work: replace generic JSON payload records with fully normalized domain tables and enforce append-only audit at the database permission/trigger layer; add repository-level pagination, filtering, retention and artifact storage. This baseline is not yet production-ready.


## Audit integrity update

- Migration `0004_audit_append_only` installs database triggers that reject UPDATE and DELETE on `audit_events` for SQLite and PostgreSQL.
- Audit history remains append-only through the database migration path. Production database credentials should still use a least-privilege application role and a separate migration role; trigger enforcement does not replace database access controls.


## Research runtime and ICT Mentor implementation update

- The central API now exposes immutable strategy-version registration/retrieval, experiment-plan registration/retrieval, and evidence-gated lifecycle history.
- Demo promotion (`oos_validated → demo_approved → demo_active`) is hard-disabled in code until a real central Risk Engine, approval verification, MT5 Demo connector, reconciliation, monitoring and kill switch are implemented and independently verified. Client-supplied booleans cannot enable it.
- ICT Mentor now has a NEXUS-hosted advisory runtime, schema validation, central model-router invocation, provenance checks against retrieved source IDs/segment IDs and metadata, and explicit user-rule validation. The central registry continues to report `specification` until production readiness gates pass.
- The knowledge store has immutable source IDs and segment metadata. Retrieval is currently lexical and loads the stored chunk set for ranking; this is a baseline, not scalable vector RAG.
- Backtesting currently supports explicit trade intents on midpoint OHLC bars, spread/slippage/commission, gap-through-stop/target handling, same-bar policy and a single open position. Entry-bar extremes are excluded to prevent look-ahead. Unclosed trades and overlapping intents fail closed.
- The evaluator reports ledger metrics and an acceptance decision. Missing expectancy-R or robustness evidence blocks acceptance; the current engine does not yet calculate expectancy-R because risk-per-trade/contract sizing semantics are not fully specified.
- Market data ingestion currently accepts strict timezone-aware OHLC CSVs. There is no live vendor feed, MT5 historical-data bridge, bid/ask tick archive, swap/financing model or broker-specific symbol specification.

## Remaining hard blockers before a usable hosted console or Demo

- Production identity provider/OIDC issuer, audience, group/role mapping and MFA policy are not configured. Static bearer tokens are a bootstrap baseline only.
- PostgreSQL service, credentials, backup/restore, migration execution and least-privilege DB roles have not been provisioned.
- A licensed/authorized ICT corpus has not been ingested; no transcript scraping or copyrighted bulk rehosting is permitted by this implementation.
- Historical XAUUSD datasets with verified broker/timezone/specification and bid/ask costs have not been supplied or connected.
- Full portfolio-level backtesting, walk-forward orchestration, out-of-sample evidence and production evaluator persistence are incomplete.
- MT5 Demo bridge, broker account reconciliation, central Risk Engine, Execution Gateway and operational kill switch do not exist yet. Live remains disabled.
- A Next.js mobile console and hosting/deployment have not been built. They must follow production identity and API hardening; no public endpoint should be exposed meanwhile.
