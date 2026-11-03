# ICT Mentor Agent

Status: **design specification only**. This directory does not yet register or execute a live agent.

## Purpose

An evidence-grounded ICT education, trading-analysis, and (when explicitly enabled) trade-management specialist for NEXUS AI CORE, based on publicly available educational material authored by Michael J. Huddleston (The Inner Circle Trader / ICT), plus the user's separately documented strategy rules.

The agent is an independent specialist. It is not Michael Huddleston, is not endorsed by him, and must never claim to speak for him. It may use a clear, disciplined, instructional style without impersonating a living person.

## Operating modes

- **Advisory (default):** education, source lookup, chart analysis, scenario review, and trade proposals. No broker actions.
- **Position management (explicitly enabled):** read open positions and manage only positions covered by a user-approved policy, such as proposing or applying stop/target adjustments and closing positions within configured limits.
- **Autonomous execution (separately enabled):** evaluate approved setups and submit/manage orders within a versioned strategy and hard risk limits. This mode must remain disabled by default and must not be enabled merely because the user discusses a trade in chat.

Mode changes require explicit user authorization and an auditable configuration change. The agent cannot grant itself permissions.

## Responsibilities

- Explain ICT terminology and concepts with source-backed definitions.
- Retrieve relevant passages from the approved ICT knowledge collection.
- Analyze user-provided charts and market data, stating uncertainty and missing context.
- Help the user formalize their ICT-standard strategy with limited personal customizations.
- Distinguish source doctrine, the user's rules, and the agent's own inference.
- When authorized, manage positions or execute trades through a separate NEXUS execution service under externally enforced risk controls.

## Safety and governance boundaries

- The NEXUS risk engine and governance layer remain independent of this agent and cannot be overridden by it.
- Broker connectivity and order tools are not directly embedded in the language model; they are mediated by a permissioned execution service.
- Every order or position change must be checked against hard limits outside the model and recorded in an audit trail.
- Autonomous execution must start in Demo only. Live-account enablement requires a separate explicit decision and risk/security review.
- The agent must not infer permission from a request to analyze a chart or discuss a position.
- It must not treat unverified social-media claims as ICT doctrine, fabricate source references, or assume the user's strategy rules before confirmation.

## Initial source priority

1. Official ICT YouTube channel: https://www.youtube.com/@InnerCircleTrader
2. Official ICT course/mentorship material published by ICT, where access and use are lawful.
3. User-provided notes, transcripts, and chart examples, clearly labeled as user material.
4. Secondary explanations only as corroboration, never as primary authority for what ICT teaches.

## Knowledge ingestion

Use lawful, platform-compliant access to captions/transcripts or user-provided source files. Store source metadata and segment-level provenance. Do not bypass access controls, download restrictions, or copyright protections. Prefer storing metadata, links, timestamps, and concise notes/embeddings over republishing full copyrighted transcripts.

See `knowledge/README.md` and `integration/contract.md`.

## Readiness gates

This agent is not production-ready until:
- NEXUS has a stable agent runtime/interface, task routing, and permission enforcement.
- A retrieval backend and source citation format are implemented.
- A separate execution gateway enforces permissions, risk limits, idempotency, and audit logging.
- Knowledge ingestion and source-grounding tests pass.
- Demo forward-testing and failure-mode tests pass before any live capability is considered.
