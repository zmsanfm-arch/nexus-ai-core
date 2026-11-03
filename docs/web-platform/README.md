# NEXUS Web Platform

**Status:** Architecture specification; no deployed website is implied.  
**Target:** Secure, mobile-first operations console for NEXUS AI CORE.

## Product intent

The web platform is the human-facing control and observability surface for the NEXUS system. It provides a single place to inspect specialist agents, research runs, strategy versions, backtests, Demo trades, risk events, approvals and audit history.

It is not a second AI brain. It must not implement an independent orchestrator, strategy engine, risk engine or order execution path. All commands are authenticated requests to the central NEXUS API, which remains authoritative.

## System topology

```
Browser / Mobile Web
        |
        | HTTPS, authenticated session
        v
NEXUS Web UI (presentation + user interaction)
        |
        | versioned API; no direct database access
        v
NEXUS Core API (identity, orchestration, policy, audit)
        |
        +--> Specialist Runtime --> ICT Mentor / other agents
        +--> Market Data Services
        +--> Backtesting Engine
        +--> Strategy Evaluator
        +--> Central Risk Engine
        +--> Execution Gateway --> MT5 Connector (Demo first)
        |
        v
PostgreSQL + immutable artifacts/object storage + audit events
```

The browser never connects directly to MT5, a broker, model providers, database credentials or internal agent endpoints.

## Main application areas

1. **Overview:** system health, active agents, current environment, pending approvals, latest research runs, Demo equity and risk status.
2. **Agents:** registry, version, capability, enabled/disabled state, health, last activity and permitted actions.
3. **ICT Mentor:** source-backed knowledge, chart reviews, hypotheses, strategy specifications and unresolved assumptions.
4. **Strategies:** immutable versions, rules, instrument/session/timeframes, status, provenance, change history and promotion gates.
5. **Research Lab:** experiment plans, parameter variants, dataset versions, queued/running/completed runs and reproducibility metadata.
6. **Backtests:** equity curve, trade list, R-multiple distribution, win rate, profit factor, expectancy, drawdown, session/timeframe breakdowns and robustness warnings.
7. **Demo Trading:** positions, orders, fills, closed trades, balance/equity, daily P&L, exposure, execution quality and broker reconciliation. Read-only until explicit central controls are implemented.
8. **Risk & Governance:** policy limits, approval queue, kill-switch state, suspensions and policy decision history. Policy edits require privileged server-side authorization and audit.
9. **Activity & Audit:** chronological task, agent, research, risk, approval and execution events, with correlation IDs.
10. **Settings:** users/roles, environment configuration status, integrations and notification preferences. Secrets are never displayed.

## Environments

- Research: historical data and simulations only.
- Demo: broker-connected paper environment, isolated from live credentials.
- Live: not part of the initial release; disabled by default and requires a separate security, risk and governance release.

The UI must display the environment conspicuously on every trading-related screen. Demo and Live data must never be mixed.

## Interaction rules

- Read operations may be broadly available to authenticated roles according to least privilege.
- Mutating actions are explicit, server-authorized, validated and audited.
- No browser action can bypass central approval or Risk Engine policy.
- Every run, strategy version, order and event is traceable by stable ID and correlation ID.
- Show source provenance and distinguish verified facts, user rules, model inference and unknowns.
- Display data freshness and connection state; stale data is never represented as current.
- Mobile-first responsive layout; desktop may expose denser tables and multi-panel analysis.

## Recommended implementation path

1. Harden and version the existing FastAPI core API; add production identity, role-based access, audit coverage and PostgreSQL migrations.
2. Build a separate web client consuming only the public NEXUS API.
3. Add read-only overview, agent registry, strategy and research/backtest views.
4. Add Demo observability after the central MT5 Demo connector exists.
5. Add privileged governance actions only after security review, approval workflows and audit tests.
6. Keep Live trading disabled until a distinct release gate is passed.

## Initial UI technology recommendation

Use a separate TypeScript web client (Next.js/React) with a typed API client, server-side session handling and responsive component system. Keep the API as the source of truth. This is a proposed implementation choice, not an existing dependency in the repository.

## Non-goals for the first web release

- No direct browser-to-broker or browser-to-MT5 connection.
- No credentials or API keys in frontend bundles/local storage.
- No strategy auto-editing or autonomous promotion.
- No manual order-entry interface until central execution controls and authorization are fully implemented.
- No public registration or public dashboard exposure before production security review.
