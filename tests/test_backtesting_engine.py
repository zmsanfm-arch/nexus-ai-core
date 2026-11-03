from datetime import datetime, timedelta, timezone

import pytest

from app.backtesting.engine import (
    BacktestConfig, Candle, ExecutionCosts, TradeIntent, run_backtest,
)


def ts(minutes):
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes)


def test_long_trade_uses_explicit_costs_and_stop_fill():
    bars = [
        Candle(ts(1), 100, 102, 99, 101),
        Candle(ts(2), 101, 103, 98, 100),
    ]
    intent = TradeIntent("t1", "long", ts(0), ts(1), 100, 98, 103, 1)
    result = run_backtest(
        bars, [intent],
        BacktestConfig(costs=ExecutionCosts(spread=0.2, slippage=0.1, commission_per_unit_per_side=0.05)),
    )[0]
    assert result.exit_reason == "stop"
    assert result.entry_fill == pytest.approx(100.2)
    assert result.exit_fill == pytest.approx(97.8)
    assert result.costs == pytest.approx(0.5)
    assert result.net_pnl == pytest.approx(-2.5)


def test_same_bar_ambiguity_can_be_rejected():
    bars = [Candle(ts(1), 100, 104, 97, 101)]
    intent = TradeIntent("t2", "long", ts(0), ts(1), 100, 98, 103)
    with pytest.raises(ValueError, match="Ambiguous"):
        run_backtest(bars, [intent], BacktestConfig(same_bar_policy="reject_ambiguous"))


def test_gap_through_stop_fills_at_worse_open():
    bars = [
        Candle(ts(1), 100, 101, 99, 100),
        Candle(ts(2), 95, 97, 94, 96),
    ]
    intent = TradeIntent("t3", "long", ts(0), ts(1), 100, 98, 105)
    result = run_backtest(bars, [intent])[0]
    assert result.exit_fill == 95
    assert result.exit_reason == "stop"


def test_invalid_long_levels_are_rejected():
    intent = TradeIntent("t4", "long", ts(0), ts(1), 100, 101, 105)
    with pytest.raises(ValueError, match="ordering"):
        run_backtest([Candle(ts(1), 100, 101, 99, 100)], [intent])


def test_single_position_engine_rejects_overlapping_intents():
    bars = [
        Candle(ts(1), 100, 101, 99, 100),
        Candle(ts(2), 100, 104, 99, 103),
    ]
    first = TradeIntent("t5", "long", ts(0), ts(1), 100, 98, 103)
    second = TradeIntent("t6", "long", ts(1), ts(2), 100, 98, 103)
    with pytest.raises(ValueError, match="Overlapping"):
        run_backtest(bars, [first, second])


def test_favorable_gap_through_target_uses_open_price():
    bars = [
        Candle(ts(1), 100, 101, 99, 100),
        Candle(ts(2), 105, 106, 104, 105),
    ]
    intent = TradeIntent("t7", "long", ts(0), ts(1), 100, 98, 103)
    result = run_backtest(bars, [intent])[0]
    assert result.exit_reason == "target"
    assert result.exit_fill == 105
