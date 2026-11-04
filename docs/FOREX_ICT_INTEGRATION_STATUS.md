# Forex / ICT Mentor Integration Status

## Architecture decision

NEXUS AI CORE is the only runtime authority. Forex/ICT Mentor is a specialist capability, not a second autonomous platform. The central Orchestrator, SpecialistRuntime, PermissionService, Registry, storage, API authentication, audit trail, and task lifecycle remain core-owned.

## Integrated on this branch

- ICT Mentor handler is injected into the central SpecialistRuntime.
- Typed ICT tasks are routed through the central Orchestrator; unknown, disabled, ambiguous, or unauthorized capabilities fail closed and never fall back to the generic agent pipeline.
- ICT Mentor is registered as advisory-only for five capabilities: education, source lookup, chart analysis, strategy formalization, and trade review.
- Only three read-oriented permissions are granted to this specialist: knowledge.retrieve, user_input.read, and chart_attachment.read. Core policy and manifest grant are both required.
- Specialist output is validated against the strict central Pydantic contract. execution_result is structurally null; source claims must match central retrieval provenance; user rules must be explicitly confirmed.
- Knowledge source ingestion is administrator-only. Search is authenticated and returns source ID, title, canonical URL, retrieval time, segment ID, and timestamp bounds.
- Knowledge retrieval is deterministic indexed lexical search with Persian/Arabic Unicode normalization. It is not vector/semantic search and does not automatically crawl external sources.
- Audit events record specialist invocation start, completion, failure, and permission denial.

## Explicitly not enabled

- ict.position_monitoring
- ict.position_management
- ict.autonomous_execution
- MT5 or broker connectivity, broker credentials, account/position access, order submission/cancellation, or live trading.
- Specialist-controlled changes to permissions, risk policy, approvals, or execution.

## Forex research capabilities ported as libraries

The deterministic OHLC backtesting engine, trade-ledger evaluator, CSV market-data validator, strategy lifecycle evidence gates, and their source schemas/tests/docs have been selectively copied into the integration branch. They are now available as core libraries, and a bounded authenticated research-only backtest endpoint (`POST /research/backtests/run`) has been added. The endpoint accepts explicit OHLC candles and trade intents, calculates a trade ledger and evaluation metrics, optionally applies acceptance criteria, and records an audit summary. Durable dataset storage, reusable dataset APIs, immutable strategy/experiment persistence, and lifecycle transition APIs still require integration and tests. The Forex branch's overlapping API, authentication, storage, and orchestration infrastructure was deliberately not copied wholesale.

Backtesting remains research-only. It uses explicit trade intents and midpoint OHLC candles; it is not a broker-grade execution simulator. It does not prove live profitability or authorize trading.

## Validation gates before merge

1. CI green on the exact PR head, including unit tests, API security tests, database checks, and container build.
2. Review all changed API routes and strict input schemas.
3. Test SQLite and PostgreSQL schema behavior for knowledge tables.
4. Confirm no generic-pipeline fallback for typed specialist tasks.
5. Confirm all specialist paths remain advisory-only and execution_result is null.
6. Resolve review comments and confirm GitHub reports the PR mergeable.
7. Merge only after these gates pass.

## Operational gaps

- Queue/lease and injectable worker lifecycle primitives exist, but no standalone worker entrypoint, approved production task handler, or supervised worker service is configured.
- No cloud deployment is configured.
- No production OIDC identity provider, distributed rate limiter, secret manager, or token rotation service is provisioned.
- No approved ICT source corpus has been populated as part of this integration.
- No MT5 Demo bridge is installed. No live trading is enabled.
