# Strategy Lifecycle and Promotion Gates

## State machine

`draft → candidate → backtested → oos_validated → demo_approved → demo_active`

Exceptional terminal or paused states:
- `suspended`: temporarily blocked by data quality, risk breach, broker mismatch, operational incident or review.
- `retired`: permanently withdrawn; retained for audit and comparison.

A transition is a NEXUS-governed decision, not an action the ICT Mentor can perform by itself.

## Required gates

| Transition | Minimum evidence / control |
|---|---|
| draft → candidate | Complete schema; deterministic rules; provenance; unresolved assumptions explicitly listed |
| candidate → backtested | Valid dataset; pinned engine/configuration; explicit cost model; reproducible run |
| backtested → oos_validated | Untouched holdout; walk-forward evaluation; sufficient sample; no critical data-quality issue |
| oos_validated → demo_approved | Acceptance criteria met; robustness review; central Risk Engine policy check; explicit NEXUS approval |
| demo_approved → demo_active | Demo account and symbol mapping verified centrally; execution permissions; operational monitoring and kill switch available |
| any active state → suspended | Risk limit breach, stale data, broker/account state mismatch, abnormal slippage, system integrity failure or manual central intervention |
| any non-retired state → retired | Explicit lifecycle decision with audit reason |

## Evaluation policy

The Strategy Evaluator should report, at minimum:
- trade count and sample coverage;
- win rate, gross/net profit, profit factor;
- expectancy in R and average R;
- maximum drawdown and drawdown duration;
- session, timeframe and directional breakdowns;
- spread and slippage sensitivity;
- parameter stability and walk-forward consistency;
- data-quality warnings and known simulation limitations.

No single metric determines acceptance. Thresholds must be declared in the experiment plan before the run. Thresholds supplied by the user, central policy and research defaults must remain distinguishable.

## Anti-overfitting controls

1. Separate train, validation and final holdout chronologically.
2. Do not use holdout results to choose parameters or rewrite rules.
3. Record every tested variant, including failed variants.
4. Use walk-forward folds where sample size permits.
5. Penalize excessive parameter sensitivity and strategy complexity.
6. Re-run finalists under stressed spread/slippage assumptions.
7. Report sample size and uncertainty; do not present a high win rate from a small sample as robust evidence.

## Demo controls (central NEXUS only)

Before automated Demo trading, central NEXUS must enforce:
- per-trade risk cap and position sizing;
- daily loss and maximum drawdown limits;
- maximum concurrent positions and daily trade count;
- permitted instruments, sessions and trading days;
- stale/missing market-data rejection;
- duplicate-order/idempotency protection;
- broker/account/position reconciliation;
- abnormal spread/slippage rejection;
- kill switch and automatic suspension;
- immutable order, decision and risk audit trail.

ICT Mentor cannot override, edit or bypass these controls. Backtest approval is not execution permission.

## Strategy changes and rollback

- Each revision increments the semantic version and records its parent version and rationale.
- A run pins an immutable strategy version and configuration hash.
- An active version is never edited in place.
- New variants must pass the same research and approval gates before promotion.
- Rollback means selecting a previously approved immutable version through NEXUS governance; it does not erase intervening audit history.

## Initial research profile (provisional)

XAUUSD is the first proposed instrument. H4/H1 context, M15 setup and M5 trigger are provisional research defaults only. They are not user-confirmed rules and must not be silently encoded as strategy truth. Session timezone, exact ICT entry criteria, stop/target rules, risk thresholds and acceptance thresholds remain unspecified until explicitly supplied or approved.
