from datetime import datetime, timezone

import pytest

from app.backtesting.engine import TradeResult
from app.backtesting.evaluator import evaluate_trades


def trade(trade_id, pnl, minute):
    t = datetime(2026, 1, 1, minute, tzinfo=timezone.utc)
    return TradeResult(
        trade_id=trade_id, direction="long", entry_time=t, exit_time=t,
        entry_fill=100, exit_fill=100, exit_reason="target", quantity=1,
        gross_pnl=pnl, costs=0, net_pnl=pnl,
    )


def test_evaluator_reports_ledger_metrics_and_drawdown():
    result = evaluate_trades([trade("a", 10, 1), trade("b", -5, 2), trade("c", 5, 3)], 100)
    assert result.trade_count == 3
    assert result.wins == 2
    assert result.losses == 1
    assert result.win_rate == 2 / 3
    assert result.profit_factor == 3
    assert result.net_profit == 10
    assert result.max_drawdown == pytest.approx(5 / 110)
    assert result.equity_curve == (100, 110, 105, 110)


def test_evaluator_handles_empty_ledger():
    result = evaluate_trades([], 100)
    assert result.trade_count == 0
    assert result.win_rate is None
    assert result.average_trade_pnl is None
    assert result.equity_curve == (100,)
