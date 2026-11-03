"""Deterministic OHLC execution simulator.

This engine deliberately consumes explicit trade intents; it does not infer ICT
signals or invent entry rules. Prices are midpoint OHLC and costs are explicit.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


Direction = Literal["long", "short"]
SameBarPolicy = Literal["stop_first", "target_first", "reject_ambiguous"]


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class TradeIntent:
    trade_id: str
    direction: Direction
    signal_time: datetime
    entry_time: datetime
    entry_price: float
    stop_price: float
    target_price: float
    quantity: float = 1.0


@dataclass(frozen=True)
class ExecutionCosts:
    spread: float = 0.0
    slippage: float = 0.0
    commission_per_unit_per_side: float = 0.0


@dataclass(frozen=True)
class BacktestConfig:
    same_bar_policy: SameBarPolicy = "stop_first"
    costs: ExecutionCosts = ExecutionCosts()


@dataclass(frozen=True)
class TradeResult:
    trade_id: str
    direction: Direction
    entry_time: datetime
    exit_time: datetime
    entry_fill: float
    exit_fill: float
    exit_reason: str
    quantity: float
    gross_pnl: float
    costs: float
    net_pnl: float
    initial_risk: float = 0.0
    r_multiple: float | None = None


def _valid_intent(intent: TradeIntent) -> None:
    if intent.direction not in ("long", "short"):
        raise ValueError("Unsupported direction")
    if intent.quantity <= 0:
        raise ValueError("Quantity must be positive")
    if intent.entry_time < intent.signal_time:
        raise ValueError("Entry cannot precede signal")
    if intent.entry_price <= 0 or intent.stop_price <= 0 or intent.target_price <= 0:
        raise ValueError("Prices must be positive")
    if intent.direction == "long" and not intent.stop_price < intent.entry_price < intent.target_price:
        raise ValueError("Invalid long stop/entry/target ordering")
    if intent.direction == "short" and not intent.target_price < intent.entry_price < intent.stop_price:
        raise ValueError("Invalid short stop/entry/target ordering")


def run_backtest(
    candles: list[Candle],
    intents: list[TradeIntent],
    config: BacktestConfig = BacktestConfig(),
) -> list[TradeResult]:
    """Run one-trade-at-a-time intents against sorted midpoint OHLC bars."""
    if config.costs.spread < 0 or config.costs.slippage < 0 or config.costs.commission_per_unit_per_side < 0:
        raise ValueError("Execution costs cannot be negative")
    if config.same_bar_policy not in ("stop_first", "target_first", "reject_ambiguous"):
        raise ValueError("Unsupported same-bar policy")
    bars = sorted(candles, key=lambda bar: bar.timestamp)
    if any(bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close, bar.high) for bar in bars):
        raise ValueError("Invalid OHLC candle")
    if len({bar.timestamp for bar in bars}) != len(bars):
        raise ValueError("Duplicate candle timestamps")
    results = []
    last_exit_time = None
    for intent in sorted(intents, key=lambda item: (item.entry_time, item.trade_id)):
        _valid_intent(intent)
        if last_exit_time is not None and intent.entry_time <= last_exit_time:
            raise ValueError("Overlapping trade intents are not supported by this single-position engine")
        eligible = [bar for bar in bars if bar.timestamp >= intent.entry_time]
        if not eligible:
            continue
        entry_bar = eligible[0]
        half_spread = config.costs.spread / 2
        slip = config.costs.slippage
        if intent.direction == "long":
            entry_fill = intent.entry_price + half_spread + slip
        else:
            entry_fill = intent.entry_price - half_spread - slip
        exit_bar = None
        exit_mid = None
        reason = None
        for bar in eligible:
            # Entry-bar extremes may have occurred before the entry; never inspect them.
            if bar.timestamp == entry_bar.timestamp:
                continue
            if intent.direction == "long":
                stop_hit = bar.open <= intent.stop_price or bar.low <= intent.stop_price
                target_hit = bar.open >= intent.target_price or bar.high >= intent.target_price
            else:
                stop_hit = bar.open >= intent.stop_price or bar.high >= intent.stop_price
                target_hit = bar.open <= intent.target_price or bar.low <= intent.target_price
            if stop_hit and target_hit:
                if config.same_bar_policy == "reject_ambiguous":
                    raise ValueError(f"Ambiguous stop/target ordering for trade {intent.trade_id}")
                reason = "stop" if config.same_bar_policy == "stop_first" else "target"
            elif stop_hit:
                reason = "stop"
            elif target_hit:
                reason = "target"
            if reason:
                exit_bar = bar
                # A gap through a stop is filled at the worse opening price.
                if reason == "stop":
                    if intent.direction == "long":
                        exit_mid = min(intent.stop_price, bar.open)
                    else:
                        exit_mid = max(intent.stop_price, bar.open)
                else:
                    if intent.direction == "long":
                        exit_mid = max(intent.target_price, bar.open)
                    else:
                        exit_mid = min(intent.target_price, bar.open)
                break
        if exit_bar is None:
            raise ValueError(f"Trade {intent.trade_id} remains open at the end of the dataset")
        if intent.direction == "long":
            exit_fill = exit_mid - half_spread - slip
            gross = (exit_mid - intent.entry_price) * intent.quantity
        else:
            exit_fill = exit_mid + half_spread + slip
            gross = (intent.entry_price - exit_mid) * intent.quantity
        commission = config.costs.commission_per_unit_per_side * intent.quantity * 2
        spread_and_slippage = abs(entry_fill - intent.entry_price) * intent.quantity + abs(exit_fill - exit_mid) * intent.quantity
        total_costs = commission + spread_and_slippage
        last_exit_time = exit_bar.timestamp
        results.append(TradeResult(
            trade_id=intent.trade_id, direction=intent.direction,
            entry_time=entry_bar.timestamp, exit_time=exit_bar.timestamp,
            entry_fill=entry_fill, exit_fill=exit_fill, exit_reason=reason,
            quantity=intent.quantity, gross_pnl=gross,
            costs=total_costs, net_pnl=gross-total_costs,
            initial_risk=abs(intent.entry_price - intent.stop_price) * intent.quantity,
            r_multiple=(gross - total_costs) / (abs(intent.entry_price - intent.stop_price) * intent.quantity),
        ))
    return results
