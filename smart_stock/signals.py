"""盯盘衍生信号：趋势打分、共振、预警。"""

from __future__ import annotations

import pandas as pd

from smart_stock.config import (
    DEFAULT_RESONANCE_CONFIG,
    DEFAULT_STRATEGY_CONFIG,
    ResonanceConfig,
    StrategyConfig,
)
from smart_stock.models import IndicatorSnapshot, MoneyFlowSnapshot, MonitoringSnapshot


def compute_trend_score(price: float, indicators: IndicatorSnapshot) -> tuple[int, str]:
    """均线共振趋势分 0-100。"""
    score = 50
    ma_pairs = [
        (indicators.ma5, 8),
        (indicators.ma10, 8),
        (indicators.ma20, 12),
        (indicators.ma60, 12),
        (indicators.ma120, 10),
    ]
    available = [(ma, weight) for ma, weight in ma_pairs if ma is not None]
    if not available:
        return 50, "震荡"

    above = sum(weight for ma, weight in available if price > ma)
    total = sum(weight for _, weight in available)
    score = int(round(20 + (above / total) * 60))

    if indicators.ma5 and indicators.ma10 and indicators.ma20:
        if indicators.ma5 > indicators.ma10 > indicators.ma20:
            score = min(100, score + 12)
        elif indicators.ma5 < indicators.ma10 < indicators.ma20:
            score = max(0, score - 12)

    if score >= 75:
        label = "强势多头"
    elif score >= 60:
        label = "偏多"
    elif score <= 25:
        label = "强势空头"
    elif score <= 40:
        label = "偏空"
    else:
        label = "震荡"
    return score, label


def _obv_trend(df: pd.DataFrame, window: int = 5) -> str:
    if len(df) < window + 1 or "obv" not in df.columns:
        return "flat"
    recent = df["obv"].tail(window)
    delta = float(recent.iloc[-1] - recent.iloc[0])
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "flat"


def _volume_signal(df: pd.DataFrame, indicators: IndicatorSnapshot) -> str:
    if len(df) < 2:
        return "量能平稳"
    latest = df.iloc[-1]
    ratio = indicators.volume_ratio
    if ratio is None or pd.isna(ratio):
        return "量能平稳"
    if ratio > 1.5 and latest["close"] > latest["open"]:
        return "放量上涨"
    if ratio > 1.5 and latest["close"] < latest["open"]:
        return "放量下跌"
    if ratio > 1.2:
        return "温和放量"
    if ratio < 0.7:
        return "缩量整理"
    return "量能平稳"


def _boll_position(price: float, indicators: IndicatorSnapshot) -> str:
    upper, lower, middle = indicators.boll_upper, indicators.boll_lower, indicators.boll_middle
    if None in (upper, lower, middle):
        return "中轨附近"
    width = upper - lower
    if width <= 0:
        return "中轨附近"
    pos = (price - lower) / width
    if pos >= 0.9:
        return "逼近上轨"
    if pos <= 0.1:
        return "逼近下轨"
    if price > middle:
        return "中轨上方"
    if price < middle:
        return "中轨下方"
    return "中轨附近"


