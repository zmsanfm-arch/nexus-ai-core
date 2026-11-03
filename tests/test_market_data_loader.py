from datetime import timedelta

import pytest

from app.market_data.csv_loader import load_ohlc_csv


def test_loader_normalizes_order_and_reports_missing_intervals(tmp_path):
    path = tmp_path / "bars.csv"
    path.write_text(
        "timestamp,open,high,low,close\n"
        "2026-01-01T00:02:00Z,101,102,100,101\n"
        "2026-01-01T00:00:00Z,100,101,99,100\n",
        encoding="utf-8",
    )
    dataset = load_ohlc_csv(path, timedelta(minutes=1))
    assert dataset.quality.row_count == 2
    assert dataset.quality.out_of_order_rows == 1
    assert dataset.quality.missing_intervals == 1
    assert dataset.candles[0].open == 100


def test_loader_rejects_timezone_naive_and_duplicate_rows(tmp_path):
    path = tmp_path / "bars.csv"
    path.write_text(
        "timestamp,open,high,low,close\n"
        "2026-01-01T00:00:00,100,101,99,100\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="timezone"):
        load_ohlc_csv(path)

    path.write_text(
        "timestamp,open,high,low,close\n"
        "2026-01-01T00:00:00Z,100,101,99,100\n"
        "2026-01-01T00:00:00Z,100,101,99,100\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate"):
        load_ohlc_csv(path)
