# NEXUS AI CORE — Core Architecture Audit

**Audit date:** 2026-11-06  
**Audited base:** `main` at `150503ea10a9bf693a1abc9b997773ef9d89cc4b`  
**Scope:** Core platform outside Web Studio  
**Status:** Audit findings documented; F-01 and F-02 have candidate fixes and regression tests on the audit branch; candidate CI remains blocked by GitHub Actions runner allocation.  
**Explicit exclusions:** Web Studio and PR #35; public production exposure, DNS/TLS, external secrets, broker/live-trading connectivity; independent external security assessment.

## Executive summary

The repository contains a functioning advisory API, durable SQL-backed task and mission queues, lease-based workers, principal-scoped mission/artifact reads, model-provider transport controls, knowledge ingestion/search, research/backtesting routes, and deployment/backup tooling. Several architectural targets remain only partially implemented: multi-user identity, semantic retrieval, capability-based model routing, universal governance enforcement, parallel DAG scheduling, and a general intent/planning layer.

The most important concrete reliability finding is that the generic task worker persists task state and queue state in separate transactions. This can produce inconsistent state around lease expiry, process crashes, or worker takeover. An atomic lease-checked finalization transaction and regression tests have been added on the audit branch; the candidate has not yet completed CI.

The exact audited main SHA has a Railway API deployment status of success. The combined status available for that SHA does **not** show a GitHub Actions test/build/security matrix. Therefore, this audit does not claim that the exact main SHA has a green CI matrix.

## Subsystem status

| Subsystem | Observed implementation | Assessment |
|---|---|---|
| API intake/authentication | FastAPI bearer-token auth; one configured API principal and one admin identity | Implemented baseline; not multi-user/OIDC |
| Core orchestration | Fixed advisory Research → Analysis → Auditor pipeline; explicit task-type dispatch | Partial; no general intent classifier or generated planner |
| Agent framework | Strict JSON outputs; advisory-only agents; no direct tools/credentials | Implemented within a deliberately narrow boundary |
| Specialist registry/contracts | Manifest validation, strict Pydantic input/output, registered/disabled status | Implemented baseline; execution remains advisory |
| Model routing | One configured OpenAI-compatible provider/model; redirects disabled; TLS/local-only HTTP validation; bounded timeout | Transport controls present; no capability-based routing/fallback |
| Governance/permissions | Fixed sensitive-action approval types; capability permission checks in mission worker | Partial; not a universal policy gate across every dispatch path |
| Risk classification | Keyword-based classification | Baseline heuristic only; not a reliable authorization control |
| Knowledge/memory | Indexed lexical token overlap; Persian/Arabic normalization | Implemented lexical retrieval; no vector/semantic retrieval or automatic external crawl |
| Mission planning | Bounded declarative DAG; topological validation; maximum node/attempt constraints | Definition/validation implemented; execution is sequential |
| Mission queue/worker | SQL persistence, idempotency uniqueness, PostgreSQL row locking with SKIP LOCKED, owner-checked leases, heartbeats, durable node checkpoints | Substantial baseline; atomic audit/terminal-state gap remains |
| Generic task queue/worker | Durable SQL queue, lease renewal, bounded retries/dead-letter state, auditor verdict gate | Implemented baseline; atomic result/queue finalization defect is high priority |
| Artifacts | Principal-scoped local content-addressed files, atomic writes, size limits, integrity verification | Implemented; durability depends on persistent volume and backup policy |
| Research/backtesting | Research lifecycle and deterministic OHLC engine using explicit trade intents | Advisory/research only; not broker-grade or live execution |
| Storage/migrations | SQLAlchemy, Alembic, PostgreSQL production path, explicit release migration job | Implemented baseline; exact current migration/CI evidence still needs confirmation on candidate SHA |
| Operations/backup | Runbook, encrypted PostgreSQL backup/restore scripts, monitoring script | Tooling exists; production RPO/RTO and production-host restore evidence remain operator-owned |
| Observability | Audit events, health/readiness, aggregate queue summary | Partial; readiness checks DB, not provider or worker; audit writes are not universally transactional |

## Findings

### F-01 — HIGH: generic task result and queue completion are not atomic

**Evidence**
- `app/services/task_lifecycle.py`: the success path calls `save_task(task)` followed by `complete_queued_task(task_id, worker_id)`.
- The failure path calls `fail_queued_task(...)` followed by `save_task(task)`.
- `app/storage.py`: these operations commit independently.

**Impact**
A process failure or lease expiry/reclaim between the writes can leave task and queue records inconsistent. On success, task data may be written before the queue operation rejects a stale lease, allowing a later worker to reclaim and execute the task again.

**Required fix**
Add SQL transaction methods that lock the queue row, verify status=leased, matching owner, and unexpired lease, then persist task state and complete/requeue the queue row in the same transaction. Implement equivalent atomic semantics in InMemoryStore. Add tests for expired lease rejection, wrong owner, success atomicity, and failure atomicity.

**Status:** Candidate fix committed; awaiting CI verification.

### F-02 — MEDIUM: mission definition API reports inconsistent execution availability

**Evidence**
- `POST /missions` returns `execution_status: not_started` and `execution_available: true`.
- `GET /missions/{mission_id}` returns `execution_status: not_started` and `execution_available: false`.
- Actual enqueue is a separate `POST /missions/{mission_id}/runs` operation.

**Impact**
Clients receive contradictory capability metadata for the same persisted definition.

