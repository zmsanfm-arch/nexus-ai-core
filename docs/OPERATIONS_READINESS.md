# NEXUS AI CORE — Operational Readiness & Deployment Runbook

**Status: NOT APPROVED FOR PUBLIC PRODUCTION.** This runbook prepares a controlled single-host deployment. It does not authorize public launch, paid hosting, external model-provider use, or trading connectivity.

## Current implementation facts

- FastAPI API, bearer-token authentication, administrator-only approval/audit routes, SQLAlchemy persistence, Alembic migrations, and PostgreSQL 16 CI coverage exist on the integration branch.
- ICT Mentor is advisory-only. Broker/MT5 connectivity, account/position access, order execution, and live trading must remain disabled.
- Durable queue storage/lease primitives, a standalone `python -m app.worker_entrypoint` process, an opt-in Compose worker service, and a generic advisory handler are provided. The worker rejects unregistered specialist/execution task types, preserves non-pass auditor verdicts as blocked tasks, uses bounded retries/dead-letter handling, and renews owner-checked leases while a task is running. Lease loss is audited and prevents the stale worker from committing a result. It requires an explicitly configured model provider and is not activated by the default Compose profile.
- Authentication is a single configured API principal/admin token model, not OIDC or multi-user identity.
- Model-provider transport rejects non-HTTPS remote URLs, embedded URL credentials, query strings/fragments, invalid ports, and non-finite/out-of-range timeouts; automatic redirects are disabled to prevent bearer-token forwarding.
- Knowledge retrieval is indexed lexical with Persian/Arabic Unicode normalization; semantic/vector retrieval and external crawling are not implemented.
- `/health` is process liveness only. `/ready` executes `SELECT 1` against the configured database and returns HTTP 503 when persistence is unavailable. Neither endpoint proves provider reachability or worker health. Admin-only `GET /admin/queue` reports aggregate queued/leased/completed/dead counts without exposing task payloads or failure details.
- Production Compose now runs Alembic as a one-shot `migrate` service before API startup. PostgreSQL migrations acquire a transaction-scoped advisory lock; API and worker startup use `NEXUS_SKIP_MIGRATIONS=true` and fail closed unless the database is already at the exact application migration head. Keep this release-job ordering in place for every deployment.
- Research backtests are not broker-grade and do not authorize trading.

## Deployment package

`docker-compose.production.yml` provides a hardened single-host starting point:
- PostgreSQL is private to the Compose network and persists in a named volume.
- API binds only to host loopback (`127.0.0.1:8000`) behind a separately configured TLS reverse proxy.
- API container runs non-root, read-only, drops Linux capabilities, and sets `no-new-privileges`.
- Docker image includes Alembic configuration and migration scripts.
- Production secrets are supplied through host-only `.env.production`; never commit it. The API startup preflight rejects missing, placeholder, weak, or reused API/admin tokens, non-PostgreSQL production storage, and startup without the dedicated migration-verification mode.

This is not a substitute for host hardening, firewall rules, TLS, backups, monitoring, and independent security review.

## Preflight — required before public exposure

