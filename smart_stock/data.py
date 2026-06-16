"""A 股行情数据获取。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from smart_stock.sample_data import generate_demo_bars, get_demo_name, search_demo_stocks

try:
    import akshare as ak
except ImportError:  # pragma: no cover
    ak = None


COLUMN_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_change",
    "涨跌额": "change",
    "换手率": "turnover",
}


class DataFetchError(RuntimeError):
    """行情获取失败。"""


def normalize_code(code: str) -> str:
    """标准化股票代码，仅保留数字部分。"""
    return "".join(ch for ch in code.strip() if ch.isdigit())


def search_stock(keyword: str, limit: int = 10, demo: bool = False) -> pd.DataFrame:
    """按代码或名称搜索 A 股。"""
    keyword = keyword.strip()
    if demo:
        return search_demo_stocks(keyword, limit=limit)

    if ak is None:
        raise DataFetchError("未安装 akshare，请执行 pip install akshare")

    stock_list = ak.stock_info_a_code_name()
    stock_list = stock_list.rename(columns={"code": "代码", "name": "名称"})

    if keyword.isdigit():
        mask = stock_list["代码"].str.contains(keyword)
    else:
        mask = stock_list["名称"].str.contains(keyword, na=False)

    return stock_list[mask].head(limit).reset_index(drop=True)


def get_stock_name(code: str, demo: bool = False) -> str:
    """获取股票名称。"""
    code = normalize_code(code)
    if demo:
        return get_demo_name(code)

    try:
        matches = search_stock(code, limit=1, demo=False)
        if not matches.empty:
            return str(matches.iloc[0]["名称"])
    except Exception:
        return code
    return code


def fetch_daily_bars(code: str, days: int = 180, demo: bool = False) -> pd.DataFrame:
    """获取 A 股日线行情（前复权）。"""
    code = normalize_code(code)
    if demo:
        return generate_demo_bars(code, days=days)

    if ak is None:
        raise DataFetchError("未安装 akshare，请执行 pip install akshare")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=max(days * 2, 365))

    raw = ak.stock_zh_a_hist(
        symbol=code,
        period="daily",
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        adjust="qfq",
    )
    if raw.empty:
        raise DataFetchError(f"未获取到股票 {code} 的行情数据")

    df = raw.rename(columns=COLUMN_MAP)
    df["date"] = pd.to_datetime(df["date"])
    numeric_cols = ["open", "close", "high", "low", "volume", "amount"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values("date").tail(days).reset_index(drop=True)


def fetch_daily_bars_safe(
    code: str,
    days: int = 180,
    demo: bool = False,
    allow_fallback: bool = False,
) -> tuple[pd.DataFrame, str]:
    """获取行情，必要时回退到演示数据。

    返回 (dataframe, data_source)，data_source 为 live / demo / demo_fallback。
    """
    if demo:
        return generate_demo_bars(code, days=days), "demo"
    try:
        return fetch_daily_bars(code, days=days, demo=False), "live"
    except Exception:
        if allow_fallback:
            return generate_demo_bars(code, days=days), "demo_fallback"
        raise
