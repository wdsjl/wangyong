"""离线演示数据，用于网络不可用时的本地测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd


STOCK_NAMES = {
    "600519": "贵州茅台",
    "000001": "平安银行",
    "300750": "宁德时代",
    "601318": "中国平安",
}


def get_demo_name(code: str) -> str:
    return STOCK_NAMES.get(code, f"演示股票{code}")


def search_demo_stocks(keyword: str, limit: int = 10) -> pd.DataFrame:
    rows = [
        {"代码": code, "名称": name}
        for code, name in STOCK_NAMES.items()
        if keyword in code or keyword in name
    ]
    return pd.DataFrame(rows).head(limit)


def generate_demo_bars(code: str, days: int = 120, seed: int | None = None) -> pd.DataFrame:
    """基于随机游走生成可复现的演示 K 线。"""
    if seed is None:
        seed = sum(ord(ch) for ch in code)

    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)

    base_price = 50 + (seed % 500)
    returns = rng.normal(0.001, 0.02, size=days)
    close = base_price * np.cumprod(1 + returns)

    open_price = close * (1 + rng.normal(0, 0.005, size=days))
    high = np.maximum(open_price, close) * (1 + rng.uniform(0, 0.02, size=days))
    low = np.minimum(open_price, close) * (1 - rng.uniform(0, 0.02, size=days))
    volume = rng.integers(100_000, 2_000_000, size=days)

    return pd.DataFrame(
        {
            "date": dates,
            "open": np.round(open_price, 2),
            "close": np.round(close, 2),
            "high": np.round(high, 2),
            "low": np.round(low, 2),
            "volume": volume,
            "amount": np.round(volume * close, 2),
        }
    )