1. Review and merge code changes in dependency order only after review and green CI: PR #2 → PR #3 → PR #4 → PR #5 → PR #6 → PR #7 → PR #9 → PR #10 → PR #11 → PR #12 → PR #13. PR #8's unique transport changes are reconciled by PR #13; do not merge PR #8's divergent branch wholesale. PR #1 is separate; do not merge wholesale. Reconcile its unique changes deliberately.
2. Confirm required CI checks on the exact merge candidate SHA. Run full tests and container build after assembling the final candidate.
3. Provision a supported Linux host, restrict inbound firewall access, patch the OS, configure SSH key-only access, and install Docker Engine/Compose. Do not expose port 8000 directly.
4. Configure the opt-in Caddy reverse proxy in `deploy/Caddyfile` after DNS A/AAAA records point to the host. Set `NEXUS_DOMAIN`, open inbound 80/443, validate certificate issuance, and start only the `public` Compose profile. The proxy enforces the configured host, 10 MB request body limit, HTTPS certificate automation, and security headers; API port 8000 remains loopback-only on the host.
5. Generate independent high-entropy API/admin secrets of at least 32 characters. Store them outside Git; establish rotation and emergency revocation. Do not reuse passwords or leave sample placeholders; production startup rejects these conditions.
6. Provision PostgreSQL with least-privilege credentials, encrypted storage, restricted network access, automated backups, retention, and a tested restore procedure.
7. Validate `.env.production` and run Compose config validation without printing secrets into logs or tickets.
8. Run the one-shot migration release job and verify its successful exit and Alembic head before starting the API. Compose enforces this dependency (`service_completed_successfully`); the API refuses to start against a missing or stale schema. Check liveness, database readiness, authenticated API access, admin route isolation, and persistence.
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
# Only after DNS/firewall/domain validation, expose the Caddy TLS proxy:
NEXUS_DOMAIN=api.example.com docker compose --env-file .env.production -f docker-compose.production.yml --profile public up -d proxy
# Only after model-provider approval/configuration, opt in to queued-task processing:
docker compose --env-file .env.production -f docker-compose.production.yml --profile worker up -d worker
docker compose --env-file .env.production -f docker-compose.production.yml ps
docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=100 api
```

Do not paste secrets into shell history, chat, GitHub issues, or logs. The sample file contains placeholders only.

## Backup, restore, secrets, and alert operations

### Encrypted PostgreSQL backup

The repository provides `scripts/backup_postgres_encrypted.sh`. Install PostgreSQL client tools and age on the trusted host, provide `DATABASE_URL`, and set `AGE_RECIPIENT` to the public age recipient. The script writes a mode-0600 encrypted custom-format dump and SHA-256 sidecar into a mode-0700 directory. Store copies off-host in an access-controlled location with provider-side encryption and retention. Do not store the age identity/private key beside the backups.

Example (run on the host; values are not to be pasted into chat or shell history):

```bash
export DATABASE_URL='postgresql://...'
export AGE_RECIPIENT='age1...'
BACKUP_DIR=/var/backups/nexus ./scripts/backup_postgres_encrypted.sh
```

### Isolated restore drill

Create a disposable PostgreSQL database whose name starts with `nexus_restore_`. Set `NEXUS_RESTORE_DATABASE_URL` to its connection URL and set `NEXUS_RESTORE_ALLOWED_DATABASE_URL` separately to the exact same URL after independently verifying the host and database are disposable. The script requires exact URL equality as well as the isolated database-name prefix; the prefix alone does not establish host isolation. It requires and verifies the SHA-256 sidecar before decryption and uses `pg_restore --exit-on-error`; a successful exit is necessary but not sufficient—also verify Alembic head, row counts, key API reads, audit continuity, and queue state. Never point this script at production.

```bash
BACKUP_FILE=/var/backups/nexus/nexus-YYYYMMDDTHHMMSSZ.dump.age \
AGE_IDENTITY_FILE=/secure/offline/backup-identity.txt \
NEXUS_RESTORE_DATABASE_URL='postgresql://.../nexus_restore_drill' \
NEXUS_RESTORE_ALLOWED_DATABASE_URL='postgresql://.../nexus_restore_drill' \
NEXUS_RESTORE_CONFIRM=YES ./scripts/restore_postgres_drill.sh
```

Record backup timestamp, checksum, source revision, DB version, restore target, duration, and verification evidence. Set and measure RPO/RTO before accepting production.

### API/admin secret rotation

Run `python scripts/rotate_api_secrets.py --output /secure/path/nexus-secrets-next.env` on the host. It creates a new file exclusively with mode 0600 and never prints token values. Transfer the new values into the approved secret manager, update the deployment environment, restart API/worker, verify authenticated API and admin access, then revoke the old tokens. This is a controlled replacement procedure, not zero-downtime dual-token rotation; plan a brief maintenance window. Keep old credentials available only for the rollback window in the secret manager, then destroy them. Never commit generated env files.

### Readiness and dead-letter alert delivery

`scripts/monitor_nexus.py` is a one-shot external monitor. Configure `NEXUS_READY_URL` (the `/ready` URL), `NEXUS_QUEUE_URL` (the admin `/admin/queue` URL), `NEXUS_ADMIN_TOKEN`, and `NEXUS_ALERT_WEBHOOK` in the scheduler's secret store. Optional `NEXUS_DEAD_TASK_ALERT_THRESHOLD` defaults to 1. Run it every minute from a trusted scheduler (systemd timer, cron, or managed monitor), with a timeout and failure alert on the scheduler itself. It checks database readiness and dead-letter count, sends a Slack-compatible webhook message, and never prints credentials. Configure deduplication/cooldown in the receiving alert platform to prevent repeated notifications. The monitor is not active until deployed and its webhook delivery is tested.

### PostgreSQL concurrency/load test

CI includes a PostgreSQL-only concurrent claim test using the service database and eight workers against a 48-task batch. It asserts each queued task is claimed exactly once. This is a correctness regression test, not a production capacity benchmark. Before scaling out, run a controlled staging load test at measured target concurrency and record throughput, p50/p95/p99 latency, connection pool saturation, lock waits, CPU, memory, and error rate. Increase load gradually and define stop thresholds before execution.

### Independent security review evidence

A developer self-review is not an independent assessment. Require a reviewer who did not implement this code to sign off on: threat model and trust boundaries; authentication/authorization and IDOR; brute-force and distributed rate limits; SSRF/URL validation; secret storage/rotation/revocation; dependency and container vulnerabilities; logging/PII leakage; migration/rollback safety; backup encryption and restore; TLS configuration and external exposure. Attach dated findings, severity, remediation PRs, retest evidence, and explicit residual-risk acceptance. Do not mark this gate complete from CI alone.

## Host, DNS, and TLS deployment gate

No host, domain, DNS record, certificate, or firewall change is performed by this repository PR. Once an operator provisions an approved host and domain, keep application port 8000 bound to loopback and expose only 80/443 at the reverse proxy. Validate DNS A/AAAA records, certificate chain and hostname, TLS 1.2/1.3, HTTP-to-HTTPS redirect, HSTS after validation, strict Host allow-list, request-size limits, and that direct public access to port 8000 and PostgreSQL is blocked. Record certificate expiry monitoring and renewal testing. A green Docker smoke test does not establish any of these facts.

## Rollback and recovery

- Keep the previous known-good image digest and application commit available.
- Before each schema migration, back up the database and verify restore to an isolated database.
- Prefer forward-only corrective migrations. Do not downgrade production schema unless tested against a restored copy.
- Roll back the application only if the prior image is schema-compatible; otherwise restore the matching database snapshot to an isolated recovery environment and follow the incident plan.
- Preserve audit records and incident evidence.

## Explicit go/no-go gates

**NO-GO until all are true:** reviewed/merged PR chain; exact-SHA CI green; independent security review complete; TLS/firewall verified; secrets stored and rotation tested; PostgreSQL backups/restores tested; migration procedure controlled; monitoring/alerts active; auth/rate limits validated; incident and rollback drills completed.

**Queued-task conditional GO:** the repository now includes a standalone generic advisory worker and a supervised Compose service behind the explicit `worker` profile. It remains opt-in because it sends task content to the configured model provider. Before enabling it, approve the provider/privacy terms, configure credentials, validate the exact-SHA CI and container image, and establish queue/dead-letter alerts. Administrators can inspect aggregate counts through `GET /admin/queue`; this endpoint is not a substitute for alert delivery. Only `general` tasks are supported; ICT specialist and all execution task types fail closed. Worker lease is 600 seconds by default; three sequential model calls have a maximum configured timeout budget of 360 seconds. Long-running worker leases are renewed while handlers run. Multi-instance worker scaling still requires PostgreSQL concurrency/load testing, idempotency validation, and dead-letter alert delivery.

**Additional NO-GO for scale-out:** OIDC or equivalent multi-user identity, distributed rate limiting, idempotency guarantees, dead-letter alerting/operations, and load/concurrency testing. The dedicated migration job and PostgreSQL advisory lock are implemented in the production Compose path, but still require deployment-level verification.

**Trading remains disabled.** This runbook does not enable live trading or broker connectivity.

## Outstanding work register

| Area | Status | Required action |
|---|---|---|
| PR chain / main integration | Open Draft PRs | Review dependency order; reconcile PR #1 separately |
| Production deployment | Not deployed; opt-in Caddy TLS proxy configuration prepared | Provision host/DNS/firewall, validate certificate issuance and external exposure only after explicit release approval |
| Secrets lifecycle | Startup rejects missing, placeholder, weak (<32 characters), or reused API/admin tokens | External secret manager, rotation, revocation, audit |
| Identity | Single API/admin token | OIDC, multi-user principals, scoped credentials |
| Rate limiting | No distributed limiter | Per-principal/IP limits and abuse protection |
| Worker | Standalone generic advisory entrypoint, opt-in supervised Compose service, bounded retries, dead-letter state, audit; specialist/execution task types rejected | Provider/privacy approval, queue/dead-letter alerts, idempotency and concurrency/load testing; PostgreSQL multi-worker load validation |
| Migrations | Dedicated one-shot Compose release job; PostgreSQL transaction advisory lock; API/worker verify exact schema head and skip implicit migration | Deployment-level migration/rollback drill and verification on the target host |
| Backups | Not provisioned | Automated encrypted backups and restore drills |
| Observability | Process liveness, database readiness (`/ready`), and admin-only aggregate queue counts | Metrics, traces, alerts/delivery, redacted logs, worker heartbeat |
| Knowledge search | Indexed lexical retrieval with Unicode normalization | Optional semantic backend if justified by corpus size/use case |
| Market/research data | No durable datasets/results | Versioned dataset and experiment persistence |
| Model-provider transport | HTTPS-only remote endpoints, strict URL validation, bounded finite timeouts, redirects disabled | Verify provider TLS/hostname policy and credentials handling during independent security review |
| Security assurance | CI only | Independent review, threat model, dependency/container scans |
| Trading | Disabled | Keep disabled; no broker/account/order connectivity |

## Release record template

Record release commit SHA, image digest, Alembic revision, test run URLs, reviewer, deployment operator, backup identifier, restore-test evidence, health-check result, and rollback image before marking a release complete.
