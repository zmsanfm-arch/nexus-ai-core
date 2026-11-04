# NEXUS Strategy Research & Backtesting Layer

**Status:** Architecture specification  
**Version:** 0.1.0  
**Execution status:** Not implemented; this document defines contracts only.

## Purpose

Define a reproducible research lifecycle for ICT-derived trading strategies, from a machine-readable hypothesis through historical simulation, out-of-sample validation and controlled Demo eligibility.

This layer is governed and orchestrated by NEXUS AI CORE. It does not introduce another orchestrator, task manager, risk engine, approval system or execution gateway.

## Ownership boundaries

| Concern | Owner |
|---|---|
| User request, routing, identity, permissions, approvals, audit and lifecycle orchestration | NEXUS AI CORE |
| ICT concepts, evidence-backed interpretation, strategy hypothesis and formalization | ICT Mentor |
| Historical data acquisition, normalization and quality metadata | NEXUS market-data services |
| Deterministic simulation and trade/equity generation | Backtesting Engine under NEXUS |
| Statistical validation, robustness checks and candidate ranking | Strategy Evaluator under NEXUS |
| Risk limits, Demo eligibility gate and kill switch | Central NEXUS Risk Engine |
| Broker/MT5 connectivity and order execution | Central NEXUS Execution Gateway / MT5 Connector |

ICT Mentor may submit a strategy specification or request a backtest through the NEXUS contract. It must never run a simulation pretending to be the Backtesting Engine, access broker credentials, connect to MT5, or submit/modify/cancel orders.

## Research workflow

1. ICT Mentor records a hypothesis and emits a versioned Strategy Specification.
2. NEXUS validates the specification, permissions, provenance and completeness.
3. NEXUS creates an immutable experiment run with pinned data, costs, parameters and code/runtime versions.
4. Backtesting Engine runs deterministic historical simulation.
5. Strategy Evaluator assesses train, validation, holdout and walk-forward results, including robustness and overfitting risk.
6. NEXUS records the decision: reject, revise, retain as candidate, or request further validation.
7. Only a separately approved candidate can be considered by the central Demo risk gate.
8. Demo activation and all order execution remain outside ICT Mentor and under NEXUS governance.

## Core invariants

- No look-ahead, survivorship or data leakage between train/validation/test partitions.
- No tuning on the final holdout set.
- All timestamps are timezone-aware; session definitions include an IANA timezone and daylight-saving behavior.
- Costs are explicit: spread, commission, slippage and any applicable swap/financing.
- Missing, stale, inconsistent or insufficient data fails closed.
- Every run is reproducible from immutable input references and version identifiers.
- Strategy versions and run results are immutable; revisions create new versions.
- A model may propose variants, but cannot silently mutate an approved or active strategy.
- Historical performance is not a guarantee of future results.
- A successful backtest is not authorization to trade.

## Contract files

- `schemas/strategy.schema.json`: normalized strategy definition.
- `schemas/experiment-plan.schema.json`: experiment design and validation protocol.
- `schemas/backtest-result.schema.json`: reproducible simulation result envelope.
- `STRATEGY_LIFECYCLE.md`: states, promotion gates and safety controls.

## Current scope and non-goals

This release is specification-only. It does not implement a data feed, simulator, optimizer, evaluator, MT5 connector, Demo execution or live trading. No strategy is approved by virtue of these schemas. XAUUSD is a proposed initial research instrument, not a hard-coded limitation of the contract.


## Implemented research runtime foundation

- `app/market_data/csv_loader.py`: strict timezone-aware OHLC CSV ingestion, OHLC validation, chronological normalization, duplicate rejection and optional expected-interval gap counts.
- `app/backtesting/engine.py`: deterministic one-intent-at-a-time OHLC simulator with explicit spread, slippage, commission, gap-through-stop handling and configurable same-bar stop/target policy.
- `app/backtesting/evaluator.py`: ledger-derived win rate, profit factor, net PnL, average trade PnL, equity curve and max drawdown.
- These modules do not generate ICT signals, select entries or represent a broker feed. A strategy-specific signal adapter, bid/ask historical datasets, swap/financing, partial fills, portfolio concurrency and full walk-forward orchestration remain future work. The current simulator must not be treated as a complete production-grade backtester.


The evaluator now derives expectancy-R and average-R from each trade's net PnL divided by initial stop-distance risk. Until broker contract size, tick value, account currency conversion and lot specifications are loaded, this is a price-distance/quantity R proxy, not a verified account-currency risk measure. Do not use it to authorize execution sizing.
