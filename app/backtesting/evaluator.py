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
