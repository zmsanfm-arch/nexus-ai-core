# ICT Mentor → NEXUS Strategy Research Handoff

**Contract status:** Proposed extension; not runtime-enabled.  
**Owner of execution:** NEXUS AI CORE.

## Purpose

Define how ICT Mentor contributes strategy research without acquiring orchestration, market-data, simulation, risk or execution authority.

## Proposed specialist task types

These task types are proposals for central routing. They must not be advertised as enabled until NEXUS implements and authorizes their routes.

- `ict.strategy_research`: formulate a falsifiable ICT-based strategy hypothesis and identify missing rule definitions.
- `ict.backtest_design`: produce or refine a machine-readable experiment plan; do not run the simulation.
- `ict.strategy_evaluation`: interpret a supplied, completed NEXUS backtest result and identify evidence, limitations and failure modes.
- `ict.strategy_revision`: propose a new immutable strategy version with a rationale; never mutate an approved or active version.

## Required inputs and outputs

- Strategy definitions conform to `docs/strategy-research/schemas/strategy.schema.json`.
- Experiment requests conform to `docs/strategy-research/schemas/experiment-plan.schema.json`.
- Simulation results supplied to the specialist conform to `docs/strategy-research/schemas/backtest-result.schema.json`.
- All source-backed ICT claims include provenance.
- Explicit user rules, documented ICT source claims and model inferences remain separate.
- Unknown entry, invalidation, stop, target, session or risk rules remain unresolved; the agent must not invent them.

## Central request flow

1. NEXUS authenticates the caller, authorizes the specialist task and supplies only permitted context.
2. ICT Mentor returns a strategy specification, experiment-plan proposal, evaluation commentary or revision proposal.
3. NEXUS validates the response and records provenance/audit metadata.
4. Only NEXUS may schedule a Backtesting Engine run against an approved dataset.
5. Only NEXUS Strategy Evaluator may issue a formal evaluation record.
6. Only central NEXUS governance and Risk Engine may approve Demo eligibility.
7. All Demo execution remains with the central Execution Gateway and MT5 Connector.

## Prohibited behavior

ICT Mentor must not:
- connect to MT5, a broker or a trading account;
- retrieve credentials, balances, live positions or order state directly;
- place, amend or cancel orders;
- launch compute or backtests outside NEXUS;
- claim that a proposed strategy is profitable or validated without a corresponding immutable run result;
- change central risk policy, approvals, permissions or lifecycle state;
- autonomously activate a strategy or modify an active version.

## Activation conditions

NEXUS must implement central task routing, schema validation, data access policy, experiment/run lifecycle, immutable result storage, evaluator policy and audit events before enabling these task types. Until then, these definitions are specification-only.
