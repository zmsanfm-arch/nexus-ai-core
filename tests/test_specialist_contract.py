import pytest
from pydantic import ValidationError

from app.services.manifest_loader import ManifestError, load_manifest
from app.services.specialist_contract import SpecialistInput, SpecialistResult


def test_ict_manifest_loads_disabled_and_advisory_only():
    manifest = load_manifest("agents/ict_mentor/agent.yaml")
    assert manifest.agent_id == "ict_mentor"
    assert manifest.status == "disabled"
    assert manifest.mode == "advisory"
    assert manifest.permissions == ()
    assert "ict.chart_analysis" in manifest.capabilities


def test_manifest_rejects_unknown_fields(tmp_path):
    path = tmp_path / "agent.yaml"
    path.write_text(
        "agent_id: unsafe_agent\nname: Unsafe\nversion: 1.0.0\n"
        "status: registered\nmode: advisory\npermissions: [broker.trade]\n"
        "unexpected: true\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        load_manifest(path)


def test_specialist_result_rejects_execution_payload():
    with pytest.raises(ValidationError):
        SpecialistResult(
            agent_id="ict_mentor",
            mode="advisory",
            answer="Analysis only",
            execution_result={"order_id": "123"},
        )


def test_specialist_input_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SpecialistInput(task_id="t1", task_type="ict.education", context={}, tools=["mt5"])



def test_specialist_input_rejects_context_over_16_kib():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="16 KiB"):
        SpecialistInput(
            task_id="task-large",
            task_type="ict.education",
            context={"payload": "x" * 17_000},
        )



def test_specialist_input_accepts_ict_v1_envelope():
    request = SpecialistInput(
        task_id="task-ict-1",
        task_type="ict.chart_analysis",
        mode="advisory",
        request="Analyze the supplied chart only",
        chart={"attachment_id": "chart-1"},
        user_rules=[{"rule_id": "R1", "text": "Risk per trade is user-defined", "status": "user_confirmed"}],
        retrieved_sources=[],
        correlation_id="corr-1",
    )
    assert request.request.startswith("Analyze")
    assert request.mode == "advisory"
    assert request.correlation_id == "corr-1"


def test_specialist_output_uses_structured_provenance_and_advisory_fields():
    result = SpecialistResult(
        agent_id="ict_mentor",
        mode="advisory",
        answer="A possible liquidity sweep is visible.",
        source_claims=[{
            "claim": "The concept describes a run on resting liquidity.",
            "source_id": "src-1",
            "title": "ICT reference",
            "url": "https://example.org/ict",
            "retrieved_at": "2026-11-04T10:00:00Z",
            "segment_id": "seg-4",
        }],
        user_rules_used=[{"rule_id": "R1", "text": "User-confirmed rule"}],
        agent_inferences=[{
            "inference": "The move may be a sweep.",
            "basis": "Visible wick beyond prior high.",
            "confidence": "medium",
        }],
        proposed_actions=[{
            "action": "Wait for confirmation",
            "rationale": "The supplied chart alone is insufficient.",
            "requires_central_review": True,
        }],
        risk_decision="refer_to_central_risk_engine",
        execution_result=None,
    )
    assert result.source_claims[0].segment_id == "seg-4"
    assert result.agent_inferences[0].confidence == "medium"
    assert result.proposed_actions[0].requires_central_review is True
    assert result.execution_result is None


def test_specialist_output_rejects_invalid_risk_decision_and_execution():
    with pytest.raises(ValidationError):
        SpecialistResult(
            agent_id="ict_mentor",
            answer="No",
            risk_decision="approved",
        )
    with pytest.raises(ValidationError):
        SpecialistResult(
            agent_id="ict_mentor",
            answer="No",
            execution_result={"order_id": "123"},
        )
