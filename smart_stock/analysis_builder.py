"""分析结果组装：指标、盯盘信号、资金流。"""

from __future__ import annotations

import hashlib

import pandas as pd

from smart_stock.chip import compute_chip_distribution
from smart_stock.config import DEFAULT_STRATEGY_CONFIG, StrategyConfig
from smart_stock.fundamentals import fetch_fundamental_snapshot, fetch_northbound_snapshot
from smart_stock.indicators import latest_indicator_snapshot
from smart_stock.models import AnalysisResult, MoneyFlowSnapshot
from smart_stock.signals import compute_monitoring_snapshot


def fetch_money_flow_snapshot(code: str, *, demo: bool, data_source: str) -> MoneyFlowSnapshot:
    if demo or data_source != "live":
        seed = int(hashlib.md5(code.encode()).hexdigest()[:8], 16)
        sign = 1 if seed % 2 == 0 else -1
        amount = (seed % 5000 + 500) * 10000 * sign
        pct = round(((seed % 15) + 1) * sign, 2)
        return MoneyFlowSnapshot(
            main_net_inflow=float(amount),
            large_net_inflow=float(amount * 0.6),
            super_large_net_inflow=float(amount * 0.4),
            main_net_pct=pct,
            source="demo",
        )

    try:
        from smart_stock.eastmoney import fetch_money_flow

        quote = fetch_money_flow(code)
        if quote and quote.main_net_inflow is not None:
            return MoneyFlowSnapshot(
                main_net_inflow=quote.main_net_inflow,
                large_net_inflow=quote.large_net_inflow,
                super_large_net_inflow=quote.super_large_net_inflow,
                main_net_pct=quote.main_net_pct,
                source="live",
            )
    except Exception:
        pass
    return MoneyFlowSnapshot(source="unavailable")


def attach_monitoring(
    analysis: AnalysisResult,
    enriched: pd.DataFrame,
    *,
    data_source: str,
    demo: bool,
    strategy_config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
) -> AnalysisResult:
    indicators = analysis.indicators or latest_indicator_snapshot(enriched)
    money_flow = fetch_money_flow_snapshot(analysis.code, demo=demo, data_source=data_source)
    chip = compute_chip_distribution(enriched)
    fundamentals = fetch_fundamental_snapshot(analysis.code, demo=demo or data_source != "live")
    northbound = fetch_northbound_snapshot(analysis.code, demo=demo or data_source != "live")
    monitoring = compute_monitoring_snapshot(
        enriched,
        indicators,
        money_flow=money_flow,
        strategy_config=strategy_config,
        chip=chip,
        fundamentals=fundamentals,
        northbound=northbound,
    )
    analysis.indicators = indicators
    analysis.monitoring = monitoring

    for alert in monitoring.alerts:
        if alert["level"] in {"strong", "danger"}:
            analysis.reasons.append(f"【预警】{alert['message']}")
            break

    if monitoring.resonance_level == "strong":
        side = "共振看多" if monitoring.resonance_side == "bullish" else "共振看空"
        analysis.reasons.insert(0, f"【{side}】{'、'.join(monitoring.resonance_hits[:3])}")

    if monitoring.momentum_resonance != "无":
        analysis.reasons.insert(0, f"【动量共振】{monitoring.momentum_resonance}")

    return analysis
