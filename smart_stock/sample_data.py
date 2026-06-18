"""离线演示数据，用于网络不可用时的本地测试。"""

from __future__ import annotations

import numpy as np
import pandas as pd


STOCK_NAMES = {
    "600519": "贵州茅台",
    "000001": "平安银行",
    "000815": "美利云",
    "300750": "宁德时代",
    "601318": "中国平安",
}

# 演示模式参考价（量级接近真实股价，仅供离线演示，非实时行情）
STOCK_BASE_PRICES = {
    "600519": 1450.0,
    "000001": 11.0,
    "000815": 15.5,
    "300750": 200.0,
    "601318": 45.0,
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
    """基于随机游走生成可复现的演示 K 线（非真实行情）。"""
    if seed is None:
        seed = sum(ord(ch) for ch in code)

    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)

    base_price = STOCK_BASE_PRICES.get(code, 50 + (seed % 500))
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


def generate_demo_intraday(code: str, period: str = "5m", bars: int = 48, seed: int | None = None) -> pd.DataFrame:
    """生成演示分时 K 线。"""
    if seed is None:
        seed = sum(ord(ch) for ch in f"{code}:{period}")

    rng = np.random.default_rng(seed)
    base_price = STOCK_BASE_PRICES.get(code, 50 + (seed % 500))
    minutes_per_bar = int("".join(ch for ch in period if ch.isdigit()) or "5")

    end = pd.Timestamp.now().replace(second=0, microsecond=0)
    start_minute = end - pd.Timedelta(minutes=minutes_per_bar * (bars - 1))
    dates = pd.date_range(start=start_minute, end=end, freq=f"{minutes_per_bar}min")

    returns = rng.normal(0, 0.0015, size=len(dates))
    close = base_price * np.cumprod(1 + returns)
    open_price = close * (1 + rng.normal(0, 0.0008, size=len(dates)))
    high = np.maximum(open_price, close) * (1 + rng.uniform(0, 0.002, size=len(dates)))
    low = np.minimum(open_price, close) * (1 - rng.uniform(0, 0.002, size=len(dates)))
    volume = rng.integers(5_000, 120_000, size=len(dates))

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
