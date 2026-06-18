"""多因子交易策略与信号生成。"""

from __future__ import annotations

import pandas as pd

from smart_stock.config import DEFAULT_STRATEGY_CONFIG, StrategyConfig
from smart_stock.indicators import latest_indicator_snapshot
from smart_stock.models import IndicatorSnapshot, Signal
from smart_stock.strategy_profile import FactorWeights, StrategyProfile


def score_trend(price: float, indicators: IndicatorSnapshot, *, use_ama: bool = True) -> tuple[float, list[str]]:
    """均线趋势评分。"""
    score = 0.0
    reasons: list[str] = []

    ma_values = [
        ("MA5", indicators.ma5),
        ("MA10", indicators.ma10),
        ("MA20", indicators.ma20),
        ("MA60", indicators.ma60),
    ]
    available = [(name, value) for name, value in ma_values if value is not None]
    if not available:
        return 0.0, reasons

    above_count = sum(1 for _, value in available if price > value)
    ratio = above_count / len(available)
    score += (ratio - 0.5) * 1.2

    if indicators.ma5 and indicators.ma10 and indicators.ma20:
        if indicators.ma5 > indicators.ma10 > indicators.ma20:
            score += 0.35
            reasons.append("短期均线呈多头排列")
        elif indicators.ma5 < indicators.ma10 < indicators.ma20:
            score -= 0.35
            reasons.append("短期均线呈空头排列")

    if price > (indicators.ma20 or price):
        reasons.append("价格站上 20 日均线")
    elif price < (indicators.ma20 or price):
        reasons.append("价格跌破 20 日均线")

    if use_ama and indicators.ama is not None:
        if price > indicators.ama:
            score += 0.2
            reasons.append("价格站上 AMA 自适应均线")
        else:
            score -= 0.2
            reasons.append("价格跌破 AMA 自适应均线")

    return score, reasons


def score_momentum(indicators: IndicatorSnapshot) -> tuple[float, list[str]]:
    """动量指标评分。"""
    score = 0.0
    reasons: list[str] = []

    if indicators.rsi is not None:
        if indicators.rsi < 30:
            score += 0.45
            reasons.append(f"RSI={indicators.rsi:.1f}，处于超卖区")
        elif indicators.rsi > 70:
            score -= 0.45
            reasons.append(f"RSI={indicators.rsi:.1f}，处于超买区")
        elif indicators.rsi < 45:
            score += 0.1
        elif indicators.rsi > 55:
            score -= 0.1

    if indicators.macd_hist is not None:
        if indicators.macd_hist > 0:
            score += 0.25
            reasons.append("MACD 柱状图为正，动能偏强")
        else:
            score -= 0.25
            reasons.append("MACD 柱状图为负，动能偏弱")

    if indicators.macd is not None and indicators.macd_signal is not None:
        if indicators.macd > indicators.macd_signal:
            score += 0.15
            reasons.append("MACD 金叉区域")
        else:
            score -= 0.15
            reasons.append("MACD 死叉区域")

    if indicators.kdj_k is not None and indicators.kdj_d is not None:
        if indicators.kdj_k < 20 and indicators.kdj_k > indicators.kdj_d:
            score += 0.2
            reasons.append(f"KDJ 低位金叉(K={indicators.kdj_k:.1f})")
        elif indicators.kdj_k > 80 and indicators.kdj_k < indicators.kdj_d:
            score -= 0.2
            reasons.append(f"KDJ 高位死叉(K={indicators.kdj_k:.1f})")

    if indicators.cci is not None:
        if indicators.cci < -100:
            score += 0.15
            reasons.append(f"CCI={indicators.cci:.1f} 超卖")
        elif indicators.cci > 100:
            score -= 0.15
            reasons.append(f"CCI={indicators.cci:.1f} 超买")

    if indicators.wr is not None:
        if indicators.wr < -80:
            score += 0.1
            reasons.append(f"WR={indicators.wr:.1f} 超卖")
        elif indicators.wr > -20:
            score -= 0.1
            reasons.append(f"WR={indicators.wr:.1f} 超买")

    if indicators.mfi is not None:
        if indicators.mfi < 20:
            score += 0.15
            reasons.append(f"MFI={indicators.mfi:.1f} 资金流出衰竭")
        elif indicators.mfi > 80:
            score -= 0.15
            reasons.append(f"MFI={indicators.mfi:.1f} 资金过热")

    return score, reasons


def score_volatility(price: float, indicators: IndicatorSnapshot) -> tuple[float, list[str]]:
    """波动区间评分。"""
    score = 0.0
    reasons: list[str] = []

    if None in (indicators.boll_upper, indicators.boll_lower, indicators.boll_middle):
        return score, reasons

    upper = indicators.boll_upper
    lower = indicators.boll_lower
    middle = indicators.boll_middle
    assert upper is not None and lower is not None and middle is not None

    band_width = upper - lower
    if band_width <= 0:
        return score, reasons

    position = (price - lower) / band_width
    if position < 0.2:
        score += 0.2
        reasons.append("价格接近布林带下轨，存在反弹空间")
    elif position > 0.8:
        score -= 0.2
        reasons.append("价格接近布林带上轨，注意回调风险")

    if price > middle:
        score += 0.05
    else:
        score -= 0.05

    return score, reasons


