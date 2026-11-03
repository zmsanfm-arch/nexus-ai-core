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