**Required fix**
Use one consistent response contract. Prefer an explicit field such as `run_submission_available: true` and retain `execution_status: not_started`; do not imply that creating a definition starts execution.

**Status:** Candidate fix and API regression test committed; awaiting CI verification.

### F-03 — MEDIUM: mission terminal status and final audit event are separate commits

**Evidence**
- `MissionRunWorker` calls `repository.finish(...)` before appending `mission_run_finished` to audit storage.
- These operations are not one transaction.

**Impact**
A crash or audit-storage error after terminal status commit can leave a completed/blocked run without its corresponding terminal audit event.

**Required fix**
If terminal audit is mandatory, persist it in the same database transaction as terminal state. Otherwise use a transactional outbox and retryable audit delivery. Define and test the invariant.

**Status:** Candidate fix committed: terminal run state and its final audit event now share one SQL transaction; success and rollback regression tests added. CI verification pending.

### F-04 — MEDIUM: operational evidence in runbook is stale

**Evidence**
- `docs/OPERATIONS_READINESS.md` contains release SHAs and CI run references that do not match the audited main SHA.
- The combined status on audited SHA `150503ea10a9bf693a1abc9b997773ef9d89cc4b` exposes a Railway API deployment status only.

**Impact**
Operators may mistake historical or different-SHA evidence for current verification.

**Required fix**
Regenerate the release evidence section from the exact candidate SHA, link each workflow run to that SHA, and distinguish deployment status from test/build/security checks.

**Status:** Candidate runbook update committed: historical snapshots are labeled as such, and the exact current main SHA plus deployment-only status and blocked CI evidence are recorded. CI verification pending.

### F-05 — MEDIUM: governance is not a universal execution gate

**Evidence**
- `app/services/governance.py` recognizes a fixed set of sensitive action labels.
- `app/services/risk.py` uses keyword matching.
- Mission execution checks capability permissions, but general task/specialist dispatch does not pass through one common policy decision interface.

**Impact**
The approval service is not proof that every operation is classified and gated. Current execution remains advisory-only, which materially limits immediate side-effect risk.

**Required fix**
Before adding any action-capable handlers, centralize policy evaluation at the execution boundary. Fail closed for unknown action classes and require exact-parameter approval binding.

**Status:** Architectural gap; no action-capable execution should be enabled until resolved.

### F-06 — LOW/MEDIUM: mission scheduling is sequential

**Evidence**
- Mission plan is topologically ordered and the worker iterates the ordered nodes sequentially.

**Impact**
Independent DAG branches do not execute concurrently. This is a throughput/latency limitation, not a correctness defect in the current sequential model.

**Required fix**
Only introduce parallel scheduling with bounded concurrency, dependency barriers, per-node lease/checkpoint semantics, and concurrency tests.

**Status:** Current behavior is explicit and safe but below a parallel-agent target.

## Confirmed controls

- Mission idempotency is enforced by a unique constraint on `(mission_id, principal_id, idempotency_key)`.
- PostgreSQL queue claiming uses `FOR UPDATE SKIP LOCKED`.
- Mission lease renewal, node checkpoint, and finish operations check current owner and unexpired lease.
- Completed mission-node checkpoints are immutable and can be resumed after lease expiry.
- Specialist output size is bounded; artifact access is principal-scoped and verifies content hash and size.
- Generic worker only accepts the generic advisory handler; unsupported specialist task types fail closed.
- Missing or non-pass auditor verdicts do not become an approved/completed business task.
- Model HTTP redirects are disabled; provider URL, timeout, and credentials are validated.
- Backtesting consumes explicit trade intents and does not connect to a broker or execute live trades.

## Verification evidence and limitations

- Audited `main` SHA: `150503ea10a9bf693a1abc9b997773ef9d89cc4b`.
- Combined commit status: Railway API deployment success only; no GitHub Actions matrix evidence was returned for this exact SHA.
- CI workflow defines Python 3.11/3.12 tests, PostgreSQL-backed tests, encrypted backup/restore drill, container smoke test, dependency audit, Bandit, and a browser-fixture job. The existence of these workflow jobs is not evidence that they passed on the audited SHA.
- PR #35 is Web Studio and excluded.
- PR #26 is the independent security/recovery handoff and excluded from this implementation audit.
- Candidate source changes for F-01 and F-02 are committed on the audit branch; they are not merged and are not CI-verified. F-03 and F-04 have candidate fixes/documentation committed; all candidate changes await CI verification.
- Independent security review remains a separate final handoff gate.

## Remediation order

1. F-05: document and enforce universal policy boundary before enabling action-capable handlers.
2. F-06: keep sequential execution until a separately scoped bounded-concurrency design is validated.
3. Run the complete CI matrix on the exact PR head SHA once GitHub runner allocation is restored.

## Acceptance checklist

- [x] F-01 candidate fix and PostgreSQL/in-memory regression tests committed; CI verification pending.
- [x] F-02 candidate fix and API contract regression test committed; CI verification pending.
- [x] F-03 candidate fix and transaction rollback/success regression tests committed; CI verification pending.
- [x] F-04 candidate runbook update committed with exact-SHA evidence; CI verification pending.
- [ ] All in-scope modules have source/test-backed status.
- [ ] Candidate CI is green on the exact candidate SHA.
- [x] No Web Studio files changed in the PR diff.
- [ ] External independent security assessment remains scheduled for final handoff.
