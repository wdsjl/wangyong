"""筹码分布估算（基于历史成交量价格分布）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from smart_stock.models import ChipSnapshot


def compute_chip_distribution(
    df: pd.DataFrame,
    *,
    lookback: int = 90,
    bins: int = 50,
) -> ChipSnapshot:
    """根据近 N 日 OHLCV 估算筹码分布。"""
    if df.empty or len(df) < 10:
        return ChipSnapshot()

    window = df.tail(lookback).copy()
    price = float(window.iloc[-1]["close"])
    low_min = float(window["low"].min())
    high_max = float(window["high"].max())
    if high_max <= low_min:
        return ChipSnapshot()

    edges = np.linspace(low_min, high_max, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    distribution = np.zeros(bins, dtype=float)

    for _, row in window.iterrows():
        bar_low = float(row["low"])
        bar_high = float(row["high"])
        volume = float(row["volume"])
        if volume <= 0 or bar_high <= bar_low:
            idx = int(np.clip(np.searchsorted(edges, float(row["close"])) - 1, 0, bins - 1))
            distribution[idx] += volume
            continue

        overlap_start = np.searchsorted(edges, bar_low, side="right") - 1
        overlap_end = np.searchsorted(edges, bar_high, side="left")
        overlap_start = max(0, overlap_start)
        overlap_end = min(bins - 1, overlap_end)
        span = overlap_end - overlap_start + 1
        if span <= 0:
            continue
        distribution[overlap_start : overlap_end + 1] += volume / span

    total = distribution.sum()
    if total <= 0:
        return ChipSnapshot()

    avg_cost = float(np.sum(centers * distribution) / total)
    profit_ratio = round(float(distribution[centers <= price].sum() / total * 100), 2)

    peak_idx = int(np.argmax(distribution))
    support_idx = max(0, peak_idx - 1)
    pressure_idx = min(bins - 1, peak_idx + 1)

    return ChipSnapshot(
        avg_cost=round(avg_cost, 2),
        profit_ratio=profit_ratio,
        trapped_ratio=round(100 - profit_ratio, 2),
        support_price=round(float(centers[support_idx]), 2),
        pressure_price=round(float(centers[pressure_idx]), 2),
        peak_price=round(float(centers[peak_idx]), 2),
    )
