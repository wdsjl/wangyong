"""波动率恐慌指数（VIX 代理）。"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from smart_stock.models import VixSnapshot


def compute_vix_proxy(df: pd.DataFrame, window: int = 20) -> VixSnapshot:
    """基于已实现波动率构造 0-100 恐慌指数（个股/指数通用）。"""
    if len(df) < window + 1 or "close" not in df.columns:
        return VixSnapshot(source="unavailable")

    returns = df["close"].pct_change().dropna()
    if len(returns) < window:
        return VixSnapshot(source="unavailable")

    recent = returns.tail(window)
    realized = float(recent.std() * math.sqrt(252) * 100)
    if np.isnan(realized):
        return VixSnapshot(source="unavailable")

    # 将年化波动率映射到恐慌指数：10%→20，30%→50，50%→80
    index_value = int(round(np.clip((realized - 10) / 40 * 70 + 20, 5, 95)))

    if index_value >= 70:
        label = "高恐慌"
    elif index_value >= 45:
        label = "中性偏谨慎"
    elif index_value >= 25:
        label = "中性"
    else:
        label = "低恐慌"

    prev_window = returns.tail(window * 2).head(window)
    prev_realized = float(prev_window.std() * math.sqrt(252) * 100) if len(prev_window) >= window else realized
    if realized > prev_realized * 1.08:
        trend = "上升"
    elif realized < prev_realized * 0.92:
        trend = "下降"
    else:
        trend = "平稳"

    return VixSnapshot(
        index_value=index_value,
        realized_vol=round(realized, 2),
        label=label,
        trend=trend,
        source="computed",
    )
