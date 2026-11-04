# ICT Mentor Integration Reconciliation — Current State

**Last reviewed: 2026-11-04.** This document records the reconciled PR chain and current release boundary.

## Current source of truth

NEXUS AI CORE owns authentication, identity, task lifecycle, orchestration, permission decisions, audit, approvals, risk, and deployment. ICT Mentor is integrated as an advisory-only specialist through the central Orchestrator and SpecialistRuntime on the stacked integration branch.

The current PR chain is:

1. PR #2 — central specialist contract and durable task lifecycle; base: `main`.
2. PR #3 — ICT Mentor integration through the central runtime; base: PR #2 branch.
3. PR #4 — evidence, approval/audit, and research-input hardening; base: PR #3 branch.
4. PR #5 — Alembic migrations and PostgreSQL validation; base: PR #4 branch.
5. PR #6 — hardened single-host deployment preparation and runbook; base: PR #5 branch.
6. PR #7 — indexed multilingual lexical knowledge retrieval; base: PR #6 branch.
7. PR #9 — supervised worker runtime; base: PR #7 branch.
8. PR #10 — queue observability; base: PR #9 branch.
9. PR #11 — database readiness; base: PR #10 branch.
10. PR #12 — dedicated migration release; base: PR #11 branch.
11. PR #13 — reconciled model-provider transport; base: PR #12 branch.
12. PR #14 — encrypted backups, restore-drill tooling, secret rotation and alert readiness; base: PR #13 branch.
13. PR #15 — monitoring endpoint validation; base: PR #14 branch.
14. PR #1 — reconciled ICT foundation plus strategy research and market-data persistence; base: PR #15 branch.

PR #8 was closed as superseded by PR #13. PR #1 is no longer a divergent standalone branch: its head is a merge commit based on PR #15 and retains the original PR #1 history as a second parent. Its legacy direct ICT endpoint is not present in the reconciled tree.

PRs #2–#7, #9–#15, and #1 are open and marked Ready for review. All have green exact-head CI and GitHub currently reports them mergeable. None has been merged into `main`; the default branch is still the earlier baseline until the stack is reviewed and deliberately integrated.


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

## Reconciled Forex branch — PR #1

PR #1 (`feature/ict-mentor-agent-foundation`) has been reconciled as the final child of PR #15. Its current head is `a8d0c115cdf6859d2bc08212ceb91346fa260858`. The branch tree is based on PR #15's current head and preserves the original PR #1 history without reintroducing its direct ICT invocation route.

The reconciled PR adds the previously missing strategy-version, experiment, strategy-transition, and immutable historical market-dataset APIs. Writes require administrator authentication; reads require API authentication. Dataset imports are bounded and checksummed. The migration is chained after the current Alembic head. Demo promotion and execution remain disabled.


## Current validation snapshot

Exact-head CI for every open PR in the stack is green as of 2026-11-04:

- PRs #2–#7 and #9–#14: Python test jobs passed.
- PR #15: Python 3.11/3.12 tests and container build/health smoke passed.
- PR #1 at `a8d0c115cdf6859d2bc08212ceb91346fa260858`: Python 3.11/3.12 tests and container build/health smoke passed (CI run #344, `41889812168`).

PR #1's earlier run failed on an overlong Alembic revision identifier and stale migration-head assertions. Both were corrected; the latest exact-head run passed. GitHub currently reports all open stack PRs mergeable. A green CI run is not a security review or production release approval.


## Operational and release blockers

The repository is not approved for public production deployment. The following are still required:

- Complete independent review and deliberate integration of the stacked PR chain. PR #1 is now the final child of PR #15; PR #8 is closed as superseded.
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