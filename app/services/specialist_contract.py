from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpecialistInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1, max_length=128)
    task_type: str = Field(min_length=1, max_length=128)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("context")
    @classmethod
    def context_must_be_bounded_json(cls, value):
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Specialist context must contain JSON-compatible values.") from exc
        if len(encoded.encode("utf-8")) > 16_384:
            raise ValueError("Specialist context exceeds the 16 KiB limit.")
        return value


class SourceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    locator: str | None = None


class SpecialistResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: str = Field(min_length=1)
    mode: str = Field(pattern=r"^(advisory|disabled)$")
    answer: str
    source_claims: list[SourceClaim] = Field(default_factory=list)
    user_rules_used: list[str] = Field(default_factory=list)
    agent_inferences: list[str] = Field(default_factory=list)
    proposed_actions: list[str] = Field(default_factory=list)
    risk_decision: str = "not_assessed"
    execution_result: None = None
    uncertainties: list[str] = Field(default_factory=list)


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
