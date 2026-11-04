# NEXUS AI CORE — Operational Readiness & Deployment Runbook

**Status: NOT APPROVED FOR PUBLIC PRODUCTION.** This runbook prepares a controlled single-host deployment. It does not authorize public launch, paid hosting, external model-provider use, or trading connectivity.

## Current implementation facts

- FastAPI API, bearer-token authentication, administrator-only approval/audit routes, SQLAlchemy persistence, Alembic migrations, and PostgreSQL 16 CI coverage exist on the integration branch.
- ICT Mentor is advisory-only. Broker/MT5 connectivity, account/position access, order execution, and live trading must remain disabled.
- Durable queue storage/lease primitives, a standalone `python -m app.worker_entrypoint` process, an opt-in Compose worker service, and a generic advisory handler are provided. The worker rejects unregistered specialist/execution task types, preserves non-pass auditor verdicts as blocked tasks, and uses bounded retries/dead-letter handling. It requires an explicitly configured model provider and is not activated by the default Compose profile.
- Authentication is a single configured API principal/admin token model, not OIDC or multi-user identity.
- Knowledge retrieval is indexed lexical with Persian/Arabic Unicode normalization; semantic/vector retrieval and external crawling are not implemented.
- `/health` is process liveness only. It does not prove database readiness, provider reachability, or worker health.
- Alembic migrations currently run during store initialization. Run exactly one API instance. Do not scale horizontally until migrations move to a dedicated release step with startup coordination.
- Research backtests are not broker-grade and do not authorize trading.

## Deployment package

`docker-compose.production.yml` provides a hardened single-host starting point:
- PostgreSQL is private to the Compose network and persists in a named volume.
- API binds only to host loopback (`127.0.0.1:8000`) behind a separately configured TLS reverse proxy.
- API container runs non-root, read-only, drops Linux capabilities, and sets `no-new-privileges`.
- Docker image includes Alembic configuration and migration scripts.
- Production secrets are supplied through host-only `.env.production`; never commit it.

This is not a substitute for host hardening, firewall rules, TLS, backups, monitoring, and independent security review.

## Preflight — required before public exposure

1. Review and merge code changes in dependency order only after review and green CI: PR #2 → PR #3 → PR #4 → PR #5 → PR #6 → PR #7. PR #1 is separate; do not merge wholesale. Reconcile its unique changes deliberately.
2. Confirm required CI checks on the exact merge candidate SHA. Run full tests and container build after assembling the final candidate.
3. Provision a supported Linux host, restrict inbound firewall access, patch the OS, configure SSH key-only access, and install Docker Engine/Compose. Do not expose port 8000 directly.
4. Configure TLS reverse proxy with valid certificates, strict host allow-list, request/body size limits, and forwarding headers trusted only from the local proxy.
5. Generate independent high-entropy API/admin secrets. Store them outside Git; establish rotation and emergency revocation. Do not reuse passwords.
6. Provision PostgreSQL with least-privilege credentials, encrypted storage, restricted network access, automated backups, retention, and a tested restore procedure.
7. Validate `.env.production` and run Compose config validation without printing secrets into logs or tickets.
8. Apply migrations once, verify Alembic revision, then start one API instance. Check liveness, authenticated API access, admin route isolation, and database persistence.
9. Establish uptime/error/latency monitoring, disk/database capacity alerts, log retention/redaction, incident ownership, and an on-call response path.
10. Complete independent security review, including brute-force controls, rate limiting, authorization boundaries, dependency/container scanning, secret leakage, and backup restoration.
11. Confirm privacy, legal, and provider terms before importing external knowledge or sending user data to a model provider.
12. Keep trading and broker capabilities disabled. No live account, broker API, MT5 terminal, order endpoint, or execution credential is permitted.

## Safe deployment commands

Run from the repository root on the target host after approval and provisioning:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
# Edit .env.production locally on the host; use unique generated secrets.
docker compose --env-file .env.production -f docker-compose.production.yml config --quiet
docker compose --env-file .env.production -f docker-compose.production.yml build
docker compose --env-file .env.production -f docker-compose.production.yml up -d
# Only after model-provider approval/configuration, opt in to queued-task processing:
docker compose --env-file .env.production -f docker-compose.production.yml --profile worker up -d worker
docker compose --env-file .env.production -f docker-compose.production.yml ps
docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=100 api
```

Do not paste secrets into shell history, chat, GitHub issues, or logs. The sample file contains placeholders only.

## Rollback and recovery

- Keep the previous known-good image digest and application commit available.
- Before each schema migration, back up the database and verify restore to an isolated database.
- Prefer forward-only corrective migrations. Do not downgrade production schema unless tested against a restored copy.
- Roll back the application only if the prior image is schema-compatible; otherwise restore the matching database snapshot to an isolated recovery environment and follow the incident plan.
- Preserve audit records and incident evidence.

## Explicit go/no-go gates

**NO-GO until all are true:** reviewed/merged PR chain; exact-SHA CI green; independent security review complete; TLS/firewall verified; secrets stored and rotation tested; PostgreSQL backups/restores tested; migration procedure controlled; monitoring/alerts active; auth/rate limits validated; incident and rollback drills completed.

**Queued-task conditional GO:** the repository now includes a standalone generic advisory worker and a supervised Compose service behind the explicit `worker` profile. It remains opt-in because it sends task content to the configured model provider. Before enabling it, approve the provider/privacy terms, configure credentials, validate the exact-SHA CI and container image, and establish queue/dead-letter alerts. Only `general` tasks are supported; ICT specialist and all execution task types fail closed. Worker lease is 600 seconds by default; three sequential model calls have a maximum configured timeout budget of 360 seconds. Long-running or multi-instance worker scaling still requires lease renewal/heartbeat and PostgreSQL concurrency/load testing.

**Additional NO-GO for scale-out:** dedicated migration job/lock, OIDC or equivalent multi-user identity, distributed rate limiting, supervised worker service, queue idempotency/dead-letter operations, and load/concurrency testing.

**Trading remains disabled.** This runbook does not enable live trading or broker connectivity.

## Outstanding work register

| Area | Status | Required action |
|---|---|---|
| PR chain / main integration | Open Draft PRs | Review dependency order; reconcile PR #1 separately |
| Production deployment | Not deployed | Provision host/TLS/firewall only after explicit release approval |
| Secrets lifecycle | Basic env configuration | Secret manager, rotation, revocation, audit |
| Identity | Single API/admin token | OIDC, multi-user principals, scoped credentials |
| Rate limiting | No distributed limiter | Per-principal/IP limits and abuse protection |
| Worker | Standalone generic advisory entrypoint, opt-in supervised Compose service, bounded retries, dead-letter state, audit; specialist/execution task types rejected | Provider/privacy approval, queue/dead-letter alerts, idempotency and concurrency/load testing; lease renewal before workloads can exceed the configured lease |
| Migrations | Alembic at startup | Dedicated migration job/lock before multi-instance use |
| Backups | Not provisioned | Automated encrypted backups and restore drills |
| Observability | Basic health endpoint | DB readiness, metrics, traces, alerts, redacted logs |
| Knowledge search | Indexed lexical retrieval with Unicode normalization | Optional semantic backend if justified by corpus size/use case |
| Market/research data | No durable datasets/results | Versioned dataset and experiment persistence |
| Security assurance | CI only | Independent review, threat model, dependency/container scans |
| Trading | Disabled | Keep disabled; no broker/account/order connectivity |

## Release record template

Record release commit SHA, image digest, Alembic revision, test run URLs, reviewer, deployment operator, backup identifier, restore-test evidence, health-check result, and rollback image before marking a release complete.
