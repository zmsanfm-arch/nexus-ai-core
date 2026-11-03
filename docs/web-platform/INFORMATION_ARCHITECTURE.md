# NEXUS Dashboard Information Architecture

## Global navigation

- Overview
- Agents
- ICT Mentor
- Strategies
- Research Lab
- Backtests
- Demo Trading
- Risk & Governance
- Activity & Audit
- Settings

A persistent environment indicator must show Research, Demo or (future) Live. Live must be visibly unavailable until explicitly released.

## Page requirements

### Overview
- API/service health and last update time.
- Agent availability and enabled state.
- Research pipeline counts: queued, running, completed, failed.
- Strategy lifecycle counts.
- Demo account summary only when a verified Demo connector is available.
- Active risk alerts and pending approvals.
- Recent audit activity.

### Agents
- Agent ID/name/version.
- Status: specification, disabled, enabled, degraded, unavailable.
- Capabilities and permission boundary.
- Last invocation and outcome.
- Link to agent-specific detail page.
- Never infer runtime health from a manifest alone.

### Strategy detail
- Strategy ID and immutable semantic version.
- Lifecycle status and promotion history.
- Instrument, market, session/timezone and timeframes.
- Human-readable entry/stop/target/invalidation rules.
- Provenance: ICT source claims, user-confirmed rules and model inferences in separate sections.
- Linked experiment runs and evaluation records.
- Parent version, revision rationale and audit history.

### Research Lab
- Experiment ID and strategy version.
- Dataset ID/version and date range.
- Train/validation/holdout partitions.
- Walk-forward configuration.
- Variants and parameter bounds.
- Cost assumptions and acceptance criteria.
- Run state, owner, timestamps and reproducibility hash.

### Backtest detail
- Run ID, immutable inputs and engine revision.
- Data quality status and warnings.
- Equity curve and drawdown curve.
- Trade ledger with entry, exit, direction, quantity, costs, P&L and R.
- Performance and risk metrics.
- Session, timeframe and direction breakdowns.
- Spread/slippage sensitivity and parameter stability.
- Explicit limitations and evaluator disposition.

### Demo Trading
- Clearly labeled Demo account and broker connection health.
- Balance/equity, open positions, pending orders and closed trades.
- Realized/unrealized P&L, daily loss and drawdown.
- Fill/slippage/spread metrics.
- Reconciliation timestamp and mismatch warnings.
- If connector is absent or stale, show unavailable/stale, never fabricated zeroes.

### Risk & Governance
- Effective policy version and limits.
- Pending approval records.
- Risk decisions and reasons.
- Kill-switch state.
- Suspended agents/strategies and reasons.
- All changes attributable to authenticated actor and timestamp.

## Common interaction patterns

- Search and filter by strategy, run, instrument, agent, status and time range.
- Drill down from overview metric to source records.
- Export authorized reports with audit record.
- Show empty, loading, error, stale and permission-denied states explicitly.
- Destructive or privileged actions require a reason and server-side authorization.
