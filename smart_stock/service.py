"""Web 与 API 业务服务。"""

from __future__ import annotations

from dataclasses import dataclass

from smart_stock.analyzer import analyze_many
from smart_stock.config import (
    DEFAULT_INDICATOR_CONFIG,
    DEFAULT_STRATEGY_CONFIG,
    IndicatorConfig,
    StrategyConfig,
)
from smart_stock.data import fetch_daily_bars, get_stock_name, normalize_code, search_stock
from smart_stock.indicators import enrich_indicators, latest_indicator_snapshot
from smart_stock.models import AnalysisResult
from smart_stock.serializers import analysis_to_dict, dataframe_to_chart
from smart_stock.strategy import generate_signal


@dataclass
class StockDetail:
    analysis: AnalysisResult
    chart: dict


def get_stock_detail(
    code: str,
    days: int | None = None,
    demo: bool = False,
    indicator_config: IndicatorConfig = DEFAULT_INDICATOR_CONFIG,
    strategy_config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
) -> StockDetail:
    """获取单只股票的完整分析详情与图表数据。"""
    normalized_code = normalize_code(code)
    lookback_days = days or strategy_config.lookback_days

    bars = fetch_daily_bars(normalized_code, days=lookback_days, demo=demo)
    enriched = enrich_indicators(bars, indicator_config)
    indicators = latest_indicator_snapshot(enriched)
    signal, score, reasons = generate_signal(enriched, indicators, strategy_config)

    latest = enriched.iloc[-1]
    analysis = AnalysisResult(
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
        analysis.reasons.insert(0, "当前为演示模式，数据为本地模拟生成")

    return StockDetail(analysis=analysis, chart=dataframe_to_chart(enriched))


def search_stocks(keyword: str, limit: int = 10, demo: bool = False) -> list[dict[str, str]]:
    df = search_stock(keyword, limit=limit, demo=demo)
    return [{"code": str(row["代码"]), "name": str(row["名称"])} for _, row in df.iterrows()]


def batch_analyze(codes: list[str], days: int | None = None, demo: bool = False) -> list[dict]:
    results = analyze_many(codes, days=days, demo=demo)
    payload = [analysis_to_dict(result) for result in results]
    return sorted(payload, key=lambda item: item["score"], reverse=True)


def compare_stocks(codes: list[str], days: int = 120, demo: bool = False) -> list[dict]:
    """对比多只股票区间涨跌幅（归一化起点为 100）。"""
    series_list: list[dict] = []
    lookback_days = max(days, 30)

    for code in codes:
        normalized_code = normalize_code(code)
        if not normalized_code:
            continue
        try:
            bars = fetch_daily_bars(normalized_code, days=lookback_days, demo=demo)
            if bars.empty:
                continue
            base_price = float(bars.iloc[0]["close"])
            if base_price <= 0:
                continue
            normalized = (bars["close"] / base_price * 100).round(4)
            latest_price = float(bars.iloc[-1]["close"])
            series_list.append(
                {
                    "code": normalized_code,
                    "name": get_stock_name(normalized_code, demo=demo),
                    "dates": [item.strftime("%Y-%m-%d") for item in bars["date"]],
                    "values": normalized.tolist(),
                    "return_pct": round((latest_price / base_price - 1) * 100, 2),
                }
            )
        except Exception:
            continue

    return sorted(series_list, key=lambda item: item["return_pct"], reverse=True)


def detail_to_dict(detail: StockDetail) -> dict:
    return {
        "analysis": analysis_to_dict(detail.analysis),
        "chart": detail.chart,
    }
