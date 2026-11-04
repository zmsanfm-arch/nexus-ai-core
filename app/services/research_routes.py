"""Central API routes for immutable strategy research and historical market data."""
import hashlib
import json
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.market_data.csv_loader import load_ohlc_csv
from app.services.research_store import ResearchStore
from app.services.strategy_lifecycle import evaluate_transition


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataPayload(StrictPayload):
    data: dict[str, Any] = Field(min_length=1)

    @field_validator("data")
    @classmethod
    def data_must_be_bounded_json(cls, value):
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Research data must contain finite JSON-compatible values") from exc
        if len(encoded.encode("utf-8")) > 262144:
            raise ValueError("Research data exceeds the 256 KiB limit")
        return value


class TransitionPayload(StrictPayload):
    target_state: Literal[
        "candidate", "backtested", "oos_validated", "demo_approved",
        "demo_active", "suspended", "retired",
    ]
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence")
    @classmethod
    def evidence_must_be_bounded_json(cls, value):
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Transition evidence must contain finite JSON-compatible values") from exc
        if len(encoded.encode("utf-8")) > 16384:
            raise ValueError("Transition evidence exceeds the 16 KiB limit")
        return value


def _validate_contract(schema_name: str, payload: dict) -> None:
    schema_path = Path(__file__).resolve().parents[2] / "docs" / "strategy-research" / "schemas" / schema_name
    try:
        import json
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload),
            key=lambda error: list(error.path),
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Research schema is unavailable or invalid") from exc
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "$"
        raise HTTPException(
            status_code=422,
            detail=f"Invalid research contract at {location}: {first.message}",
        )


