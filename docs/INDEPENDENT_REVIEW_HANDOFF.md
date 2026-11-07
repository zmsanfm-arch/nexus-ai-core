# NEXUS AI CORE — Independent Security & Recovery Review Handoff

**Review status:** Internal implementation and CI validation completed for the current release. Independent security and recovery assessment has not yet been performed. This document is evidence and scope for the evaluator; it is not a security certification or production launch approval.

## 1. Exact release under review

- Repository: `zmsanfm-arch/nexus-ai-core`
- Main commit: `111edb6fbae59ad1044b3252609304a11f7e49cf`
- Railway project: `02d83d3f-57ff-4123-abb6-00994d5d700d`
- Environment: `production`
- API service: `nexus-api`
- Latest successful deployment: `8057f6d0-c118-4af6-b045-311b401a1aa0`
- Deployment result: `SUCCESS`; one replica online.
- Database: Railway PostgreSQL, referenced through the service variable `DATABASE_URL`. No credential values are included here.
- Release migration: `python scripts/migrate_release.py`.
- Runtime migration policy: `NEXUS_MIGRATION_COMMAND=true`; `NEXUS_SKIP_MIGRATIONS=true`. The release job performs migrations explicitly; API startup verifies the exact Alembic head and fails closed if the schema is behind.
- Deployment evidence: logs show PostgreSQL dialect (`PostgresqlImpl`), migration job completion, application startup, and `GET /ready` returning HTTP 200.
- Public domain: none attached at the time of this record. DNS, TLS, and external firewall verification are operator-owned and must be completed before public exposure.

## 2. Automated evidence

CI run 443 passed on PR #25 candidate SHA `db9e023d8998d85ccf4cd79adf0fecb853cdad79`.

- 169 tests passed on Python 3.11.
- 169 tests passed on Python 3.12.
- PostgreSQL 16 concurrency coverage: 16 workers / 256 queue tasks.
- Docker image build and container health smoke test passed.
- Dependency audit and Bandit passed with no issues identified.
- Encrypted PostgreSQL backup/restore drill passed against disposable CI databases.
- Secret rotation utility tests verify distinct generated tokens, restrictive file permissions, no secret output, and no-overwrite behavior.
- Authenticated API and admin principal rate-limit tests verify 429 responses, Retry-After, separate budgets, and health/readiness exemptions.

**Important limitation:** the CI backup/restore drill is not evidence of a production backup schedule, off-host retention, production-key custody, or production restore RPO/RTO. The PostgreSQL concurrency test is not a production capacity benchmark.

## 3. Current security controls

- Separate API and administrator bearer tokens; production preflight rejects missing, weak, placeholder, or reused tokens.
- Constant-time token comparison in authentication.
- Separate authenticated-principal fixed-window limits: 600 API requests/minute and 300 admin requests/minute by default.
- `/health` and `/ready` are exempt from principal rate limits.
- The current API deployment is intentionally one replica. The limiter is process-local and must be replaced with a shared limiter before scaling horizontally.
- Invalid credentials are not throttled by the application middleware. Add trusted edge-level invalid-auth/request throttling before public exposure.
- Secret values are supplied through Railway variables and are not included in repository documentation or CI logs.
- Trading and broker connectivity remain disabled.

## 4. Required independent security assessment

The reviewer should independently validate, not merely inspect the claims above:

1. Authentication boundaries: unauthenticated, wrong-token, API-token, and admin-token access across every route; verify privilege separation and no accidental public admin route.
2. Rate limiting: API/admin thresholds, concurrent requests, Retry-After behavior, health/readiness exemptions, invalid-credential throttling at the edge, and behavior after process restart.
3. Secrets: entropy, separation, access control, log redaction, rotation, revocation, and rollback after a rotation failure.
4. Input and agent boundaries: prompt injection, tool authorization, SSRF, path traversal, unsafe URL/file handling, data exfiltration, and cross-agent privilege escalation.
5. Data handling: tenant/principal ownership, audit-log integrity, sensitive data retention, and database permissions.
6. API abuse and availability: request size limits, concurrency, queue exhaustion, denial-of-service controls, and failure behavior when PostgreSQL is unavailable.
7. Container and deployment: non-root execution, image contents, dependency/SBOM review, environment-variable exposure, network reachability, and rollback behavior.
8. Trading safety: confirm trading, broker credentials, and order execution remain disabled and cannot be enabled by an ordinary API request.

## 5. Required independent recovery assessment

1. Provision an off-host backup destination and define retention, encryption-key custody, and access policy.
2. Verify backup integrity and encryption without exposing the decryption identity.
3. Restore a production backup into an isolated PostgreSQL instance; never overwrite the live database for a drill.
4. Validate row counts, migration head, task/approval/audit records, and application-level invariants after restore.
5. Measure and record actual RPO and RTO; do not infer either from CI.
6. Test restore from a prior backup, key rotation, missing/corrupt backup, and interrupted restore.
7. Verify rollback to the previous application image and schema-compatible release.

## 6. Known residual gates

| Gate | Current state | Required action |
|---|---|---|
| DNS / TLS / external firewall | Operator-owned; no public domain attached | Configure and verify before public exposure |
| Production backup retention | Scripts and CI drill exist; no verified off-host production schedule | Select destination, key custody, retention, and schedule |
| Production restore | Not executed | Independent isolated restore drill and measured RPO/RTO |
| Monitoring / alerts | Railway resource metrics available; no external alert delivery verified | Configure alert endpoint and test delivery |
| Invalid-auth throttling | Not implemented at application edge | Add trusted edge control before public exposure |
| Horizontal scaling | One replica; limiter is process-local | Keep one replica or implement shared limiter first |
| Secret rotation | Script tested; live rotation/revocation not executed | Schedule controlled rotation with client update and rollback |
| Production load benchmark | CI concurrency test passed; no production capacity test | Run in isolated staging with agreed load profile |
| Independent assessment | Not performed | Evaluator to execute this handoff plan and record findings |

## 7. Reviewer output requested

The evaluator should return:
- findings classified by severity (Critical / High / Medium / Low / Informational),
- reproducible evidence and affected commit/deployment,
- remediation recommendations,
- pass/fail result for security and recovery,
- measured RPO/RTO,
- explicit approval or rejection for public production exposure.

Do not mark the project independently certified until this review is completed and all Critical/High findings are closed and retested.
