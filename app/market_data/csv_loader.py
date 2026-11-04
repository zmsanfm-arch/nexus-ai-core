"""Strict, resource-bounded CSV OHLC ingestion for research datasets."""
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from pathlib import Path

from app.backtesting.engine import Candle


MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_CSV_ROWS = 10000


@dataclass(frozen=True)
class DataQuality:
    row_count: int
    duplicate_timestamps: int
    out_of_order_rows: int
    missing_intervals: int
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class CandleDataset:
    candles: tuple[Candle, ...]
    quality: DataQuality


def load_ohlc_csv(path: str | Path, expected_interval: timedelta | None = None) -> CandleDataset:
    required = {"timestamp", "open", "high", "low", "close"}
    source_path = Path(path)
    if source_path.stat().st_size > MAX_CSV_BYTES:
        raise ValueError("CSV exceeds the 5 MiB ingestion limit")
    if expected_interval is not None and (
        not isinstance(expected_interval, timedelta) or expected_interval.total_seconds() <= 0
    ):
        raise ValueError("Expected interval must be a positive duration")
    raw = []
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("CSV must contain timestamp, open, high, low, close columns")
        for line, row in enumerate(reader, start=2):
            if len(raw) >= MAX_CSV_ROWS:
                raise ValueError("CSV exceeds the 10000-row ingestion limit")
            try:
                timestamp_text = row["timestamp"]
                if not timestamp_text or len(timestamp_text) > 64:
                    raise ValueError("timestamp field is empty or too long")
                timestamp = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
                if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                    raise ValueError("timestamp must include a timezone")
                values = []
                for key in ("open", "high", "low", "close"):
                    field = row[key]
                    if field is None or len(field) > 64:
                        raise ValueError(f"{key} field is empty or too long")
                    value = float(field)
                    if not isfinite(value) or value <= 0:
                        raise ValueError(f"{key} must be finite and positive")
                    values.append(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid row {line}: {exc}") from exc
            candle = Candle(timestamp, *values)
            if candle.high < max(candle.open, candle.close, candle.low) or candle.low > min(candle.open, candle.close, candle.high):
                raise ValueError(f"Invalid OHLC values on row {line}")
            raw.append(candle)

    if not raw:
        raise ValueError("Dataset is empty")
    ordered = sorted(raw, key=lambda item: item.timestamp)
    timestamps = [item.timestamp for item in raw]
    duplicates = len(timestamps) - len(set(timestamps))
    out_of_order = sum(1 for left, right in zip(timestamps, timestamps[1:]) if right <= left)
    if duplicates:
        raise ValueError("Duplicate timestamps are not allowed")
    missing = 0
    if expected_interval is not None:
        for left, right in zip(ordered, ordered[1:]):
            delta = right.timestamp - left.timestamp
            if delta > expected_interval:
                missing += max(0, int(delta / expected_interval) - 1)
    warnings = []
    if out_of_order:
        warnings.append("Rows were not in chronological order; normalized by timestamp")
    if missing:
        warnings.append(f"{missing} expected intervals are missing")
    return CandleDataset(
        candles=tuple(ordered),
        quality=DataQuality(len(ordered), duplicates, out_of_order, missing, tuple(warnings)),
    )
