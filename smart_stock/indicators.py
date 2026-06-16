"""技术指标计算。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from smart_stock.config import DEFAULT_INDICATOR_CONFIG, IndicatorConfig
from smart_stock.models import IndicatorSnapshot


def add_moving_averages(df: pd.DataFrame, periods: tuple[int, ...]) -> pd.DataFrame:
    result = df.copy()
    for period in periods:
        result[f"ma{period}"] = result["close"].rolling(window=period, min_periods=period).mean()
    return result


def add_volume_ma(df: pd.DataFrame, periods: tuple[int, ...]) -> pd.DataFrame:
    result = df.copy()
    for period in periods:
        result[f"vma{period}"] = result["volume"].rolling(window=period, min_periods=period).mean()
    if "vma5" in result.columns and result["vma5"].notna().any():
        result["volume_ratio"] = result["volume"] / result["vma5"].replace(0, np.nan)
    return result


def add_bias(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    result = df.copy()
    ma_col = f"ma{period}"
    if ma_col not in result.columns:
        result = add_moving_averages(result, (period,))
    ma = result[ma_col]
    result[f"bias{period}"] = (result["close"] - ma) / ma.replace(0, np.nan) * 100
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


def add_obv(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    direction = np.sign(result["close"].diff()).fillna(0)
    result["obv"] = (direction * result["volume"]).fillna(0).cumsum()
    return result


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    result = df.copy()
    prev_close = result["close"].shift(1)
    tr = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - prev_close).abs(),
            (result["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr"] = tr.rolling(window=period, min_periods=period).mean()
    return result


def enrich_indicators(
    df: pd.DataFrame,
    config: IndicatorConfig = DEFAULT_INDICATOR_CONFIG,
) -> pd.DataFrame:
    """为行情数据补充常用技术指标。"""
    enriched = add_moving_averages(df, config.ma_periods)
    enriched = add_volume_ma(enriched, config.vma_periods)
    enriched = add_bias(enriched, config.bias_period)
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
    enriched = add_obv(enriched)
    enriched = add_atr(enriched, config.atr_period)
    return enriched


def latest_indicator_snapshot(df: pd.DataFrame) -> IndicatorSnapshot:
    """提取最新一行的指标快照。"""
    row = df.iloc[-1]
    return IndicatorSnapshot(
        ma5=_safe_float(row.get("ma5")),
        ma10=_safe_float(row.get("ma10")),
        ma20=_safe_float(row.get("ma20")),
        ma60=_safe_float(row.get("ma60")),
        ma120=_safe_float(row.get("ma120")),
        bias20=_safe_float(row.get("bias20")),
        rsi=_safe_float(row.get("rsi")),
        macd=_safe_float(row.get("macd")),
        macd_signal=_safe_float(row.get("macd_signal")),
        macd_hist=_safe_float(row.get("macd_hist")),
        boll_upper=_safe_float(row.get("boll_upper")),
        boll_middle=_safe_float(row.get("boll_middle")),
        boll_lower=_safe_float(row.get("boll_lower")),
        obv=_safe_float(row.get("obv")),
        atr=_safe_float(row.get("atr")),
        vma5=_safe_float(row.get("vma5")),
        vma20=_safe_float(row.get("vma20")),
        volume_ratio=_safe_float(row.get("volume_ratio")),
    )


def _safe_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
