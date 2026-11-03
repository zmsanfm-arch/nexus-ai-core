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
