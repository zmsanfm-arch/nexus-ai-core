# ICT Mentor Integration Reconciliation — Current State

**Last reviewed: 2026-11-04.** This document supersedes the earlier pre-integration reconciliation snapshot.

## Current source of truth

NEXUS AI CORE owns authentication, identity, task lifecycle, orchestration, permission decisions, audit, approvals, risk, and deployment. ICT Mentor is integrated as an advisory-only specialist through the central Orchestrator and SpecialistRuntime on the stacked integration branch.

The current PR chain is:

1. PR #2 — central specialist contract and durable task lifecycle; base: `main`.
2. PR #3 — ICT Mentor integration through the central runtime; base: PR #2 branch.
3. PR #4 — evidence, approval/audit, and research-input hardening; base: PR #3 branch.
4. PR #5 — Alembic migrations and PostgreSQL validation; base: PR #4 branch.
5. PR #6 — hardened single-host deployment preparation and runbook; base: PR #5 branch.
6. PR #7 — indexed multilingual lexical knowledge retrieval; base: PR #6 branch.

All six PRs remain open Drafts in this review. They are stacked and must be reviewed/integrated in dependency order. A green CI run on each head does not mean the chain is merged or released. The default `main` branch remains the earlier MVP baseline until the PR chain is deliberately integrated.

## ICT Mentor contract and permissions

The integrated manifest registers ICT Mentor in advisory mode for exactly these capabilities:

- `ict.education`
- `ict.source_lookup`
- `ict.chart_analysis`
- `ict.strategy_formalization`
- `ict.trade_review`

The manifest declares only these read-oriented permissions:

- `knowledge.retrieve`
- `user_input.read`
- `chart_attachment.read`

Each invocation requires both the central permission policy and the specialist manifest grant. The handler uses the NEXUS-owned knowledge store, preserves source provenance, distinguishes user-confirmed rules from model inference, and validates the strict specialist result contract. Execution results remain structurally unavailable.

The following capabilities remain excluded:

- `ict.position_monitoring`
- `ict.position_management`
- `ict.autonomous_execution`
- MT5/broker connectivity, account/position access, order submission/cancellation, and live trading.

No broker credentials or trading account are required for this phase. Backtesting is research-only, uses midpoint OHLC and explicit trade intents, and is not a broker-grade execution simulator or trade authorization.

## Separate Forex branch — PR #1

PR #1 (`feature/ict-mentor-agent-foundation`) is a separate, divergent branch that overlaps central API, authentication, storage, orchestration, and CI files. GitHub currently reports it as non-mergeable, and no PR-triggered CI run was associated with its current head during this review.

Do not merge PR #1 wholesale, rebase it blindly, or change the central PR chain to depend on it. Any unique assets still needed from that branch must be reconciled selectively against the already integrated central implementation, with tests and review.

## Current validation snapshot

As of this review, exact-head CI runs for PRs #2 through #7 completed successfully:

- PR #2: Python test job passed.
- PRs #3–#7: Python 3.11 tests, Python 3.12 tests, and Docker build/container smoke checks passed.

This validation applies to the exact commit heads inspected on 2026-11-04. Any subsequent commit requires a fresh green run on its new SHA.

## Operational and release blockers

The repository is not approved for public production deployment. The following are still required:

- Complete review and deliberate integration of the stacked PR chain; reconcile PR #1 separately.
- A standalone worker entrypoint, approved task handler, supervised worker service, and operational queue/dead-letter monitoring before queued tasks are advertised as operational.
- A dedicated migration release step/lock before running multiple API/worker instances; current storage initialization applies migrations at startup.
- Production identity beyond one configured API principal/admin token, including OIDC or equivalent multi-user identity and credential lifecycle.
- Distributed rate limiting and abuse controls.
- Managed secrets storage, rotation, and emergency revocation.
- TLS reverse proxy, firewall and host hardening on an explicitly approved host.
- Automated encrypted database backups and a demonstrated restore drill.
- Database readiness, metrics, traces, alerting, log redaction, and incident ownership.
- Independent security review, threat-model review, dependency/container scanning, and release/rollback drills.

Knowledge retrieval is now indexed lexical with Persian/Arabic Unicode normalization; semantic/vector retrieval and external crawling are not implemented. Research dataset/experiment persistence remains incomplete.

## Release boundary

A green CI pipeline and a passing research evaluation do not authorize public exposure or trading. Do not provision paid hosting, merge the PR chain, connect a broker, enable MT5, or activate live trading as part of this workstream without the required separate authorization.