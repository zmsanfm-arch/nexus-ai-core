"""Deterministic, bounded dependency planning for multi-agent workflows.

This module deliberately plans work only. It does not grant tools, permissions,
or execution capabilities to agents.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class WorkflowPlanError(ValueError):
    """Raised when a workflow graph is invalid or exceeds configured bounds."""


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    agent_id: str
    dependencies: tuple[str, ...] = ()
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if not self.node_id or not self.node_id.strip():
            raise WorkflowPlanError("Workflow node id must not be empty.")
        if not self.agent_id or not self.agent_id.strip():
            raise WorkflowPlanError("Workflow agent id must not be empty.")
        if self.max_attempts < 1:
            raise WorkflowPlanError("max_attempts must be at least 1.")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise WorkflowPlanError(f"Duplicate dependency in node: {self.node_id}")
        if self.node_id in self.dependencies:
            raise WorkflowPlanError(f"Node cannot depend on itself: {self.node_id}")


@dataclass(frozen=True)
class WorkflowPlan:
    ordered_nodes: tuple[WorkflowNode, ...]
    levels: tuple[tuple[str, ...], ...]
    max_attempts: int


def build_workflow_plan(
    nodes: Iterable[WorkflowNode],
    *,
    max_nodes: int = 32,
    max_total_attempts: int = 64,
) -> WorkflowPlan:
    """Validate a DAG and return stable topological execution levels.

    Nodes in the same level have all dependencies satisfied and may be scheduled
    concurrently by a future bounded scheduler. Ordering is stable by node id.
    """
    items = tuple(nodes)
    if not items:
        raise WorkflowPlanError("Workflow must contain at least one node.")
    if max_nodes < 1 or len(items) > max_nodes:
        raise WorkflowPlanError("Workflow exceeds the configured node limit.")
    by_id: dict[str, WorkflowNode] = {}
    for node in items:
        if node.node_id in by_id:
            raise WorkflowPlanError(f"Duplicate workflow node: {node.node_id}")
        by_id[node.node_id] = node

    for node in items:
        missing = sorted(set(node.dependencies) - by_id.keys())
        if missing:
            raise WorkflowPlanError(
                f"Node {node.node_id} has unknown dependencies: {', '.join(missing)}"
            )

    total_attempts = sum(node.max_attempts for node in items)
    if total_attempts > max_total_attempts:
        raise WorkflowPlanError("Workflow exceeds the configured attempt budget.")

    remaining = set(by_id)
    completed: set[str] = set()
    levels: list[tuple[str, ...]] = []
    while remaining:
        ready = tuple(sorted(
            node_id for node_id in remaining
            if set(by_id[node_id].dependencies).issubset(completed)
        ))
        if not ready:
            raise WorkflowPlanError("Workflow contains a dependency cycle.")
        levels.append(ready)
        completed.update(ready)
        remaining.difference_update(ready)

    ordered = tuple(by_id[node_id] for level in levels for node_id in level)
    return WorkflowPlan(
        ordered_nodes=ordered,
        levels=tuple(levels),
        max_attempts=total_attempts,
    )
