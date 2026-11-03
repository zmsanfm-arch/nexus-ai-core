"""Strict CSV OHLC ingestion for research datasets; no vendor connection implied."""
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app.backtesting.engine import Candle


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
    raw = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("CSV must contain timestamp, open, high, low, close columns")
        for line, row in enumerate(reader, start=2):
            try:
                timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                    raise ValueError("timestamp must include a timezone")
                values = [float(row[key]) for key in ("open", "high", "low", "close")]
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid row {line}: {exc}") from exc
            candle = Candle(timestamp, *values)
            if min(values) <= 0 or candle.high < max(candle.open, candle.close, candle.low) or candle.low > min(candle.open, candle.close, candle.high):
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
        if expected_interval.total_seconds() <= 0:
            raise ValueError("Expected interval must be positive")
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
