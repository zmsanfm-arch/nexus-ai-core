# ICT Mentor: Three-Level Learning Architecture

## Status and scope

This document defines the target product and runtime contract for the ICT Mentor specialist in NEXUS AI CORE. It is an architecture specification, not a claim that every capability described here is already implemented or enabled.

ICT Mentor remains a specialist dispatched by the central NEXUS Orchestrator. It does not own a parallel orchestrator, task manager, permission system, risk engine, execution gateway, or audit system. It operates in advisory-only mode.

## Product model

ICT Mentor has three cooperating levels:

1. **Teacher** — teaches ICT concepts and methods.
2. **Analyst** — analyses supplied market information, charts, and datasets.
3. **Mentor** — measures the learner's progress over time, identifies demonstrated weaknesses, and adapts the next learning activities to observed performance.

The Mentor level is the differentiator. Without longitudinal assessment and adaptation, the product is only a domain-specific chatbot.

## Responsibilities and boundaries

### Teacher

- Deliver structured lessons from prerequisite concepts to advanced material.
- Explain terminology, market structure, liquidity, displacement, dealing ranges, sessions, and other ICT topics.
- Generate examples, guided exercises, quizzes, and retrieval-practice prompts.
- Explain mistakes with references to the relevant learning objective.
- Record lesson and assessment outcomes as evidence events; it must not independently decide a user's long-term mastery.

### Analyst

- Analyse only the chart, market data, and context supplied or explicitly retrieved through authorized NEXUS capabilities.
- Separate observed facts, interpretation, assumptions, alternative scenarios, and uncertainty.
- Identify structure, liquidity areas, possible setups, invalidation conditions, and uncertainty.
- When formalizing a strategy, specify testable rules such as context, setup, trigger, entry, stop, target, invalidation, and risk/reward.
- Keep backtesting and strategy research separate from trade authorization. A research result is not permission to trade.

### Mentor

- Maintain a longitudinal learner model from attributable evidence, not conversational impressions.
- Track mastery by learning objective and skill, including confidence and evidence freshness.
- Detect recurring error patterns and prerequisite gaps.
- Distinguish knowledge gaps from execution/process errors and insufficient evidence.
- Select the next lesson, exercise, review, or assessment based on the learner model.
- Reassess after the intervention and update the learner model.
- Explain why a learning activity was selected and what evidence would demonstrate improvement.

## Learning loop

The Mentor runs a closed learning loop:

1. **Observe:** collect completed lessons, quiz answers, chart-analysis submissions, trade-review records, and user-confirmed practice outcomes.
2. **Normalize:** map each item to versioned learning objectives and skill dimensions.
3. **Evaluate:** score correctness, reasoning quality, consistency, and independence using explicit rubrics.
4. **Diagnose:** identify the strongest supported knowledge gap or process weakness; preserve uncertainty where evidence is sparse.
5. **Plan:** choose a bounded next intervention (teach, demonstrate, guided practice, independent practice, or reassessment).
6. **Deliver:** delegate the content task to Teacher or the analytical task to Analyst through central NEXUS dispatch.
7. **Verify:** assess the new attempt against the same rubric and compare it with the prior evidence.
8. **Adapt:** update mastery estimates and the next learning plan. Do not mark mastery from a single lucky or unverified answer.

## Learner model

The learner model is a versioned, user-scoped record. At minimum it should contain:

- Stable learner identifier and model version.
- Learning objectives and skill taxonomy version.
- Per-objective mastery state: not_assessed, emerging, developing, proficient, or needs_review.
- Evidence references, timestamps, source type, rubric version, and assessor.
- Accuracy and reasoning-quality trends, attempt count, and confidence.
- Recurring misconceptions and prerequisite dependencies.
- Current learning plan, selected intervention, rationale, and reassessment condition.
- Explicit user corrections and disputed assessments.

Do not store raw broker credentials, account secrets, or unnecessary personal data in the learner model. Store references to evidence where possible rather than duplicating sensitive payloads.

