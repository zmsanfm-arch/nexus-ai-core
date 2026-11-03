from __future__ import annotations

import json
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfirmedUserRule(StrictModel):
    rule_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    status: Literal["user_confirmed"]


class RetrievedSource(StrictModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    segment_id: str = Field(min_length=1)
    published_at: str | None = None
    timestamp_start: str | None = None
    timestamp_end: str | None = None
    summary: str | None = None


class SpecialistInput(StrictModel):
    """Advisory request envelope compatible with ICT Mentor Contract v1."""
    task_id: str = Field(min_length=1, max_length=128)
    task_type: str = Field(min_length=1, max_length=128)
    mode: Literal["advisory"] = "advisory"
    request: str = Field(min_length=1, max_length=8_000)
    context: dict[str, Any] = Field(default_factory=dict)
    chart: dict[str, Any] | None = None
    trade: dict[str, Any] | None = None
    user_rules: list[ConfirmedUserRule] = Field(default_factory=list)
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)
    correlation_id: str | None = Field(default=None, max_length=128)

    @field_validator("context", "chart", "trade", "user_rules", "retrieved_sources", mode="before")
    @classmethod
    def payloads_must_be_bounded_json(cls, value):
        if value is None:
            return value
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Specialist payload must contain JSON-compatible values.") from exc
        if len(encoded.encode("utf-8")) > 16_384:
            raise ValueError("Specialist payload exceeds the 16 KiB limit.")
        return value


class SourceClaim(StrictModel):
    claim: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    segment_id: str = Field(min_length=1)
    published_at: str | None = None
    timestamp_start: str | None = None
    timestamp_end: str | None = None


class UserRuleUsed(StrictModel):
    rule_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class AgentInference(StrictModel):
    inference: str = Field(min_length=1)
    basis: str = Field(min_length=1)
    confidence: Literal["low", "medium", "high"]


class ProposedAction(StrictModel):
    action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    requires_central_review: Literal[True] = True


class SpecialistResult(StrictModel):
    """Strict advisory output; execution_result is structurally forced to null."""
    agent_id: str = Field(min_length=1)
    mode: Literal["advisory"]
    answer: str
    source_claims: list[SourceClaim]
    user_rules_used: list[UserRuleUsed]
    agent_inferences: list[AgentInference]
    proposed_actions: list[ProposedAction]
    risk_decision: Literal[
        "not_requested",
        "not_assessed_by_specialist",
        "refer_to_central_risk_engine",
        "blocked_insufficient_information",
    ]
    execution_result: None
    uncertainties: list[str]


@runtime_checkable
class SpecialistAgent(Protocol):
    """A specialist exposes reasoning only; it receives no implicit tool access."""

    agent_id: str
    version: str
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]

    def run(self, request: SpecialistInput) -> SpecialistResult:
        """Return a validated advisory result. Execution is outside this interface."""
        ...