def register_research_routes(app, storage, require_api_access, require_admin):
    """Attach authenticated routes; all writes remain admin-controlled."""
    router = APIRouter()
    research = ResearchStore(storage.engine)

    @router.post("/strategies/{strategy_id}/versions")
    def create_strategy_version(
        strategy_id: str,
        payload: DataPayload,
        reviewer_id: str = Depends(require_admin),
    ):
        data = payload.data
        if data.get("strategy_id") != strategy_id:
            raise HTTPException(status_code=422, detail="strategy_id in payload must match URL")
        _validate_contract("strategy.schema.json", data)
        if data.get("status") != "draft":
            raise HTTPException(status_code=422, detail="New strategy versions must start in draft")
        if not isinstance(data.get("version"), str) or len(data["version"]) > 32:
            raise HTTPException(status_code=422, detail="Strategy version must not exceed 32 characters")
        try:
            record_id = research.create_strategy_version(strategy_id, data["version"], data)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        storage.append_audit({
            "event": "strategy_version_created", "strategy_id": strategy_id,
            "version": data["version"], "actor": reviewer_id, "status": data["status"],
        })
        return {
            "id": record_id, "strategy_id": strategy_id,
            "version": data["version"], "status": data["status"],
        }

    @router.get("/strategies/{strategy_id}/versions/{version}")
    def get_strategy_version(
        strategy_id: str, version: str,
        principal_id: str = Depends(require_api_access),
    ):
        data = research.get_strategy_version(strategy_id, version)
        if data is None:
            raise HTTPException(status_code=404, detail="Strategy version not found")
        return {"strategy_id": strategy_id, "version": version, "data": data}

    @router.post("/research/experiments")
    def create_experiment(
        payload: DataPayload,
        reviewer_id: str = Depends(require_admin),
    ):
        data = payload.data
        _validate_contract("experiment-plan.schema.json", data)
        try:
            research.save_research_record("experiment", data["experiment_id"], data)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        storage.append_audit({
            "event": "research_experiment_created",
            "experiment_id": data["experiment_id"], "actor": reviewer_id,
            "strategy_id": data["strategy_id"], "strategy_version": data["strategy_version"],
        })
        return {"experiment_id": data["experiment_id"], "status": "registered"}

    @router.get("/research/experiments/{experiment_id}")
    def get_experiment(
        experiment_id: str,
        principal_id: str = Depends(require_api_access),
    ):
        record = research.get_research_record(experiment_id)
        if record is None or record.get("record_type") != "experiment":
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {
            "experiment_id": experiment_id,
            "data": {key: value for key, value in record.items() if key != "record_type"},
        }

    @router.post("/strategies/{strategy_id}/versions/{version}/transitions")
    def transition_strategy(
        strategy_id: str,
        version: str,
        payload: TransitionPayload,
        reviewer_id: str = Depends(require_admin),
    ):
        strategy = research.get_strategy_version(strategy_id, version)
        if strategy is None:
            raise HTTPException(status_code=404, detail="Strategy version not found")
        history = [
            item for item in research.list_strategy_transitions(strategy_id)
            if item["version"] == version
        ]
        current_state = history[-1]["to_state"] if history else strategy["status"]
        decision = evaluate_transition(current_state, payload.target_state, payload.evidence)
        if not decision.allowed:
            storage.append_audit({
                "event": "strategy_transition_blocked", "strategy_id": strategy_id,
                "version": version, "from_state": current_state,
                "to_state": payload.target_state,
                "missing_evidence": list(decision.missing_evidence), "actor": reviewer_id,
            })
            raise HTTPException(
                status_code=409,
                detail={"reason": decision.reason, "missing_evidence": list(decision.missing_evidence)},
            )
        transition = {
            "transition_id": str(uuid.uuid4()), "strategy_id": strategy_id,
            "version": version, "from_state": current_state,
            "to_state": payload.target_state, "evidence": payload.evidence,
            "actor": reviewer_id, "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        research.save_research_record("strategy_transition", transition["transition_id"], transition)
        storage.append_audit({
            "event": "strategy_transition_accepted", "strategy_id": strategy_id,
            "version": version, "from_state": current_state,
            "to_state": payload.target_state, "actor": reviewer_id,
        })
        return transition

    @router.get("/strategies/{strategy_id}/versions/{version}/transitions")
    def get_strategy_transitions(
        strategy_id: str, version: str,
        principal_id: str = Depends(require_api_access),
    ):
        strategy = research.get_strategy_version(strategy_id, version)
        if strategy is None:
            raise HTTPException(status_code=404, detail="Strategy version not found")
        history = [
            item for item in research.list_strategy_transitions(strategy_id)
            if item["version"] == version
        ]
        current_state = history[-1]["to_state"] if history else strategy["status"]
        return {
            "strategy_id": strategy_id, "version": version,
            "current_state": current_state, "history": history,
        }

    @router.post("/market-data/datasets")
    async def import_market_dataset(
        file: UploadFile = File(...),
        instrument: str = Form(..., min_length=3, max_length=64),
        timeframe: str = Form(..., pattern="^(M1|M5|M15|M30|H1|H4|D1)$"),
        expected_interval_seconds: int | None = Form(default=None, ge=1, le=86400),
        reviewer_id: str = Depends(require_admin),
    ):
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=415, detail="Only CSV market-data files are accepted")
        raw = await file.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Market-data CSV exceeds the 5 MiB import limit")
        try:
            text_data = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="CSV must be UTF-8 encoded") from exc
        if not text_data.strip():
            raise HTTPException(status_code=422, detail="CSV is empty")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8", newline="") as temp:
            temp.write(text_data)
            temp.flush()
            try:
                dataset = load_ohlc_csv(
                    temp.name,
                    expected_interval=timedelta(seconds=expected_interval_seconds)
                    if expected_interval_seconds else None,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        dataset_id = str(uuid.uuid4())
        candles = [{
            "timestamp": candle.timestamp.isoformat(),
            "open": candle.open, "high": candle.high,
            "low": candle.low, "close": candle.close,
        } for candle in dataset.candles]
        quality = asdict(dataset.quality)
        digest = hashlib.sha256(raw).hexdigest()
        research.save_market_dataset({
            "id": dataset_id, "instrument": instrument.upper(),
            "timeframe": timeframe, "content_sha256": digest,
            "row_count": len(candles), "quality": quality,
            "candles": candles, "created_at": datetime.now(timezone.utc),
        })
        storage.append_audit({
            "event": "market_dataset_imported", "dataset_id": dataset_id,
            "instrument": instrument.upper(), "timeframe": timeframe,
            "row_count": len(candles), "actor": reviewer_id,
        })
        return {
            "dataset_id": dataset_id, "instrument": instrument.upper(),
            "timeframe": timeframe, "row_count": len(candles),
            "content_sha256": digest, "quality": quality,
        }

    @router.get("/market-data/datasets/{dataset_id}")
    def get_market_dataset(
        dataset_id: str,
        principal_id: str = Depends(require_api_access),
    ):
        dataset = research.get_market_dataset(dataset_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Market dataset not found")
        return {key: value for key, value in dataset.items() if key != "candles"}

    @router.get("/market-data/datasets/{dataset_id}/candles")
    def get_market_dataset_candles(
        dataset_id: str, offset: int = 0, limit: int = 1000,
        principal_id: str = Depends(require_api_access),
    ):
        if offset < 0 or limit < 1 or limit > 5000:
            raise HTTPException(status_code=422, detail="Invalid pagination")
        dataset = research.get_market_dataset(dataset_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Market dataset not found")
        return {
            "dataset_id": dataset_id, "offset": offset, "limit": limit,
            "total": dataset["row_count"],
            "candles": dataset["candles"][offset:offset + limit],
        }

    app.include_router(router)