## Assessment principles

- Every assessment must map to one or more explicit learning objectives.
- Rubrics must be deterministic where possible and versioned when changed.
- Separate factual correctness from quality of reasoning and process discipline.
- Record provenance: user submission, imported dataset, chart attachment, or system-generated exercise.
- Do not infer a user's skill from time spent chatting, confidence of tone, or unsupported self-report alone.
- Mark evidence as insufficient when the sample is too small, stale, contradictory, or unverifiable.
- Allow the learner to inspect and challenge a diagnosis; preserve the original evidence and append the correction as a new audited event.
- Progress scores are educational indicators, not predictions of profitability or guarantees of trading performance.

## Suggested capability contract

The specialist can expose these logical capabilities through the existing central registry and permission policy:

- ict.education — Teacher lesson and exercise delivery.
- ict.source_lookup — authorized source research with provenance.
- ict.chart_analysis — Analyst chart and market-data analysis.
- ict.strategy_formalization — convert a hypothesis into explicit, testable rules.
- ict.trade_review — review user-provided trade records for process and rule adherence.
- ict.learning_assessment — assess a submitted answer or analysis against a rubric.
- ict.progress_review — summarize longitudinal progress and supported skill gaps.
- ict.learning_plan — produce and revise the next learning plan from the learner model.

These are capability names for the target contract. They are not permission grants. Every invocation remains subject to central authorization; manifests must not grant permissions merely because a capability is declared.

## Event and data flow

Use append-only evidence and assessment events as the source of truth. A materialized learner-model snapshot may be rebuilt from those events.

Suggested event types:

- lesson_completed
- exercise_submitted
- assessment_scored
- chart_analysis_submitted
- trade_review_recorded
- learning_gap_identified
- learning_intervention_assigned
- reassessment_completed
- learner_assessment_disputed

Each event should include an event ID, learner scope, objective IDs, source/evidence reference, timestamp, rubric or taxonomy version, actor, and correlation/mission ID. Enforce tenant/user isolation and central audit requirements.

## Routing and orchestration

NEXUS Core remains the only orchestration authority:

- Core receives the user request and creates/manages the mission.
- Core routes to Teacher, Analyst, or Mentor capability as appropriate.
- Mentor may request Teacher or Analyst work only through central dispatch; it cannot spawn an independent orchestration tree.
- Storage, identity, authorization, audit, and risk controls remain central services.
- All outputs remain advisory. No MT5, broker, account, order, position-management, or live-execution access is introduced by this design.

## Acceptance criteria

The three-level model is not complete until tests demonstrate all of the following:

1. Teacher can deliver an objective-linked lesson and assessment.
2. Analyst distinguishes observations, assumptions, scenarios, and invalidation conditions.
3. Mentor can build a learner profile from multiple evidence events across separate sessions.
4. Mentor identifies a repeated weakness only when supported by sufficient evidence and reports uncertainty otherwise.
5. Mentor selects a targeted next intervention and explains the evidence-based reason.
6. A subsequent assessment updates the learner model and demonstrates whether the intervention helped.
7. A learner can inspect and dispute an assessment without rewriting historical evidence.
8. Learner data is isolated by user/tenant and all material updates are auditable.
9. Core remains the sole orchestrator and all capability calls pass central authorization.
10. No educational or backtesting outcome can authorize demo or live trading.

## Delivery sequence

1. Add versioned objective taxonomy and assessment rubrics.
2. Add append-only learner evidence/event schemas and tenant-scoped persistence.
3. Add deterministic assessment and mastery aggregation service.
4. Add Mentor diagnosis and learning-plan generation with explicit evidence references.
5. Connect Teacher and Analyst outputs to the evidence pipeline through central dispatch.
6. Add integration tests for longitudinal progress, adaptation, disputes, isolation, and advisory-only boundaries.
7. Enable the new capabilities only after CI and policy tests pass on the exact commit.

Until these steps are implemented and validated, the three-level model is the approved target architecture, not a statement of production readiness.
