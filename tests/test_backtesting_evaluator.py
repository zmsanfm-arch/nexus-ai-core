from datetime import datetime, timezone

import pytest

from app.backtesting.engine import TradeResult
from app.backtesting.evaluator import evaluate_trades, evaluate_acceptance


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


def test_acceptance_blocks_when_required_evidence_is_missing():
    evaluation = evaluate_trades([trade("a", 10, 1), trade("b", -5, 2)], 100)
    decision = evaluate_acceptance(
        evaluation,
        {
            "minimum_trades": 2,
            "minimum_profit_factor": 1.5,
            "maximum_drawdown": 0.1,
            "minimum_expectancy_r": 0.2,
            "robustness_required": True,
            "criteria_owner": "research_default",
        },
    )
    assert decision.status == "blocked"
    assert "minimum_expectancy_r" in decision.unevaluable
    assert "robustness_required" in decision.unevaluable


def test_acceptance_fails_if_any_declared_threshold_is_missed():
    evaluation = evaluate_trades([trade("a", 10, 1), trade("b", -5, 2)], 100)
    decision = evaluate_acceptance(
        evaluation,
        {
            "minimum_trades": 10,
            "minimum_profit_factor": 1,
            "maximum_drawdown": 0.1,
            "minimum_expectancy_r": 0.1,
            "robustness_required": False,
            "criteria_owner": "user",
        },
        expectancy_r=0.5,
    )
    assert decision.status == "fail"
    assert "minimum_trades" in decision.failed


def test_evaluator_computes_expectancy_r_from_trade_ledger():
    from dataclasses import replace

    first = replace(trade("r1", 10, 1), initial_risk=5, r_multiple=2.0)
    second = replace(trade("r2", -5, 2), initial_risk=5, r_multiple=-1.0)
    result = evaluate_trades([first, second], 100)
    assert result.expectancy_r == 0.5
    assert result.average_r == 0.5
    decision = evaluate_acceptance(
        result,
        {
            "minimum_trades": 2,
            "minimum_profit_factor": 1,
            "maximum_drawdown": 0.1,
            "minimum_expectancy_r": 0.4,
            "robustness_required": False,
            "criteria_owner": "research_default",
        },
    )
    assert decision.status == "pass"
