# ICT Mentor Change Log — 2026-11-04

- Replaced permissive modes with advisory-only operation.
- Declared five active task types and three defined-but-disabled future task types.
- Removed direct market, account, position, order, MT5, and broker permissions.
- Added strict input/output JSON Schemas; execution_result is null in this release.
- Added education, chart-analysis, and trade-review examples without invented citations or user rules.
- Added positive and negative schema-validation tests.
- Clarified NEXUS ownership of orchestration, authorization, audit, risk engine, and execution gateway.

Files updated/added: agent.yaml; schemas/input.schema.json; schemas/output.schema.json; examples/contract_examples.json; tests/test_contract.py; integration/SPECIALIST_CONTRACT_V1.md; CAPABILITIES_AND_PERMISSIONS.md; CHANGELOG_2026-11-04.md.

No main changes, merge, rebase, runtime registration, broker integration, or live-trading permission were performed.
