"""Controlled self-extension: generate validated, inert capability proposals.

This module creates declarative YAML artifacts only. It never writes to the
repository, installs packages, imports generated code, grants permissions, or
activates a capability. Approval and activation remain core-governed actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Literal
from typing import Any

import yaml
from pydantic import ValidationError

from app.services.capability_catalog import (
    CapabilityDefinitionError,
    SkillDefinition,
    ToolDefinition,
)
from app.services.plugin_registry import PluginManifest


ProposalKind = Literal["tool", "skill", "plugin"]


@dataclass(frozen=True)
class CapabilityProposal:
    kind: ProposalKind
    artifact_name: str
    content: str
    status: Literal["proposed", "validated"] = "validated"
    activation_status: Literal["disabled"] = "disabled"


class CapabilityProposalError(ValueError):
    """Raised when a self-extension request cannot be safely materialized."""


class CapabilityProposalFactory:
    """Build schema-checked, disabled artifacts from structured requirements."""

    @staticmethod
    def _dump(data: dict[str, Any]) -> str:
        return yaml.safe_dump(data, sort_keys=True, allow_unicode=True)

    def propose_tool(
        self,
        *,
        tool_id: str,
        version: str,
        required_permission: str,
        input_schema: dict[str, Any],
    ) -> CapabilityProposal:
        raw = {
            "tool_id": tool_id,
            "version": version,
            "status": "disabled",
            "required_permission": required_permission,
            "input_schema": input_schema,
        }
        try:
            item = ToolDefinition.validate_definition(raw)
        except CapabilityDefinitionError as exc:
            raise CapabilityProposalError("Generated tool failed schema validation.") from exc
        return CapabilityProposal(
            kind="tool",
            artifact_name=f"{item.tool_id.replace('.', '_')}.tool.yaml",
            content=self._dump(item.model_dump(mode="json")),
        )

    def propose_skill(
        self,
        *,
        skill_id: str,
        version: str,
        description: str,
        instructions: str,
        required_permissions: tuple[str, ...] = (),
    ) -> CapabilityProposal:
        raw = {
            "skill_id": skill_id,
            "version": version,
            "status": "disabled",
            "description": description,
            "required_permissions": required_permissions,
            "instructions": instructions,
        }
        try:
            item = SkillDefinition.model_validate(raw)
        except ValidationError as exc:
            raise CapabilityProposalError("Generated skill failed schema validation.") from exc
        return CapabilityProposal(
            kind="skill",
            artifact_name=f"{item.skill_id.replace('.', '_')}.skill.yaml",
            content=self._dump(item.model_dump(mode="json")),
        )

    def propose_plugin(
        self,
        *,
        plugin_id: str,
        name: str,
        version: str,
        kind: Literal["tool", "provider", "channel", "hook", "skill"],
        requested_permissions: tuple[str, ...] = (),
        capabilities: tuple[str, ...] = (),
    ) -> CapabilityProposal:
        # Requested permissions are recorded for human/core review only.
        # Actual grants are always empty and the plugin remains disabled.
        raw = {
            "plugin_id": plugin_id,
            "name": name,
            "version": version,
            "kind": kind,
            "status": "disabled",
            "capabilities": capabilities,
            "permissions": (),
            "requested_permissions": requested_permissions,
        }
        try:
            item = PluginManifest.model_validate(raw)
        except ValidationError as exc:
            raise CapabilityProposalError("Generated plugin failed manifest validation.") from exc
        return CapabilityProposal(
            kind="plugin",
            artifact_name=f"{item.plugin_id}/plugin.yaml",
            content=self._dump(item.model_dump(mode="json")),
        )
