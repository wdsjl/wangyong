"""策略回测与收益统计。"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from smart_stock.config import (
    DEFAULT_INDICATOR_CONFIG,
    DEFAULT_STRATEGY_CONFIG,
    IndicatorConfig,
    StrategyConfig,
)
from smart_stock.data import fetch_daily_bars, get_stock_name, normalize_code
from smart_stock.indicators import enrich_indicators, latest_indicator_snapshot
from smart_stock.models import Signal
from smart_stock.strategy import generate_signal


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0005
    position_ratio: float = 1.0
    lot_size: int = 100
    warmup_days: int = 60


@dataclass
class TradeRecord:
    date: str
    action: str
    price: float
    shares: int
    amount: float
    signal: str
    score: float


@dataclass
class BacktestResult:
    code: str
    name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    total_return_pct: float
    benchmark_return_pct: float
    excess_return_pct: float
    max_drawdown_pct: float
    win_rate_pct: float
    trade_count: int
    sharpe_ratio: float | None
    equity_curve: list[dict] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)
    risk_note: str = "回测结果基于历史数据模拟，不代表未来收益。"


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    rolling_max = equity.cummax()
    drawdown = equity / rolling_max - 1
    return float(drawdown.min() * 100)


def _sharpe_ratio(returns: pd.Series) -> float | None:
    if len(returns) < 2:
        return None
    std = returns.std()
    if std == 0 or np.isnan(std):
        return None
    return float((returns.mean() / std) * np.sqrt(252))


def _calc_win_rate(trades: list[TradeRecord]) -> float:
    if len(trades) < 2:
        return 0.0
    profits: list[float] = []
    buy_price: float | None = None
    for trade in trades:
        if trade.action == "buy":
            buy_price = trade.price
        elif trade.action == "sell" and buy_price is not None:
            profits.append(trade.price - buy_price)
            buy_price = None
    if not profits:
        return 0.0
    wins = sum(1 for profit in profits if profit > 0)
    return round(wins / len(profits) * 100, 2)


def run_backtest(
    code: str,
    days: int = 180,
    demo: bool = False,
    backtest_config: BacktestConfig = BacktestConfig(),
    indicator_config: IndicatorConfig = DEFAULT_INDICATOR_CONFIG,
    strategy_config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
) -> BacktestResult:
    """基于多因子信号进行全仓买卖回测。"""
    normalized_code = normalize_code(code)
    lookback_days = max(days, backtest_config.warmup_days + 20)
    bars = fetch_daily_bars(normalized_code, days=lookback_days, demo=demo)
    enriched = enrich_indicators(bars, indicator_config)

    cash = backtest_config.initial_capital
    shares = 0
    trades: list[TradeRecord] = []
    equity_rows: list[dict] = []

    warmup = backtest_config.warmup_days
    if len(enriched) <= warmup:
        raise ValueError("历史数据不足以完成回测")

    benchmark_start = float(enriched.iloc[warmup]["close"])
    prev_equity = backtest_config.initial_capital

    for index in range(warmup, len(enriched)):
        window = enriched.iloc[: index + 1]
        row = enriched.iloc[index]
        indicators = latest_indicator_snapshot(window)
        signal, score, _ = generate_signal(window, indicators, strategy_config)
        price = float(row["close"])
        trade_date = row["date"].strftime("%Y-%m-%d")

        if signal in (Signal.BUY, Signal.STRONG_BUY) and shares == 0 and cash > 0:
            invest = cash * backtest_config.position_ratio
            buy_price = price * (1 + backtest_config.slippage_rate)
            commission = invest * backtest_config.commission_rate
            affordable = invest - commission
            lot_shares = int(affordable / buy_price / backtest_config.lot_size) * backtest_config.lot_size
            if lot_shares > 0:
                amount = lot_shares * buy_price + commission
                cash -= amount
                shares = lot_shares
                trades.append(
                    TradeRecord(
                        date=trade_date,
                        action="buy",
                        price=round(buy_price, 2),
                        shares=lot_shares,
                        amount=round(amount, 2),
                        signal=signal.value,
                        score=score,
                    )
                )
        elif signal in (Signal.SELL, Signal.STRONG_SELL) and shares > 0:
            sell_price = price * (1 - backtest_config.slippage_rate)
            gross = shares * sell_price
            commission = gross * backtest_config.commission_rate
            cash += gross - commission
            trades.append(
                TradeRecord(
                    date=trade_date,
                    action="sell",
                    price=round(sell_price, 2),
                    shares=shares,
                    amount=round(gross - commission, 2),
                    signal=signal.value,
                    score=score,
                )
            )
            shares = 0

        equity = cash + shares * price
        benchmark_equity = backtest_config.initial_capital * (price / benchmark_start)
        daily_return = 0.0 if prev_equity == 0 else (equity / prev_equity - 1)
        equity_rows.append(
            {
                "date": trade_date,
                "equity": round(equity, 2),
                "benchmark": round(benchmark_equity, 2),
                "daily_return": round(daily_return, 6),
            }
        )
        prev_equity = equity

    final_equity = equity_rows[-1]["equity"]
    benchmark_final = equity_rows[-1]["benchmark"]
    total_return_pct = round((final_equity / backtest_config.initial_capital - 1) * 100, 2)
    benchmark_return_pct = round((benchmark_final / backtest_config.initial_capital - 1) * 100, 2)
    returns = pd.Series([row["daily_return"] for row in equity_rows])

    return BacktestResult(
        code=normalized_code,
        name=get_stock_name(normalized_code, demo=demo),
        start_date=equity_rows[0]["date"],
        end_date=equity_rows[-1]["date"],
        initial_capital=backtest_config.initial_capital,
        final_equity=final_equity,
        total_return_pct=total_return_pct,
        benchmark_return_pct=benchmark_return_pct,
        excess_return_pct=round(total_return_pct - benchmark_return_pct, 2),
        max_drawdown_pct=round(_max_drawdown(pd.Series([row["equity"] for row in equity_rows])), 2),
        win_rate_pct=_calc_win_rate(trades),
        trade_count=len(trades),
        sharpe_ratio=_sharpe_ratio(returns),
        equity_curve=equity_rows,
        trades=trades,
    )
