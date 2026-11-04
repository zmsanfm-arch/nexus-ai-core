import pytest

from app.services.workflow_planner import (
    WorkflowNode,
    WorkflowPlanError,
    build_workflow_plan,
)


def test_planner_builds_stable_dependency_levels():
    plan = build_workflow_plan([
        WorkflowNode("audit", "auditor", ("analysis",)),
        WorkflowNode("research", "research"),
        WorkflowNode("analysis", "analyst", ("research",)),
        WorkflowNode("context", "research"),
    ])

    assert plan.levels == (("context", "research"), ("analysis",), ("audit",))
    assert [node.node_id for node in plan.ordered_nodes] == [
        "context", "research", "analysis", "audit"
    ]


def test_planner_rejects_duplicate_ids_and_dependencies():
    with pytest.raises(WorkflowPlanError, match="Duplicate workflow node"):
        build_workflow_plan([
            WorkflowNode("same", "research"),
            WorkflowNode("same", "analysis"),
        ])

    with pytest.raises(WorkflowPlanError, match="Duplicate dependency"):
        WorkflowNode("analysis", "analyst", ("research", "research"))


def test_planner_rejects_missing_dependencies_and_cycles():
    with pytest.raises(WorkflowPlanError, match="unknown dependencies"):
        build_workflow_plan([WorkflowNode("analysis", "analyst", ("missing",))])

    with pytest.raises(WorkflowPlanError, match="dependency cycle"):
        build_workflow_plan([
            WorkflowNode("a", "research", ("b",)),
            WorkflowNode("b", "analysis", ("a",)),
        ])


def test_planner_enforces_node_and_attempt_budgets():
    with pytest.raises(WorkflowPlanError, match="node limit"):
        build_workflow_plan(
            [WorkflowNode("a", "research"), WorkflowNode("b", "analysis")],
            max_nodes=1,
        )

    with pytest.raises(WorkflowPlanError, match="attempt budget"):
        build_workflow_plan(
            [WorkflowNode("a", "research", max_attempts=2)],
            max_total_attempts=1,
        )


def test_node_rejects_self_dependency_and_invalid_attempt_count():
    with pytest.raises(WorkflowPlanError, match="depend on itself"):
        WorkflowNode("a", "research", ("a",))

    with pytest.raises(WorkflowPlanError, match="at least 1"):
        WorkflowNode("a", "research", max_attempts=0)
