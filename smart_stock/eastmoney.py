"""东方财富行情直连（不经过 requests / akshare）。"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from smart_stock.network import direct_http_get_json

KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
SUGGEST_URL = "https://searchapi.eastmoney.com/api/suggest/get"
SUGGEST_TOKEN = "D43BF5C8E79E06BEE2A6F6E3E8C4B5"

PERIOD_MAP = {"daily": "101", "weekly": "102", "monthly": "103"}
ADJUST_MAP = {"qfq": "1", "hfq": "2", "": "0"}

KLINE_COLUMNS = [
    "日期",
    "开盘",
    "收盘",
    "最高",
    "最低",
    "成交量",
    "成交额",
    "振幅",
    "涨跌幅",
    "涨跌额",
    "换手率",
]


def to_secid(code: str) -> str:
    """将 6 位股票代码转为东方财富 secid。"""
    code = "".join(ch for ch in code if ch.isdigit()).zfill(6)
    market = "1" if code.startswith("6") else "0"
    return f"{market}.{code}"


def fetch_kline(
    code: str,
    start_date: str,
    end_date: str,
    period: str = "daily",
    adjust: str = "qfq",
) -> pd.DataFrame:
    """拉取 K 线原始数据（列名与 akshare stock_zh_a_hist 一致）。"""
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": PERIOD_MAP[period],
        "fqt": ADJUST_MAP[adjust],
        "secid": to_secid(code),
        "beg": start_date,
        "end": end_date,
    }
    payload = direct_http_get_json(KLINE_URL, params=params)
    klines = (payload.get("data") or {}).get("klines") or []
    if not klines:
        return pd.DataFrame()

    frame = pd.DataFrame([row.split(",") for row in klines], columns=KLINE_COLUMNS)
    frame["股票代码"] = "".join(ch for ch in code if ch.isdigit()).zfill(6)
    return frame


def suggest_stocks(keyword: str, limit: int = 10) -> pd.DataFrame:
    """按代码或名称搜索 A 股。"""
    keyword = keyword.strip()
    if not keyword:
        return pd.DataFrame(columns=["代码", "名称"])

    payload = direct_http_get_json(
        SUGGEST_URL,
        params={
            "input": keyword,
            "type": "14",
            "token": SUGGEST_TOKEN,
            "count": str(max(limit * 3, 10)),
        },
    )
    rows = (payload.get("QuotationCodeTable") or {}).get("Data") or []
    matches: list[dict[str, str]] = []
    for row in rows:
        if row.get("Classify") != "AStock":
            continue
        matches.append({"代码": str(row.get("Code", "")), "名称": str(row.get("Name", ""))})
        if len(matches) >= limit:
            break
    return pd.DataFrame(matches, columns=["代码", "名称"])


def get_stock_name(code: str) -> str:
    """根据代码获取股票名称。"""
    code = "".join(ch for ch in code if ch.isdigit()).zfill(6)
    matches = suggest_stocks(code, limit=1)
    if not matches.empty:
        return str(matches.iloc[0]["名称"])
    return code


def fetch_daily_bars(
    code: str,
    start_date: datetime,
    end_date: datetime,
    days: int,
) -> pd.DataFrame:
    """获取日线并裁剪到指定天数。"""
    raw = fetch_kline(
        code=code,
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        period="daily",
        adjust="qfq",
    )
    if raw.empty:
        raise ValueError(f"未获取到股票 {code} 的行情数据")
    return raw.tail(days).reset_index(drop=True)
