"""Validated, user-authored mission definitions for agent workflows.

A mission is a declarative DAG. This module validates and compiles it only;
it does not execute agents, grant permissions, or invoke external tools.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.workflow_planner import (
    WorkflowNode,
    WorkflowPlan,
    WorkflowPlanError,
    build_workflow_plan,
)


class MissionContractError(ValueError):
    """Raised when a mission definition is invalid or unauthorized."""


class MissionNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    agent_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    capability: str = Field(pattern=r"^[a-z][a-z0-9_.]{1,127}$")
    dependencies: tuple[str, ...] = ()
    max_attempts: int = Field(default=1, ge=1, le=8)


class MissionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mission_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    name: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1, max_length=4000)
    nodes: tuple[MissionNode, ...] = Field(min_length=1, max_length=32)
    max_total_attempts: int = Field(default=32, ge=1, le=64)
    approval_policy: Literal["required_for_external_actions"] = (
        "required_for_external_actions"
    )

    @model_validator(mode="after")
    def validate_graph_and_budget(self):
        try:
            build_workflow_plan(
                tuple(
                    WorkflowNode(
                        node.node_id,
                        node.agent_id,
                        node.dependencies,
                        node.max_attempts,
                    )
                    for node in self.nodes
                ),
                max_nodes=32,
                max_total_attempts=self.max_total_attempts,
            )
        except WorkflowPlanError as exc:
            raise ValueError(str(exc)) from exc
        return self


def compile_mission(
    mission: MissionDefinition,
    registered_agent_ids: set[str] | frozenset[str],
) -> WorkflowPlan:
    """Compile a mission only when every referenced agent is registered.

    Registration is not execution authorization: callers must still enforce
    capability permissions and require installed handlers at runtime.
    """
    unknown = sorted(
        {node.agent_id for node in mission.nodes} - set(registered_agent_ids)
    )
    if unknown:
        raise MissionContractError(
            "Mission references unregistered agents: " + ", ".join(unknown)
        )
    try:
        return build_workflow_plan(
            tuple(
                WorkflowNode(
                    node.node_id,
                    node.agent_id,
                    node.dependencies,
                    node.max_attempts,
                )
                for node in mission.nodes
            ),
            max_nodes=32,
            max_total_attempts=mission.max_total_attempts,
        )
    except WorkflowPlanError as exc:
        raise MissionContractError(str(exc)) from exc