def score_volume(df: pd.DataFrame, indicators: IndicatorSnapshot) -> tuple[float, list[str]]:
    """成交量变化评分。"""
    if len(df) < 6 or "volume" not in df.columns:
        return 0.0, []

    latest = df.iloc[-1]
    ratio = indicators.volume_ratio
    if ratio is None or pd.isna(ratio):
        avg_volume = df["volume"].tail(6).iloc[:-1].mean()
        if avg_volume <= 0 or pd.isna(avg_volume):
            return 0.0, []
        ratio = latest["volume"] / avg_volume

    if ratio > 1.5 and latest["close"] > latest["open"]:
        return 0.25, ["放量上涨，资金关注度提升"]
    if ratio > 1.5 and latest["close"] < latest["open"]:
        return -0.25, ["放量下跌，抛压加重"]
    if ratio > 1.2 and latest["close"] > latest["open"]:
        return 0.1, ["温和放量上攻"]
    if ratio < 0.7:
        return -0.05, ["成交量萎缩，趋势动能不足"]
    return 0.0, []


def score_obv(df: pd.DataFrame, price: float, indicators: IndicatorSnapshot) -> tuple[float, list[str]]:
    """OBV 能量潮评分。"""
    if len(df) < 6 or "obv" not in df.columns:
        return 0.0, []

    recent = df["obv"].tail(5)
    delta = float(recent.iloc[-1] - recent.iloc[0])
    score = 0.0
    reasons: list[str] = []

    if delta > 0 and price >= (indicators.ma20 or price):
        score += 0.15
        reasons.append("OBV 上行，资金流入")
    elif delta < 0 and price <= (indicators.ma20 or price):
        score -= 0.15
        reasons.append("OBV 下行，资金流出")

    if len(df) >= 10:
        price_up = price > float(df.iloc[-10]["close"])
        obv_up = float(df.iloc[-1]["obv"]) > float(df.iloc[-10]["obv"])
        if price_up and not obv_up:
            score -= 0.1
            reasons.append("价涨 OBV 不涨，警惕顶背离")
        if not price_up and obv_up:
            score += 0.1
            reasons.append("价跌 OBV 不跌，或有底部吸筹")

    return score, reasons


def generate_signal(
    df: pd.DataFrame,
    indicators: IndicatorSnapshot,
    config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
    weights: FactorWeights | None = None,
    use_ama_trend: bool = True,
) -> tuple[Signal, float, list[str]]:
    """综合评分并输出交易信号。"""
    price = float(df.iloc[-1]["close"])
    factor_weights = (weights or FactorWeights()).clamp()
    total_score = 0.0
    reasons: list[str] = []

    components = [
        (score_trend(price, indicators, use_ama=use_ama_trend), factor_weights.trend),
        (score_momentum(indicators), factor_weights.momentum),
        (score_volatility(price, indicators), factor_weights.volatility),
        (score_volume(df, indicators), factor_weights.volume),
        (score_obv(df, price, indicators), factor_weights.obv),
    ]

    for (partial_score, partial_reasons), weight in components:
        total_score += partial_score * weight
        reasons.extend(partial_reasons)

    if total_score >= config.buy_threshold + 0.4:
        signal = Signal.STRONG_BUY
    elif total_score >= config.buy_threshold:
        signal = Signal.BUY
    elif total_score <= config.sell_threshold - 0.4:
        signal = Signal.STRONG_SELL
    elif total_score <= config.sell_threshold:
        signal = Signal.SELL
    else:
        signal = Signal.HOLD
        reasons.append("多空因素交织，建议继续观望")

    if indicators.adx is not None and indicators.adx < config.adx_range_threshold:
        if signal in {Signal.BUY, Signal.STRONG_BUY, Signal.SELL, Signal.STRONG_SELL}:
            signal = Signal.HOLD
            reasons.append(f"ADX={indicators.adx:.1f}<20，震荡市屏蔽短线信号")
    elif indicators.adx is not None and indicators.adx >= config.adx_trend_threshold:
        reasons.append(f"ADX={indicators.adx:.1f}≥25，趋势行情")

    return signal, round(total_score, 3), reasons


def compute_trade_markers(
    enriched: pd.DataFrame,
    strategy_config: StrategyConfig = DEFAULT_STRATEGY_CONFIG,
    profile: StrategyProfile | None = None,
    warmup_days: int = 60,
) -> dict[str, list[dict[str, float | str]]]:
    """根据策略信号生成 K 线买卖点标记（信号由观望转为买入/卖出时触发）。"""
    buy_markers: list[dict[str, float | str]] = []
    sell_markers: list[dict[str, float | str]] = []

    if len(enriched) <= warmup_days:
        return {"buy_markers": buy_markers, "sell_markers": sell_markers}

    active_profile = profile or StrategyProfile(strategy=strategy_config)
    prev_signal: Signal | None = None
    buy_set = {Signal.BUY, Signal.STRONG_BUY}
    sell_set = {Signal.SELL, Signal.STRONG_SELL}

    for index in range(warmup_days, len(enriched)):
        window = enriched.iloc[: index + 1]
        row = enriched.iloc[index]
        indicators = latest_indicator_snapshot(window)
        signal, score, _ = generate_signal(
            window,
            indicators,
            active_profile.strategy,
            weights=active_profile.weights,
            use_ama_trend=active_profile.use_ama_trend,
        )

        if signal in buy_set and (prev_signal is None or prev_signal not in buy_set):
            buy_markers.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "price": round(float(row["close"]), 2),
                    "signal": signal.value,
                    "score": round(score, 3),
                }
            )
        elif signal in sell_set and (prev_signal is None or prev_signal not in sell_set):
            sell_markers.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "price": round(float(row["close"]), 2),
                    "signal": signal.value,
                    "score": round(score, 3),
                }
            )
        prev_signal = signal

    return {"buy_markers": buy_markers, "sell_markers": sell_markers}