def _detect_macd_bullish_divergence(df: pd.DataFrame, lookback: int = 20) -> bool:
    if len(df) < lookback or "macd_hist" not in df.columns:
        return False
    window = df.tail(lookback)
    price = window["close"]
    hist = window["macd_hist"]
    if price.isna().any() or hist.isna().any():
        return False
    price_low_idx = price.idxmin()
    half = window.iloc[len(window) // 2 :]
    if half.empty:
        return False
    later_price_low = half["close"].min()
    later_hist_at_lows = half.loc[half["close"] == later_price_low, "macd_hist"]
    if later_hist_at_lows.empty:
        return False
    first_hist = float(hist.loc[price_low_idx])
    later_hist = float(later_hist_at_lows.iloc[-1])
    return later_price_low < float(price.loc[price_low_idx]) and later_hist > first_hist


def _detect_macd_bearish_divergence(df: pd.DataFrame, lookback: int = 20) -> bool:
    if len(df) < lookback or "macd_hist" not in df.columns:
        return False
    window = df.tail(lookback)
    price = window["close"]
    hist = window["macd_hist"]
    if price.isna().any() or hist.isna().any():
        return False
    price_high_idx = price.idxmax()
    half = window.iloc[len(window) // 2 :]
    if half.empty:
        return False
    later_price_high = half["close"].max()
    later_hist_at_highs = half.loc[half["close"] == later_price_high, "macd_hist"]
    if later_hist_at_highs.empty:
        return False
    first_hist = float(hist.loc[price_high_idx])
    later_hist = float(later_hist_at_highs.iloc[-1])
    return later_price_high > float(price.loc[price_high_idx]) and later_hist < first_hist


def compute_resonance(
    df: pd.DataFrame,
    indicators: IndicatorSnapshot,
    price: float,
    config: ResonanceConfig = DEFAULT_RESONANCE_CONFIG,
) -> tuple[str, str, list[str], int]:
    """多指标共振：返回 level, side, hits, score。"""
    bullish_hits: list[str] = []
    bearish_hits: list[str] = []

    if indicators.ma5 and indicators.ma10 and indicators.ma20 and indicators.ma5 > indicators.ma10 > indicators.ma20:
        bullish_hits.append("均线多头排列")
    if indicators.ma5 and indicators.ma10 and indicators.ma20 and indicators.ma5 < indicators.ma10 < indicators.ma20:
        bearish_hits.append("均线空头排列")

    if indicators.macd_hist is not None and indicators.macd_hist > 0:
        bullish_hits.append("MACD红柱")
    if indicators.macd_hist is not None and indicators.macd_hist < 0:
        bearish_hits.append("MACD绿柱")

    if indicators.rsi is not None and indicators.rsi < config.rsi_oversold:
        bullish_hits.append(f"RSI超卖({indicators.rsi:.1f})")
    if indicators.rsi is not None and indicators.rsi > config.rsi_overbought:
        bearish_hits.append(f"RSI超买({indicators.rsi:.1f})")

    ratio = indicators.volume_ratio or 0
    if ratio >= config.volume_breakout_ratio and len(df) >= 1 and df.iloc[-1]["close"] > df.iloc[-1]["open"]:
        bullish_hits.append("放量阳线")
    if ratio >= config.volume_breakout_ratio and len(df) >= 1 and df.iloc[-1]["close"] < df.iloc[-1]["open"]:
        bearish_hits.append("放量阴线")

    if _detect_macd_bullish_divergence(df):
        bullish_hits.append("MACD底背离")
    if _detect_macd_bearish_divergence(df):
        bearish_hits.append("MACD顶背离")

    obv = _obv_trend(df)
    if obv == "up" and price >= (indicators.ma20 or price):
        bullish_hits.append("OBV资金流入")
    if obv == "down" and price <= (indicators.ma20 or price):
        bearish_hits.append("OBV资金流出")

    bull_count = len(bullish_hits)
    bear_count = len(bearish_hits)

    if bull_count >= config.strong_min_hits and bull_count > bear_count:
        return "strong", "bullish", bullish_hits, min(100, 50 + bull_count * 10)
    if bear_count >= config.strong_min_hits and bear_count > bull_count:
        return "strong", "bearish", bearish_hits, max(0, 50 - bear_count * 10)
    if bull_count >= config.weak_min_hits and bull_count > bear_count:
        return "weak", "bullish", bullish_hits, min(100, 40 + bull_count * 8)
    if bear_count >= config.weak_min_hits and bear_count > bull_count:
        return "weak", "bearish", bearish_hits, max(0, 60 - bear_count * 8)
    return "none", "neutral", [], 50


def compute_atr_stop_loss(
    price: float,
    indicators: IndicatorSnapshot,
    strategy_config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
) -> float | None:
    if indicators.atr is None or indicators.atr <= 0:
        return None
    return round(price - strategy_config.atr_stop_multiplier * indicators.atr, 2)


def build_alerts(
    df: pd.DataFrame,
    indicators: IndicatorSnapshot,
    price: float,
    resonance_level: str,
    resonance_side: str,
    resonance_hits: list[str],
    money_flow: MoneyFlowSnapshot | None,
    strategy_config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []

    boll_pos = _boll_position(price, indicators)
    if boll_pos == "逼近上轨":
        alerts.append({"level": "warning", "type": "boll", "message": "价格逼近布林上轨，注意回调"})
    if boll_pos == "逼近下轨":
        alerts.append({"level": "info", "type": "boll", "message": "价格逼近布林下轨，关注反弹"})

    stop_loss = compute_atr_stop_loss(price, indicators, strategy_config)
    if stop_loss is not None and price <= stop_loss * 1.01:
        alerts.append(
            {
                "level": "danger",
                "type": "atr",
                "message": f"价格接近 ATR 动态止损位 {stop_loss:.2f}",
            }
        )

    if resonance_level == "strong" and resonance_side == "bullish":
        alerts.append(
            {
                "level": "strong",
                "type": "resonance",
                "message": "多指标强势共振看多：" + "、".join(resonance_hits[:4]),
            }
        )
    elif resonance_level == "strong" and resonance_side == "bearish":
        alerts.append(
            {
                "level": "strong",
                "type": "resonance",
                "message": "多指标强势共振看空：" + "、".join(resonance_hits[:4]),
            }
        )
    elif resonance_level == "weak" and resonance_hits:
        alerts.append(
            {
                "level": "weak",
                "type": "resonance",
                "message": "弱共振信号：" + "、".join(resonance_hits[:3]),
            }
        )

    if money_flow and money_flow.main_net_inflow is not None:
        if money_flow.main_net_inflow > 0 and money_flow.main_net_pct and money_flow.main_net_pct >= 5:
            alerts.append(
                {
                    "level": "info",
                    "type": "money_flow",
                    "message": f"主力净流入 {money_flow.main_net_inflow / 10000:.1f} 万，占比 {money_flow.main_net_pct:.1f}%",
                }
            )
        elif money_flow.main_net_inflow < 0 and money_flow.main_net_pct and money_flow.main_net_pct <= -5:
            alerts.append(
                {
                    "level": "warning",
                    "type": "money_flow",
                    "message": f"主力净流出 {abs(money_flow.main_net_inflow) / 10000:.1f} 万，占比 {abs(money_flow.main_net_pct):.1f}%",
                }
            )

    return alerts


def compute_monitoring_snapshot(
    df: pd.DataFrame,
    indicators: IndicatorSnapshot,
    money_flow: MoneyFlowSnapshot | None = None,
    strategy_config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
    resonance_config: ResonanceConfig = DEFAULT_RESONANCE_CONFIG,
) -> MonitoringSnapshot:
    price = float(df.iloc[-1]["close"])
    trend_score, trend_label = compute_trend_score(price, indicators)
    resonance_level, resonance_side, resonance_hits, resonance_score = compute_resonance(
        df, indicators, price, resonance_config
    )
    stop_loss = compute_atr_stop_loss(price, indicators, strategy_config)

    alerts = build_alerts(
        df,
        indicators,
        price,
        resonance_level,
        resonance_side,
        resonance_hits,
        money_flow,
        strategy_config,
    )

    return MonitoringSnapshot(
        trend_score=trend_score,
        trend_label=trend_label,
        resonance_level=resonance_level,
        resonance_side=resonance_side,
        resonance_hits=resonance_hits,
        resonance_score=resonance_score,
        atr_stop_loss=stop_loss,
        atr_stop_multiplier=strategy_config.atr_stop_multiplier,
        obv_trend=_obv_trend(df),
        volume_signal=_volume_signal(df, indicators),
        boll_position=_boll_position(price, indicators),
        alerts=alerts,
        money_flow=money_flow,
    )
