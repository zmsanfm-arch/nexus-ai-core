"""Declarative tool and skill catalogs; definitions never execute code."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class CapabilityDefinitionError(ValueError):
    pass


class ToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tool_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{1,95}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    status: Literal["disabled", "enabled"]
    required_permission: str = Field(pattern=r"^[a-z][a-z0-9_.-]{1,127}$")
    input_schema: dict[str, Any]

    @classmethod
    def validate_definition(cls, raw: dict[str, Any]) -> "ToolDefinition":
        try:
            item = cls.model_validate(raw)
            Draft202012Validator.check_schema(item.input_schema)
            if item.input_schema.get("type") != "object":
                raise CapabilityDefinitionError("Tool input schema must be an object.")
            return item
        except (ValidationError, Exception) as exc:
            if isinstance(exc, CapabilityDefinitionError):
                raise
            raise CapabilityDefinitionError("Invalid tool definition.") from exc


class SkillDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    skill_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{1,95}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    status: Literal["disabled", "enabled"]
    description: str = Field(min_length=1, max_length=500)
    required_permissions: tuple[str, ...] = ()
    instructions: str = Field(min_length=1, max_length=12000)


def load_tool_definition(path: str | Path) -> ToolDefinition:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise CapabilityDefinitionError("Tool definition must be a mapping.")
        return ToolDefinition.validate_definition(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise CapabilityDefinitionError("Invalid tool definition file.") from exc


def load_skill_definition(path: str | Path) -> SkillDefinition:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise CapabilityDefinitionError("Skill definition must be a mapping.")
        return SkillDefinition.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise CapabilityDefinitionError("Invalid skill definition file.") from exc