# ICT Mentor Agent

Status: **advisory runtime foundation implemented; production activation pending**. NEXUS now exposes a central invocation route and validates structured specialist output. The agent remains specification-state until model configuration, approved source corpus and runtime operational checks are complete.

## Purpose
An evidence-grounded ICT education and trade-analysis specialist hosted by NEXUS AI CORE. It is not Michael J. Huddleston, is not endorsed by him, and must not claim to speak for him.

## Architecture boundary
ICT Mentor is invoked only through the NEXUS central orchestrator. It does not own an orchestrator, task manager, scheduler, permission system, audit service, risk engine, MT5 connector, broker adapter, or execution gateway. NEXUS owns these central services.

## Enabled capabilities
- ict.education
- ict.source_lookup
- ict.chart_analysis
- ict.strategy_formalization
- ict.trade_review

## Defined but disabled capabilities
- ict.position_monitoring
- ict.position_management
- ict.autonomous_execution

Only advisory mode is supported. No direct market/account/position access, order actions, broker credentials, or MT5 connectivity are granted. execution_result must remain null.

## Evidence policy
For ICT doctrine, cite retrieved source title, canonical URL, retrieval timestamp, and segment/timestamp. Without evidence, mark attribution unverified. Keep official source claims, explicitly user-confirmed strategy rules, and agent inferences separate. Never invent the user's rules.

## Source priority
1. Official ICT YouTube channel: https://www.youtube.com/@InnerCircleTrader
2. Official ICT material where access and use are lawful.
3. User-provided notes, transcripts, and chart examples, labeled as user material.
4. Secondary sources only as corroboration, not primary authority for ICT attribution.

## Contract and validation
- Input schema: schemas/input.schema.json
- Output schema: schemas/output.schema.json
- Examples: examples/contract_examples.json
- Tests: tests/test_contract.py

Install jsonschema>=4.21 and run from repository root:
python -m unittest discover -s agents/ict_mentor/tests -v

## Readiness
The advisory runtime adapter and central route are implemented. Knowledge retrieval currently uses a deterministic lexical baseline over ingested segments; embedding-based retrieval, production identity, operational monitoring, and an approved populated ICT corpus are still pending. The registry intentionally continues to report `specification` until these activation gates pass. Any future position/execution capability requires a separate NEXUS-led design, authorization, risk review, and release; it is not enabled by this specification.
