"""分析编排入口。"""

from __future__ import annotations

from smart_stock.analysis_builder import attach_monitoring
from smart_stock.config import (
    DEFAULT_INDICATOR_CONFIG,
    DEFAULT_STRATEGY_CONFIG,
    IndicatorConfig,
    StrategyConfig,
)
from smart_stock.data import (
    DataFetchError,
    attach_live_spot_price,
    fetch_daily_bars_safe,
    get_stock_name,
    normalize_code,
    search_stock,
)
from smart_stock.indicators import enrich_indicators, latest_indicator_snapshot
from smart_stock.models import AnalysisResult, Signal
from smart_stock.strategy import generate_signal


def analyze_stock(
    code: str,
    days: int | None = None,
    demo: bool = False,
    allow_fallback: bool = False,
    indicator_config: IndicatorConfig = DEFAULT_INDICATOR_CONFIG,
    strategy_config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
) -> AnalysisResult:
    """对单只股票执行智能分析。"""
    normalized_code = normalize_code(code)
    lookback_days = days or strategy_config.lookback_days

    bars, data_source = fetch_daily_bars_safe(
        normalized_code,
        days=lookback_days,
        demo=demo,
        allow_fallback=allow_fallback,
    )
    use_demo_names = demo or data_source != "live"
    enriched = enrich_indicators(bars, indicator_config)
    indicators = latest_indicator_snapshot(enriched)
    signal, score, reasons = generate_signal(enriched, indicators, strategy_config)

    latest = enriched.iloc[-1]
    result = AnalysisResult(
        code=normalized_code,
        name=get_stock_name(normalized_code, demo=use_demo_names),
        latest_price=float(latest["close"]),
        latest_date=latest["date"].strftime("%Y-%m-%d"),
        signal=signal,
        score=score,
        reasons=reasons,
        indicators=indicators,
    )
    if data_source == "demo":
        result.reasons.insert(0, "【演示模式】价格为本地模拟数据，非真实行情；要看实盘请去掉 --demo")
    elif data_source == "demo_fallback":
        result.reasons.insert(
            0,
            "【网络波动】实盘行情暂时拉取失败，已展示模拟 K 线。请稍后重试 analyze 命令刷新实盘数据。",
        )
    result = attach_live_spot_price(result, normalized_code, data_source)
    return attach_monitoring(
        result,
        enriched,
        data_source=data_source,
        demo=use_demo_names,
        strategy_config=strategy_config,
    )


def analyze_many(
    codes: list[str],
    days: int | None = None,
    demo: bool = False,
    allow_fallback: bool = False,
) -> list[AnalysisResult]:
    """批量分析多只股票。"""
    results: list[AnalysisResult] = []
    for code in codes:
        try:
            results.append(
                analyze_stock(code, days=days, demo=demo, allow_fallback=allow_fallback)
            )
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
