"""Strict contract for an independently supplied mission auditor."""
from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class MissionAuditResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: Literal["pass", "revise", "block"]
    summary: str = Field(min_length=1, max_length=4_000)
    findings: tuple[str, ...] = Field(default=(), max_length=32)
    limitations: tuple[str, ...] = Field(default=(), max_length=32)


class IndependentAuditor(Protocol):
    """Auditor is injected separately from mission node handlers."""

    def audit(self, *, mission, outputs: dict) -> MissionAuditResult | dict:
        """Return a strict verdict; never execute or authorize external actions."""
        ...
