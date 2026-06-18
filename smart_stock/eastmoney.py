"""东方财富行情直连（不经过 requests / akshare）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from smart_stock.network import direct_http_get_json

KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
SPOT_URL = "https://push2.eastmoney.com/api/qt/stock/get"
SUGGEST_URL = "https://searchapi.eastmoney.com/api/suggest/get"
SUGGEST_TOKEN = "D43BF5C8E79E06BEE2A6F6E3E8C4B5"

PERIOD_MAP = {
    "daily": "101",
    "weekly": "102",
    "monthly": "103",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "60m": "60",
}
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


@dataclass
class SpotQuote:
    code: str
    name: str
    price: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None
    main_net_inflow: float | None = None
    large_net_inflow: float | None = None
    super_large_net_inflow: float | None = None
    main_net_pct: float | None = None


def _parse_number(value: object) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def fetch_spot_quote(code: str) -> SpotQuote | None:
    """拉取东方财富实时报价。"""
    normalized_code = "".join(ch for ch in code if ch.isdigit()).zfill(6)
    payload = direct_http_get_json(
        SPOT_URL,
        params={
            "fltt": "2",
            "invt": "2",
            "fields": "f43,f44,f45,f46,f57,f58,f60,f169,f170,f62,f66,f69,f184",
            "secid": to_secid(normalized_code),
        },
    )
    data = payload.get("data") or {}
    price = _parse_number(data.get("f43"))
    if price is None:
        return None

    return SpotQuote(
        code=str(data.get("f57") or normalized_code),
        name=str(data.get("f58") or normalized_code),
        price=price,
        open=_parse_number(data.get("f46")),
        high=_parse_number(data.get("f44")),
        low=_parse_number(data.get("f45")),
        prev_close=_parse_number(data.get("f60")),
        change_pct=_parse_number(data.get("f170")),
        main_net_inflow=_parse_number(data.get("f62")),
        large_net_inflow=_parse_number(data.get("f66")),
        super_large_net_inflow=_parse_number(data.get("f69")),
        main_net_pct=_parse_number(data.get("f184")),
    )


def fetch_money_flow(code: str) -> SpotQuote | None:
    """拉取实时报价与主力资金流向。"""
    return fetch_spot_quote(code)


def to_secid(code: str) -> str:
    """将 6 位股票代码转为东方财富 secid。"""
    code = "".join(ch for ch in code if ch.isdigit()).zfill(6)
    market = "1" if code.startswith("6") else "0"
    return f"{market}.{code}"


@dataclass
class SectorQuote:
    change_pct: float
    up_ratio: float
    sentiment_score: int
    sentiment_label: str


SECTOR_URL = "https://push2.eastmoney.com/api/qt/stock/get"


def fetch_sector_quote(sector_code: str) -> SectorQuote | None:
    """拉取东方财富板块指数涨跌（用于板块情绪）。"""
    if not sector_code:
        return None
    market = "90"
    payload = direct_http_get_json(
        SECTOR_URL,
        params={
            "fltt": "2",
            "invt": "2",
            "fields": "f3,f104,f105,f106",
            "secid": f"{market}.{sector_code}",
        },
    )
    data = payload.get("data") or {}
    try:
        change_pct = float(data.get("f3"))
    except (TypeError, ValueError):
        return None
    up_count = int(data.get("f104") or 0)
    down_count = int(data.get("f105") or 0)
    flat_count = int(data.get("f106") or 0)
    total = up_count + down_count + flat_count
    up_ratio = round(up_count / total * 100, 1) if total > 0 else 50.0
    sentiment_score = int(round(50 + change_pct * 8 + (up_ratio - 50) * 0.3))
    sentiment_score = max(0, min(100, sentiment_score))
    if sentiment_score >= 65:
        label = "板块偏强"
    elif sentiment_score <= 35:
        label = "板块偏弱"
    else:
        label = "板块中性"
    return SectorQuote(
        change_pct=round(change_pct, 2),
        up_ratio=up_ratio,
        sentiment_score=sentiment_score,
        sentiment_label=label,
    )


def fetch_intraday_bars(code: str, period: str = "5m", bars: int = 48) -> pd.DataFrame:
    """拉取分时/分钟 K 线。"""
    if period not in PERIOD_MAP:
        raise ValueError(f"不支持的周期: {period}")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5 if period in {"5m", "15m"} else 10)
    raw = fetch_kline(
        code=code,
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        period=period,
        adjust="",
    )
    if raw.empty:
        return pd.DataFrame()
    return raw.tail(bars).reset_index(drop=True)


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
    span_candidates = sorted(
        {max(days * 2, 365), max(days * 2, 180), max(days + 30, 90), days + 15},
        reverse=True,
    )
    last_error: Exception | None = None

    for span_days in span_candidates:
        window_start = end_date - timedelta(days=span_days)
        try:
            raw = fetch_kline(
                code=code,
                start_date=window_start.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                period="daily",
                adjust="qfq",
            )
            if raw.empty:
                continue
            trimmed = raw.tail(days).reset_index(drop=True)
            if len(trimmed) >= min(days, 30):
                return trimmed
        except Exception as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    raise ValueError(f"未获取到股票 {code} 的行情数据")
