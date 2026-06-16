"""分析编排入口。"""

from __future__ import annotations

from smart_stock.config import (
    DEFAULT_INDICATOR_CONFIG,
    DEFAULT_STRATEGY_CONFIG,
    IndicatorConfig,
    StrategyConfig,
)
from smart_stock.data import fetch_daily_bars, get_stock_name, normalize_code, search_stock
from smart_stock.indicators import enrich_indicators, latest_indicator_snapshot
from smart_stock.models import AnalysisResult, Signal
from smart_stock.strategy import generate_signal


def analyze_stock(
    code: str,
    days: int | None = None,
    demo: bool = False,
    indicator_config: IndicatorConfig = DEFAULT_INDICATOR_CONFIG,
    strategy_config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
) -> AnalysisResult:
    """对单只股票执行智能分析。"""
    normalized_code = normalize_code(code)
    lookback_days = days or strategy_config.lookback_days

    bars = fetch_daily_bars(normalized_code, days=lookback_days, demo=demo)
    enriched = enrich_indicators(bars, indicator_config)
    indicators = latest_indicator_snapshot(enriched)
    signal, score, reasons = generate_signal(enriched, indicators, strategy_config)

    latest = enriched.iloc[-1]
    result = AnalysisResult(
        code=normalized_code,
        name=get_stock_name(normalized_code, demo=demo),
        latest_price=float(latest["close"]),
        latest_date=latest["date"].strftime("%Y-%m-%d"),
        signal=signal,
        score=score,
        reasons=reasons,
        indicators=indicators,
    )
    if demo:
        result.reasons.insert(0, "【演示模式】价格为本地模拟数据，非真实行情；要看实盘请去掉 --demo")
    return result


def analyze_many(codes: list[str], days: int | None = None, demo: bool = False) -> list[AnalysisResult]:
    """批量分析多只股票。"""
    results: list[AnalysisResult] = []
    for code in codes:
        try:
            results.append(analyze_stock(code, days=days, demo=demo))
        except Exception as exc:  # noqa: BLE001 - 批量分析需要跳过失败项
            results.append(
                AnalysisResult(
                    code=normalize_code(code),
                    name=get_stock_name(code, demo=demo),
                    latest_price=0.0,
                    latest_date="-",
                    signal=Signal.HOLD,
                    score=0.0,
                    reasons=[f"分析失败: {exc}"],
                )
            )
    return results


__all__ = ["analyze_stock", "analyze_many", "search_stock"]
