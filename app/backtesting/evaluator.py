"""Transparent metrics for deterministic backtest trade ledgers."""
from dataclasses import dataclass
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
    max_drawdown: float
    equity_curve: tuple[float, ...]


def evaluate_trades(trades: Sequence[TradeResult], initial_equity: float) -> Evaluation:
    if initial_equity <= 0:
        raise ValueError("Initial equity must be positive")
    ordered = sorted(trades, key=lambda trade: (trade.exit_time, trade.trade_id))
    pnls = [float(trade.net_pnl) for trade in ordered]
    wins = sum(pnl > 0 for pnl in pnls)
    losses = sum(pnl < 0 for pnl in pnls)
    breakeven = len(pnls) - wins - losses
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    equity = initial_equity
    peak = initial_equity
    max_drawdown = 0.0
    curve = [equity]
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
        curve.append(equity)
    return Evaluation(
        trade_count=len(pnls), wins=wins, losses=losses, breakeven=breakeven,
        win_rate=(wins / len(pnls)) if pnls else None,
        gross_profit=gross_profit, gross_loss=gross_loss,
        profit_factor=(gross_profit / gross_loss) if gross_loss else (None if not gross_profit else float("inf")),
        net_profit=sum(pnls),
        average_trade_pnl=(sum(pnls) / len(pnls)) if pnls else None,
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
    """Evaluate predeclared gates; missing evidence blocks rather than passes."""
    owner = criteria.get("criteria_owner", "research_default")
    if owner not in {"user", "central_policy", "research_default"}:
        raise ValueError("Unknown acceptance criteria owner")
    passed, failed, unevaluable = [], [], []

    checks = [
        ("minimum_trades", evaluation.trade_count, lambda actual, limit: actual >= limit),
        ("minimum_profit_factor", evaluation.profit_factor, lambda actual, limit: actual is not None and actual >= limit),
        ("maximum_drawdown", evaluation.max_drawdown, lambda actual, limit: actual <= limit),
    ]
    for name, actual, predicate in checks:
        limit = criteria.get(name)
        if limit is None or actual is None:
            unevaluable.append(name)
        elif predicate(actual, limit):
            passed.append(name)
        else:
            failed.append(name)

    min_expectancy = criteria.get("minimum_expectancy_r")
    if min_expectancy is None or expectancy_r is None:
        unevaluable.append("minimum_expectancy_r")
    elif expectancy_r >= min_expectancy:
        passed.append("minimum_expectancy_r")
    else:
        failed.append("minimum_expectancy_r")

    if criteria.get("robustness_required", False):
        if robustness_passed is None:
            unevaluable.append("robustness_required")
        elif robustness_passed:
            passed.append("robustness_required")
        else:
            failed.append("robustness_required")

    status = "fail" if failed else ("blocked" if unevaluable else "pass")
    return AcceptanceDecision(status, owner, tuple(passed), tuple(failed), tuple(unevaluable))
