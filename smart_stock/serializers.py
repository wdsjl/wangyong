"""API 序列化工具。"""

from __future__ import annotations

from dataclasses import asdict
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from smart_stock.backtest import BacktestResult
from smart_stock.models import AnalysisResult, IndicatorSnapshot, MonitoringSnapshot, Signal


def signal_to_dict(signal: Signal) -> dict[str, str]:
    return {"value": signal.value, "key": signal.name}


def indicator_to_dict(indicators: IndicatorSnapshot | None) -> dict[str, float | None]:
    if indicators is None:
        return {}
    return asdict(indicators)


def monitoring_to_dict(monitoring: MonitoringSnapshot | None) -> dict[str, Any]:
    if monitoring is None:
        return {}
    payload = asdict(monitoring)
    if monitoring.money_flow is not None:
        payload["money_flow"] = asdict(monitoring.money_flow)
    if monitoring.chip is not None:
        payload["chip"] = asdict(monitoring.chip)
    if monitoring.fundamentals is not None:
        payload["fundamentals"] = asdict(monitoring.fundamentals)
    if monitoring.northbound is not None:
        payload["northbound"] = asdict(monitoring.northbound)
    return payload


def analysis_to_dict(result: AnalysisResult) -> dict[str, Any]:
    return {
        "code": result.code,
        "name": result.name,
        "latest_price": result.latest_price,
        "latest_date": result.latest_date,
        "price_label": result.price_label,
        "signal": signal_to_dict(result.signal),
        "score": result.score,
        "reasons": result.reasons,
        "indicators": indicator_to_dict(result.indicators),
        "monitoring": monitoring_to_dict(result.monitoring),
        "risk_note": result.risk_note,
    }


def dataframe_to_chart(df: pd.DataFrame) -> dict[str, list[Any]]:
    """将行情与指标 DataFrame 转为前端图表数据。"""
    chart_columns = [
        "date",
        "open",
        "close",
        "high",
        "low",
        "volume",
        "ma5",
        "ma10",
        "ma20",
        "ma60",
        "ma120",
        "vma5",
        "vma20",
        "volume_ratio",
        "rsi",
        "macd",
        "macd_signal",
        "macd_hist",
        "boll_upper",
        "boll_middle",
        "boll_lower",
        "obv",
        "atr",
        "kdj_k",
        "kdj_d",
        "kdj_j",
        "cci",
        "wr",
        "mfi",
        "adx",
        "plus_di",
        "minus_di",
    ]

    payload: dict[str, list[Any]] = {"dates": []}
    for column in chart_columns[1:]:
        payload[column] = []

    for _, row in df.iterrows():
        payload["dates"].append(row["date"].strftime("%Y-%m-%d"))
        for column in chart_columns[1:]:
            value = row.get(column)
            if value is None or (isinstance(value, float) and np.isnan(value)):
                payload[column].append(None)
            elif column == "volume":
                payload[column].append(int(value))
            else:
                payload[column].append(round(float(value), 4))

    return payload


def backtest_to_dict(result: BacktestResult) -> dict[str, Any]:
    return {
        "code": result.code,
        "name": result.name,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "final_equity": result.final_equity,
        "total_return_pct": result.total_return_pct,
        "benchmark_return_pct": result.benchmark_return_pct,
        "excess_return_pct": result.excess_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "win_rate_pct": result.win_rate_pct,
        "trade_count": result.trade_count,
        "sharpe_ratio": result.sharpe_ratio,
        "equity_curve": result.equity_curve,
        "trades": [asdict(trade) for trade in result.trades],
        "risk_note": result.risk_note,
    }


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    return value
