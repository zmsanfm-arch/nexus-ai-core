# NEXUS AI CORE — Operational Readiness & Deployment Runbook

**Status: NOT APPROVED FOR PUBLIC PRODUCTION.** This runbook prepares a controlled deployment and records current evidence. It does not authorize public launch, external model-provider use, or trading connectivity.

## Evidence freshness — 2026-11-06

The dated deployment and CI entries below are historical snapshots and must not be interpreted as verification of the current main revision.

- Audited main SHA: `150503ea10a9bf693a1abc9b997773ef9d89cc4b`.
- The combined status on that exact SHA reports the Railway API deployment as successful. It does not report a complete GitHub Actions test/build/security matrix.
- GitHub Actions run [#744](https://github.com/zmsanfm-arch/nexus-ai-core/actions/runs/42196815895) for the audited main SHA failed before any job step ran; the job step lists are empty. This is a runner/service allocation failure pattern, not a test result.
- Audit remediation is isolated in draft [PR #38](https://github.com/zmsanfm-arch/nexus-ai-core/pull/38), head SHA `13dfd356bf13bd5c0c7f67ad34c7c85c17dd49e2`. It is not merged or deployed. Its workflow run [#752](https://github.com/zmsanfm-arch/nexus-ai-core/actions/runs/42197160533) also failed before any job step ran.
- Do not infer test success from deployment success or from historical CI runs on different SHAs. Before release, rerun the complete CI matrix on the exact candidate SHA and verify that each job actually executes and passes.

## Historical Railway deployment evidence (snapshot 2026-11-04)

- Main release commit: `6d3293b1b58be7a5a37f07de27dc6d212b2d3538`.
- Railway API deployment: `0bec6b64-f828-4615-8dfc-8f1fd9e5ead7`; state `SUCCESS`, one replica online.
- Railway API service: `nexus-api`; production environment has no public or custom domain attached. DNS/TLS and external firewall verification are operator-owned.
- The pre-deploy release command is `python scripts/migrate_release.py`. It requires a PostgreSQL `DATABASE_URL`, sets migration flags before importing the application store, runs Alembic explicitly, and performs a database round-trip check.
- Deployment logs confirm `PostgresqlImpl`, successful upgrades through the current migration chain, application startup, and `GET /ready` returning `200 OK`. API startup uses `NEXUS_SKIP_MIGRATIONS=true` and fails closed unless the database is at the exact migration head.
- CI run 438 passed on PR #23 candidate SHA `bb84faa3179edfb0abd73d077b14600b03d1c560`: Python 3.11 and 3.12 tests, PostgreSQL 16 queue concurrency tests (16 workers / 256 tasks), container build and health smoke test, dependency audit, Bandit, and encrypted PostgreSQL backup/restore drill against disposable CI databases. CI run 437 also passed after upgrading checkout/setup-python actions to Node 24-compatible releases.
- Authenticated API and administrator principals have separate in-process fixed-window limits: 600 API requests/minute and 300 admin requests/minute by default. `/health` and `/ready` are exempt. Railway is configured with one API replica; this limiter is not shared across replicas.
- PRs #1–#7 and #9–#23 are merged. PR #8 is closed as superseded. The current production deployment is the merged mainline, not an unmerged draft.
- Railway recorded earlier failed deployments while the migration release path was being corrected. The latest deployment is successful and has no active warning/critical notifications; historical failures remain visible in Railway's recent-failure window.
- CI restore evidence is not a production backup schedule, off-host retention, or production-host restore test. Do not claim production RPO/RTO until measured.

## Current implementation facts

- FastAPI API, bearer-token authentication, administrator-only approval/audit routes, SQLAlchemy persistence, Alembic migrations, and PostgreSQL 16 CI coverage exist in the mainline.
- ICT Mentor is advisory-only. Broker/MT5 connectivity, account/position access, order execution, and live trading must remain disabled.
- Durable queue storage/lease primitives, a standalone `python -m app.worker_entrypoint` process, an opt-in Compose worker service, and a generic advisory handler are provided. The worker rejects unregistered specialist/execution task types, preserves non-pass auditor verdicts as blocked tasks, uses bounded retries/dead-letter handling, and renews owner-checked leases while a task is running. Lease loss is audited and prevents the stale worker from committing a result. It requires an explicitly configured model provider and is not activated by the default Compose profile.
- Authentication is a single configured API principal/admin token model, not OIDC or multi-user identity.
- Model-provider transport rejects non-HTTPS remote URLs, embedded URL credentials, query strings/fragments, invalid ports, and non-finite/out-of-range timeouts; automatic redirects are disabled to prevent bearer-token forwarding.
- Knowledge retrieval is indexed lexical with Persian/Arabic Unicode normalization; semantic/vector retrieval and external crawling are not implemented.
- `/health` is process liveness only. `/ready` executes `SELECT 1` against the configured database and returns HTTP 503 when persistence is unavailable. Neither endpoint proves provider reachability or worker health. Admin-only `GET /admin/queue` reports aggregate queued/leased/completed/dead counts without exposing task payloads or failure details.
- Production Compose now runs Alembic as a one-shot `migrate` service before API startup. PostgreSQL migrations acquire a transaction-scoped advisory lock; API and worker startup use `NEXUS_SKIP_MIGRATIONS=true` and fail closed unless the database is already at the exact application migration head. Keep this release-job ordering in place for every deployment.
- Research backtests are not broker-grade and do not authorize trading.

## Deployment package

The active Railway deployment uses the Dockerfile and the one-shot `python scripts/migrate_release.py` release command. The API verifies the exact Alembic head on startup and is not permitted to perform implicit migrations. `docker-compose.production.yml` remains an alternative hardened single-host deployment package:
- PostgreSQL is private to the Compose network and persists in a named volume.
- API binds only to host loopback (`127.0.0.1:8000`) behind a separately configured TLS reverse proxy.
- API container runs non-root, read-only, drops Linux capabilities, and sets `no-new-privileges`.
- Docker image includes Alembic configuration and migration scripts.
- Production secrets are supplied through host-only `.env.production`; never commit it. The API startup preflight rejects missing, placeholder, weak, or reused API/admin tokens, non-PostgreSQL production storage, and startup without the dedicated migration-verification mode.

This is not a substitute for host hardening, firewall rules, TLS, backups, monitoring, and independent security review.

## Preflight — required before public exposure

1. The PR chain and release SHAs recorded in the dated sections below are historical snapshots. Verify the live main SHA and its exact-SHA CI evidence before every new release; as of 2026-11-06, main is `150503ea10a9bf693a1abc9b997773ef9d89cc4b` and its available combined status is deployment-only.
2. Confirm required CI checks on the exact merge candidate SHA. CI run 430 passed on PR #19 candidate SHA `8ac327151818324234ef1287de862e9dc6a7cb42`; the corresponding merge is deployed successfully. Continue to validate exact candidate SHAs for future changes.
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

The CI pipeline also performs an end-to-end drill against a disposable PostgreSQL service: it creates an age-encrypted dump, verifies the checksum, restores into an isolated `nexus_restore_*` database, and checks a known restored row. This validates the scripts in ephemeral CI; it does not replace a production-host restore drill, off-host retention, or measured RPO/RTO.

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
| PR chain / main integration | Merged through PR #19; PR #8 superseded | Keep future changes behind green CI and review |
| Production deployment | Railway API online; one replica; `/ready` returned 200 against PostgreSQL; no public domain | Operator to configure approved domain/TLS and verify external firewall/exposure; public launch remains NO-GO |
| Secrets lifecycle | Startup rejects missing, placeholder, weak (<32 characters), or reused API/admin tokens; rotation script now has mode/no-overwrite/no-leak tests | External secret manager, executed rotation/revocation drill, audit |
| Identity | Single API/admin token | OIDC, multi-user principals, scoped credentials |
| Rate limiting | Authenticated API/admin per-process limits (600/300 per minute); health/readiness exempt; one API replica | Edge-level invalid-auth throttling and shared limiter before multi-replica scaling |
| Worker | Standalone generic advisory entrypoint and opt-in supervised Compose service; CI PostgreSQL claim test covers 16 workers / 256 tasks | Provider/privacy approval, queue/dead-letter alerts, idempotency validation, and production capacity benchmark |
| Migrations | Railway one-shot `scripts/migrate_release.py` succeeded against PostgreSQL; API verifies exact schema head at startup | Complete deployment-level rollback drill and record release evidence |
| Backups | Encrypted backup/restore script and disposable PostgreSQL CI drill pass | Provision off-host production backups, retention, key custody, and measured production restore/RPO/RTO |
| Observability | `/health`, PostgreSQL-backed `/ready`, admin queue summary, Railway resource metrics; no active external alert delivery | Configure external uptime/latency/DB-capacity monitoring, webhook delivery, log retention/redaction, and worker heartbeat |
| Knowledge search | Indexed lexical retrieval with Unicode normalization | Optional semantic backend if justified by corpus size/use case |
| Market/research data | Immutable strategy versions, experiment plans, lifecycle history, and historical OHLC datasets are persisted; no broker-grade/live feed | Continue research validation; do not use backtests as execution authorization |
| Model-provider transport | HTTPS-only remote endpoints, strict URL validation, bounded finite timeouts, redirects disabled | Verify provider TLS/hostname policy and credentials handling during independent security review |
| Security assurance | CI dependency audit, Bandit, container smoke test, and code-level controls pass; no independent assessment | User-designated independent security/recovery review after internal completion; remediate and retest findings |
| Trading | Disabled | Keep disabled; no broker/account/order connectivity |

## Release record template

Record release commit SHA, image digest, Alembic revision, test run URLs, reviewer, deployment operator, backup identifier, restore-test evidence, health-check result, and rollback image before marking a release complete.
