"""技术指标计算。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from smart_stock.config import IndicatorConfig, DEFAULT_INDICATOR_CONFIG
from smart_stock.models import IndicatorSnapshot


def add_moving_averages(df: pd.DataFrame, periods: tuple[int, ...]) -> pd.DataFrame:
    result = df.copy()
    for period in periods:
        result[f"ma{period}"] = result["close"].rolling(window=period, min_periods=period).mean()
    return result


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    result = df.copy()
    delta = result["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result["rsi"] = 100 - (100 / (1 + rs))
    return result


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    result = df.copy()
    ema_fast = result["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = result["close"].ewm(span=slow, adjust=False).mean()
    result["macd"] = ema_fast - ema_slow
    result["macd_signal"] = result["macd"].ewm(span=signal, adjust=False).mean()
    result["macd_hist"] = result["macd"] - result["macd_signal"]
    return result


def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    result = df.copy()
    middle = result["close"].rolling(window=period, min_periods=period).mean()
    rolling_std = result["close"].rolling(window=period, min_periods=period).std()
    result["boll_middle"] = middle
    result["boll_upper"] = middle + std * rolling_std
    result["boll_lower"] = middle - std * rolling_std
    return result


def enrich_indicators(
    df: pd.DataFrame,
    config: IndicatorConfig = DEFAULT_INDICATOR_CONFIG,
) -> pd.DataFrame:
    """为行情数据补充常用技术指标。"""
    enriched = add_moving_averages(df, config.ma_periods)
    enriched = add_rsi(enriched, config.rsi_period)
    enriched = add_macd(
        enriched,
        fast=config.macd_fast,
        slow=config.macd_slow,
        signal=config.macd_signal,
    )
    enriched = add_bollinger_bands(
        enriched,
        period=config.boll_period,
        std=config.boll_std,
    )
    return enriched


def latest_indicator_snapshot(df: pd.DataFrame) -> IndicatorSnapshot:
    """提取最新一行的指标快照。"""
    row = df.iloc[-1]
    return IndicatorSnapshot(
        ma5=_safe_float(row.get("ma5")),
        ma10=_safe_float(row.get("ma10")),
        ma20=_safe_float(row.get("ma20")),
        ma60=_safe_float(row.get("ma60")),
        rsi=_safe_float(row.get("rsi")),
        macd=_safe_float(row.get("macd")),
        macd_signal=_safe_float(row.get("macd_signal")),
        macd_hist=_safe_float(row.get("macd_hist")),
        boll_upper=_safe_float(row.get("boll_upper")),
        boll_middle=_safe_float(row.get("boll_middle")),
        boll_lower=_safe_float(row.get("boll_lower")),
    )


def _safe_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
