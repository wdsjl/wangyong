"""Web 与 API 业务服务。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from smart_stock.analysis_builder import attach_monitoring
from smart_stock.analyzer import analyze_many
from smart_stock.config import DEFAULT_INDICATOR_CONFIG, IndicatorConfig
from smart_stock.data import (
    DataFetchError,
    attach_live_spot_price,
    fetch_daily_bars_safe,
    fetch_intraday_bars_safe,
    get_stock_name,
    normalize_code,
    search_stock,
)
from smart_stock.indicators import enrich_indicators, latest_indicator_snapshot
from smart_stock.intraday import intraday_to_chart, latest_intraday_snapshot
from smart_stock.models import AnalysisResult
from smart_stock.backtest import BacktestConfig, run_backtest
from smart_stock.llm_insight import generate_insight
from smart_stock.serializers import analysis_to_dict, backtest_to_dict, dataframe_to_chart
from smart_stock.store import get_strategy_settings
from smart_stock.strategy import compute_trade_markers, generate_signal
from smart_stock.strategy_profile import StrategyProfile


@dataclass
class StockDetail:
    analysis: AnalysisResult
    chart: dict
    data_source: str = "live"


def load_strategy_profile() -> StrategyProfile:
    try:
        return StrategyProfile.from_dict(get_strategy_settings())
    except Exception:
        return StrategyProfile()


def get_stock_detail(
    code: str,
    days: int | None = None,
    demo: bool = False,
    allow_fallback: bool = False,
    indicator_config: IndicatorConfig = DEFAULT_INDICATOR_CONFIG,
    profile: StrategyProfile | None = None,
) -> StockDetail:
    """获取单只股票的完整分析详情与图表数据。"""
    active_profile = profile or load_strategy_profile()
    strategy_config = active_profile.strategy
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
    signal, score, reasons = generate_signal(
        enriched,
        indicators,
        strategy_config,
        weights=active_profile.weights,
        use_ama_trend=active_profile.use_ama_trend,
    )

    intraday_bars, _ = fetch_intraday_bars_safe(
        normalized_code,
        period="5m",
        bars=48,
        demo=use_demo_names,
        allow_fallback=allow_fallback,
    )

    latest = enriched.iloc[-1]
    analysis = AnalysisResult(
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
        analysis.reasons.insert(0, "【演示模式】价格为本地模拟数据，非真实行情；要看实盘请去掉 --demo")
    elif data_source == "demo_fallback":
        analysis.reasons.insert(
            0,
            "【网络波动】实盘行情暂时拉取失败，已展示模拟 K 线。请稍后再次点击「分析」刷新实盘数据。",
        )

    analysis = attach_live_spot_price(analysis, normalized_code, data_source)
    analysis = attach_monitoring(
        analysis,
        enriched,
        data_source=data_source,
        demo=use_demo_names,
        profile=active_profile,
        intraday_df=intraday_bars,
    )
    chart = dataframe_to_chart(enriched)
    markers = compute_trade_markers(enriched, profile=active_profile)
    chart["buy_markers"] = markers["buy_markers"]
    chart["sell_markers"] = markers["sell_markers"]
    return StockDetail(analysis=analysis, chart=chart, data_source=data_source)


def get_intraday_detail(
    code: str,
    period: str = "5m",
    bars: int = 48,
    demo: bool = False,
    allow_fallback: bool = False,
) -> dict:
    normalized_code = normalize_code(code)
    bars_df, data_source = fetch_intraday_bars_safe(
        normalized_code,
        period=period,
        bars=bars,
        demo=demo,
        allow_fallback=allow_fallback,
    )
    snapshot = latest_intraday_snapshot(bars_df)
    return {
        "code": normalized_code,
        "period": period,
        "snapshot": asdict(snapshot) if hasattr(snapshot, "__dataclass_fields__") else snapshot,
        "chart": intraday_to_chart(bars_df),
        "data_source": data_source,
    }


def search_stocks(keyword: str, limit: int = 10, demo: bool = False) -> list[dict[str, str]]:
    df = search_stock(keyword, limit=limit, demo=demo)
    return [{"code": str(row["代码"]), "name": str(row["名称"])} for _, row in df.iterrows()]


def batch_analyze(
    codes: list[str],
    days: int | None = None,
    demo: bool = False,
    allow_fallback: bool = False,
) -> list[dict]:
    results = analyze_many(codes, days=days, demo=demo, allow_fallback=allow_fallback)
    payload = [analysis_to_dict(result) for result in results]
    return sorted(payload, key=lambda item: item["score"], reverse=True)


def compare_stocks(
    codes: list[str],
    days: int = 120,
    demo: bool = False,
    allow_fallback: bool = False,
) -> list[dict]:
    """对比多只股票区间涨跌幅（归一化起点为 100）。"""
    series_list: list[dict] = []
    lookback_days = max(days, 30)

    for code in codes:
        normalized_code = normalize_code(code)
        if not normalized_code:
            continue
        try:
            bars, data_source = fetch_daily_bars_safe(
                normalized_code,
                days=lookback_days,
                demo=demo,
                allow_fallback=allow_fallback,
            )
            if bars.empty:
                continue
            base_price = float(bars.iloc[0]["close"])
            if base_price <= 0:
                continue
            normalized = (bars["close"] / base_price * 100).round(4)
            latest_price = float(bars.iloc[-1]["close"])
            use_demo_names = demo or data_source != "live"
            series_list.append(
                {
                    "code": normalized_code,
                    "name": get_stock_name(normalized_code, demo=use_demo_names),
                    "dates": [item.strftime("%Y-%m-%d") for item in bars["date"]],
                    "values": normalized.tolist(),
                    "return_pct": round((latest_price / base_price - 1) * 100, 2),
                    "data_source": data_source,
                }
            )
        except Exception:
            continue

    return sorted(series_list, key=lambda item: item["return_pct"], reverse=True)


def backtest_stock(
    code: str,
    days: int = 180,
    demo: bool = False,
    initial_capital: float = 100_000.0,
) -> dict:
    result = run_backtest(
        code,
        days=days,
        demo=demo,
        backtest_config=BacktestConfig(initial_capital=initial_capital),
    )
    return backtest_to_dict(result)


def stock_insight(code: str, days: int = 120, demo: bool = False, news_limit: int = 5) -> dict:
    return generate_insight(code, days=days, demo=demo, news_limit=news_limit)


def detail_to_dict(detail: StockDetail) -> dict:
    return {
        "analysis": analysis_to_dict(detail.analysis),
        "chart": detail.chart,
        "data_source": detail.data_source,
        "demo_fallback": detail.data_source == "demo_fallback",
    }


def check_live_data_available(*, quick: bool = False) -> bool:
    """探测能否拉取实盘行情。"""
    if quick:
        try:
            from smart_stock.eastmoney import fetch_spot_quote

            return fetch_spot_quote("000815") is not None
        except Exception:
            return False

    try:
        bars, source = fetch_daily_bars_safe("000815", days=30, demo=False, allow_fallback=False)
    except DataFetchError:
        return False
    except Exception:
        return False
    return source == "live" and not bars.empty


def is_akshare_installed() -> bool:
    try:
        import akshare  # noqa: F401
    except ImportError:
        return False
    return True
