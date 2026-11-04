"""Transparent metrics for deterministic backtest trade ledgers."""
from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from app.backtesting.engine import TradeResult


@dataclass(frozen=True)
class Evaluation:
    trade_count: int
    wins: int
    losses: int
    breakeven: int
    win_rate: float | None
    gross_profit: float
    gross_loss: float
    profit_factor: float | None
    net_profit: float
    average_trade_pnl: float | None
    expectancy_r: float | None
    average_r: float | None
    max_drawdown: float
    equity_curve: tuple[float, ...]


def evaluate_trades(trades: Sequence[TradeResult], initial_equity: float) -> Evaluation:
    if isinstance(initial_equity, bool) or not isinstance(initial_equity, (int, float)) or not isfinite(initial_equity) or initial_equity <= 0:
        raise ValueError("Initial equity must be finite and positive")
    ordered = sorted(trades, key=lambda trade: (trade.exit_time, trade.trade_id))
    pnls = []
    r_values = []
    for trade in ordered:
        pnl = trade.net_pnl
        if isinstance(pnl, bool) or not isinstance(pnl, (int, float)) or not isfinite(pnl):
            raise ValueError("Trade net PnL values must be finite numbers")
        pnls.append(float(pnl))
        if trade.r_multiple is not None:
            value = trade.r_multiple
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError("Trade R-multiples must be finite numbers")
            r_values.append(float(value))
    wins = sum(pnl > 0 for pnl in pnls)
    losses = sum(pnl < 0 for pnl in pnls)
    breakeven = len(pnls) - wins - losses
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    equity = float(initial_equity)
    peak = equity
    max_drawdown = 0.0
    curve = [equity]
    for pnl in pnls:
        equity += pnl
        if not isfinite(equity):
            raise ValueError("Equity curve overflowed the finite numeric range")
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
        curve.append(equity)
    return Evaluation(
        trade_count=len(pnls), wins=wins, losses=losses, breakeven=breakeven,
        win_rate=(wins / len(pnls)) if pnls else None,
        gross_profit=gross_profit, gross_loss=gross_loss,
        profit_factor=(gross_profit / gross_loss) if gross_loss else None,
        net_profit=sum(pnls),
        average_trade_pnl=(sum(pnls) / len(pnls)) if pnls else None,
        expectancy_r=(sum(r_values) / len(r_values)) if r_values else None,
        average_r=(sum(r_values) / len(r_values)) if r_values else None,
        max_drawdown=max_drawdown, equity_curve=tuple(curve),
    )


@dataclass(frozen=True)
class AcceptanceDecision:
    status: str
    criteria_owner: str
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    unevaluable: tuple[str, ...]


def evaluate_acceptance(
    evaluation: Evaluation,
    criteria: dict,
    *,
    expectancy_r: float | None = None,
    robustness_passed: bool | None = None,
) -> AcceptanceDecision:
    """Evaluate predeclared gates; malformed or missing evidence never passes."""
    if not isinstance(criteria, dict):
        raise ValueError("Acceptance criteria must be an object")
    owner = criteria.get("criteria_owner", "research_default")
    if owner not in {"user", "central_policy", "research_default"}:
        raise ValueError("Unknown acceptance criteria owner")

    def finite_number(name, value, *, integer=False):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if integer and (not isinstance(value, int) or value < 0):
            raise ValueError(f"{name} must be a non-negative integer")
        return value

    passed, failed, unevaluable = [], [], []
    checks = [
        ("minimum_trades", evaluation.trade_count, lambda actual, limit: actual >= limit, True),
        ("minimum_profit_factor", evaluation.profit_factor, lambda actual, limit: actual is not None and actual >= limit, False),
        ("maximum_drawdown", evaluation.max_drawdown, lambda actual, limit: actual <= limit, False),
    ]
    for name, actual, predicate, integer in checks:
        limit = criteria.get(name)
        if limit is None:
            unevaluable.append(name)
            continue
        limit = finite_number(name, limit, integer=integer)
        if name == "minimum_profit_factor" and limit < 0:
            raise ValueError("minimum_profit_factor cannot be negative")
        if name == "maximum_drawdown" and not 0 <= limit <= 1:
            raise ValueError("maximum_drawdown must be between 0 and 1")
        if actual is None:
            unevaluable.append(name)
        else:
            (passed if predicate(actual, limit) else failed).append(name)

    min_expectancy = criteria.get("minimum_expectancy_r")
    expectancy_r = evaluation.expectancy_r if expectancy_r is None else expectancy_r
    if min_expectancy is None:
        unevaluable.append("minimum_expectancy_r")
    else:
        min_expectancy = finite_number("minimum_expectancy_r", min_expectancy)
        if expectancy_r is None:
            unevaluable.append("minimum_expectancy_r")
        else:
            expectancy_r = finite_number("expectancy_r", expectancy_r)
            (passed if expectancy_r >= min_expectancy else failed).append("minimum_expectancy_r")

    robustness_required = criteria.get("robustness_required", False)
    if not isinstance(robustness_required, bool):
        raise ValueError("robustness_required must be boolean")
    if robustness_required:
        if robustness_passed is None:
            unevaluable.append("robustness_required")
        elif not isinstance(robustness_passed, bool):
            raise ValueError("robustness_passed must be boolean")
        elif robustness_passed:
            passed.append("robustness_required")
        else:
            failed.append("robustness_required")

    status = "fail" if failed else ("blocked" if unevaluable else "pass")
    return AcceptanceDecision(status, owner, tuple(passed), tuple(failed), tuple(unevaluable))
