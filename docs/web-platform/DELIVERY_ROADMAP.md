# NEXUS Web Platform Delivery Roadmap

## Phase 0 — foundation and truthfulness
- Confirm backend API and runtime boundaries.
- Define canonical IDs and contracts for agents, strategies, experiments, runs, trades, risk decisions and audit events.
- Ensure UI status labels distinguish specification, implemented, enabled, degraded and unavailable.
- Establish environment separation (research/demo/live).

## Phase 1 — secure read-only console
- Production authentication and role/permission checks.
- Responsive web shell and overview.
- Agent registry and agent detail.
- Strategy/version browser.
- Research experiment and backtest result views.
- Audit/activity timeline.
- No broker actions and no write controls beyond safe research request creation.

## Phase 2 — research workflow
- Strategy proposal submission through NEXUS.
- Experiment plan validation.
- Backtest job submission and status tracking.
- Results, artifacts and evaluation reports.
- Immutable versioning and approval workflow.

## Phase 3 — Demo observability
- Central MT5 Demo connector and account reconciliation.
- Read-only positions/orders/trades/equity dashboard.
- Data freshness and connection monitoring.
- Risk events, execution quality and kill-switch visibility.

## Phase 4 — controlled Demo operations
- Central Risk Engine and Execution Gateway production hardening.
- Explicit approval/authorization rules.
- Idempotent command handling and full audit.
- Bounded automated Demo execution with automatic suspension controls.
- UI only exposes operations supported by central APIs.

## Phase 5 — live environment (not scheduled)
A separate design, threat model, independent risk review, operational readiness review and explicit user/governance decision are required. Live mode stays disabled until then.

## Acceptance criteria for first usable release
- User can authenticate securely from mobile and desktop.
- Overview accurately reflects backend state and update timestamps.
- Agent pages never claim specification-only agents are running.
- Strategy and backtest records are traceable and reproducible.
- Audit timeline links actions to actors and correlation IDs.
- No secrets are exposed to the browser.
- No browser path can bypass central NEXUS authorization, risk or execution.
- Empty, stale, unavailable and unauthorized states are explicit.
